"""CdTe virtual devices.

These wrap the surrogate landscape into a sequence of "instruments". Each one
takes the experiment parameters (plus any upstream outputs) and returns the
standard device_result schema with realistic, noisy, sometimes-failing outputs.

Design choices worth defending in an interview:
  * Measurements are separated from the objective. Devices emit *measurements*
    (crystallinity, bandgap, a J-V curve); only ScoringEngine turns those into a
    single decision number. In a real lab the instruments don't know your
    objective — the orchestration layer does.
  * Noise is recorded, not hidden. Every noisy output carries its noise model in
    metadata, so provenance is auditable.
  * Failures short-circuit the workflow and are categorized.
"""

from __future__ import annotations
import numpy as np

from devices.base import BaseDevice, device_result
from devices.cdte import landscape
from policy.weighted_policy import WeightedPolicy


class ThinFilmDepositionSimulator(BaseDevice):
    name = "thin_film_deposition_simulator"

    def __init__(self, rng: np.random.Generator, noise_sigma: float = 0.03):
        self.rng = rng
        self.noise_sigma = noise_sigma

    def run(self, inputs: dict) -> dict:
        p = inputs["parameters"]
        fail = landscape.failure_for(p)
        if fail == "low_crystallinity":
            # substrate too cold: deposition itself yields an unusable film
            return device_result(
                "failed",
                metadata={"reason": "substrate_temp_too_low", "substrate_temp_c": p["substrate_temp_c"]},
                data_quality_score=0.15,
                failure_category="low_crystallinity",
            )
        # initial film quality tracks thickness + substrate terms of the landscape
        c = landscape.true_components(p)
        film_quality = 0.6 * c.thickness_term + 0.4 * c.substrate_term
        film_quality = float(np.clip(film_quality + self.rng.normal(0, self.noise_sigma), 0, 1))
        thickness_dev = float(self.rng.normal(0, 0.02))  # relative thickness deviation
        return device_result(
            "completed",
            outputs={"film_quality": round(film_quality, 4),
                     "thickness_deviation": round(thickness_dev, 4)},
            metadata={"noise_model": "gaussian", "noise_sigma": self.noise_sigma},
        )


class CdCl2TreatmentSimulator(BaseDevice):
    name = "cdcl2_treatment_simulator"

    def __init__(self, rng: np.random.Generator, noise_sigma: float = 0.03):
        self.rng = rng
        self.noise_sigma = noise_sigma

    def run(self, inputs: dict) -> dict:
        p = inputs["parameters"]
        fail = landscape.failure_for(p)
        if fail == "sample_degraded":
            return device_result(
                "failed",
                metadata={"reason": "overtreatment_hot_and_long",
                          "cdcl2_treatment_temp_c": p["cdcl2_treatment_temp_c"],
                          "cdcl2_treatment_time_min": p["cdcl2_treatment_time_min"]},
                data_quality_score=0.15,
                failure_category="sample_degraded",
            )
        c = landscape.true_components(p)
        # defect passivation = how well we sit in the treatment window, net of cliff
        passivation = c.treatment_window_term * (1.0 - 0.85 * c.overtreatment_penalty)
        passivation = float(np.clip(passivation + self.rng.normal(0, self.noise_sigma), 0, 1))
        return device_result(
            "completed",
            outputs={"defect_passivation_score": round(passivation, 4),
                     "in_optimal_window": bool(c.treatment_window_term > 0.6 and c.overtreatment_penalty < 0.2)},
            metadata={"noise_model": "gaussian", "noise_sigma": self.noise_sigma},
        )


class XRDSimulator(BaseDevice):
    name = "xrd_simulator"

    def __init__(self, rng: np.random.Generator, noise_sigma: float = 0.03):
        self.rng = rng
        self.noise_sigma = noise_sigma

    def run(self, inputs: dict) -> dict:
        p = inputs["parameters"]
        c = landscape.true_components(p)
        crystallinity = 0.5 * c.substrate_term + 0.5 * c.treatment_window_term
        crystallinity = float(np.clip(crystallinity + self.rng.normal(0, self.noise_sigma), 0, 1))
        phase_purity = float(np.clip(1.0 - 0.7 * c.overtreatment_penalty + self.rng.normal(0, self.noise_sigma), 0, 1))
        # tiny synthetic diffractogram as an artifact (kept small)
        two_theta = np.linspace(20, 60, 64)
        peak = np.exp(-((two_theta - 24.0) ** 2) / 2.0) * crystallinity
        artifact = {
            "artifact_type": "xrd_pattern",
            "x_two_theta": [round(float(v), 2) for v in two_theta[::8]],
            "y_intensity": [round(float(v), 4) for v in peak[::8]],
        }
        return device_result(
            "completed",
            outputs={"crystallinity_score": round(crystallinity, 4),
                     "phase_purity": round(phase_purity, 4)},
            metadata={"noise_model": "gaussian", "noise_sigma": self.noise_sigma},
            artifacts=[artifact],
        )


class OpticalSpectroscopySimulator(BaseDevice):
    name = "optical_spectroscopy_simulator"

    def __init__(self, rng: np.random.Generator, noise_sigma: float = 0.02):
        self.rng = rng
        self.noise_sigma = noise_sigma

    def run(self, inputs: dict) -> dict:
        p = inputs["parameters"]
        c = landscape.true_components(p)
        # CdTe bandgap ~1.5 eV; drift slightly with thickness term, add noise
        bandgap = float(1.50 + 0.03 * (c.thickness_term - 0.5) + self.rng.normal(0, 0.01))
        absorption = float(np.clip(0.7 * c.thickness_term + 0.3 + self.rng.normal(0, self.noise_sigma), 0, 1))
        return device_result(
            "completed",
            outputs={"bandgap_ev": round(bandgap, 4),
                     "absorption_score": round(absorption, 4)},
            metadata={"noise_model": "gaussian", "noise_sigma": self.noise_sigma},
        )


class SolarCellJVSimulator(BaseDevice):
    name = "solar_cell_jv_simulator"

    def __init__(self, rng: np.random.Generator, noise_sigma: float = 0.03):
        self.rng = rng
        self.noise_sigma = noise_sigma

    def run(self, inputs: dict) -> dict:
        p = inputs["parameters"]
        up = inputs.get("upstream", {})
        true = landscape.true_score(p)
        # device-level proxies derived from the true score + upstream measurements
        voc = float(np.clip(0.8 * true + 0.1 + self.rng.normal(0, self.noise_sigma), 0, 1))
        jsc = float(np.clip(0.7 * up.get("absorption_score", 0.5) + 0.3 * true + self.rng.normal(0, self.noise_sigma), 0, 1))
        ff = float(np.clip(0.6 * up.get("defect_passivation_score", 0.5) + 0.3 + self.rng.normal(0, self.noise_sigma), 0, 1))
        pce_proxy = float(np.clip(voc * jsc * ff * 1.15, 0, 1))
        # tiny J-V curve artifact
        v = np.linspace(0, 0.9, 32)
        j = jsc * (1 - np.exp((v - voc) / 0.05))
        artifact = {
            "artifact_type": "jv_curve",
            "voltage_v": [round(float(x), 3) for x in v[::4]],
            "current_proxy": [round(float(max(-0.05, y)), 4) for y in j[::4]],
        }
        return device_result(
            "completed",
            outputs={"voc_proxy": round(voc, 4), "jsc_proxy": round(jsc, 4),
                     "fill_factor_proxy": round(ff, 4), "pce_proxy": round(pce_proxy, 4)},
            metadata={"noise_model": "gaussian", "noise_sigma": self.noise_sigma},
            artifacts=[artifact],
        )


class ScoringEngine(BaseDevice):
    """Turns accumulated measurements into the single objective the optimizer sees.

    This is the ONLY place measurements become a decision number — and it does
    not decide the trade-off itself. The weights come from a WeightedPolicy
    loaded from `configs/policies/`, because "how much is phase purity worth
    relative to efficiency?" is a research-strategy question, not a property of
    an instrument. Hard-coding it here would bury the most contestable
    assumption in the system inside a simulated device.

    The same policy mechanism drives hydride candidate triage, so both halves of
    the project make trade-offs the same auditable way.
    """
    name = "scoring_engine"

    def __init__(self, policy: WeightedPolicy):
        self.policy = policy

    def run(self, inputs: dict) -> dict:
        m = inputs.get("upstream", {})
        # A missing metric raises rather than scoring as zero — see WeightedPolicy.
        score = self.policy.score(m)
        return device_result(
            "completed",
            outputs={"objective_score": round(score, 4)},
            metadata={
                **self.policy.provenance(),
                # per-term breakdown so a dashboard can show WHY it scored this way
                "contributions": self.policy.contributions(m),
            },
        )


DEFAULT_CDTE_POLICY = "configs/policies/cdte_balanced_device_quality.yaml"


def build_cdte_devices(rng: np.random.Generator,
                       policy: WeightedPolicy | str | None = None) -> dict[str, BaseDevice]:
    """Registry mapping the `device:` names in the YAML to instances.

    `policy` accepts a WeightedPolicy, a path to a policy YAML, or None for the
    default balanced policy.
    """
    if policy is None:
        policy = DEFAULT_CDTE_POLICY
    if isinstance(policy, str):
        policy = WeightedPolicy.from_yaml(policy)

    return {
        d.name: d for d in [
            ThinFilmDepositionSimulator(rng),
            CdCl2TreatmentSimulator(rng),
            XRDSimulator(rng),
            OpticalSpectroscopySimulator(rng),
            SolarCellJVSimulator(rng),
            ScoringEngine(policy),
        ]
    }
