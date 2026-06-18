"""CdTe virtual instruments.

Each device asks the landscape for the 'truth', adds measurement noise, and
returns a measurement via the standard device_result() contract. The optimizer
only ever sees these noisy measurements — never the landscape's true values.
"""

import numpy as np

from devices.base import BaseDevice, device_result
from devices.cdte import landscape


class XRDSimulator(BaseDevice):
    """Simulates an XRD measurement of film crystallinity."""

    name = "xrd_simulator"

    def __init__(self, rng, noise_sigma=0.03):
        # rng = a random-number generator (passed in so results are reproducible)
        # noise_sigma = how much measurement noise to add
        self.rng = rng
        self.noise_sigma = noise_sigma

    def run(self, inputs):
        params = inputs["parameters"]

        # First: does this parameter set fail outright? If so, return a failure
        # instead of a fake measurement. Failures are first-class data.
        failure = landscape.failure_for(params)
        if failure is not None:
            return device_result(
                "failed",
                metadata={"reason": failure},
                data_quality_score=0.15,   # a failed run yields low-quality data
                failure_category=failure,
            )

        # Otherwise: ask the landscape for the TRUE score at this point.
        true = landscape.true_score(params)

        # Add gaussian measurement noise: same point measured twice differs a bit.
        # TASK: produce a noisy version of `true`.
        # Hint: self.rng.normal(0, self.noise_sigma) draws one random noise value.
        #       Add it to `true`.
        measured = true + self.rng.normal(0, self.noise_sigma) # replace this

        # Keep the measurement inside [0, 1] (noise could push it outside).
        measured = float(np.clip(measured, 0, 1))

        return device_result(
            "completed",
            outputs={"crystallinity_score": round(measured, 4)},
            metadata={"noise_model": "gaussian", "noise_sigma": self.noise_sigma},
        )
    
class SolarCellJVSimulator(BaseDevice):
    """Simulates a J-V (current-voltage) measurement — the final device that
    produces the overall objective score for an experiment."""

    name = "solar_cell_jv_simulator"

    def __init__(self, rng, noise_sigma=0.03):
        self.rng = rng
        self.noise_sigma = noise_sigma

    def run(self, inputs):
        params = inputs["parameters"]

        # Same failure check as before: don't measure a degraded sample.
        failure = landscape.failure_for(params)
        if failure is not None:
            return device_result(
                "failed",
                metadata={"reason": failure},
                data_quality_score=0.15,
                failure_category=failure,
            )

        # The 'upstream' dict carries measurements from devices that ran earlier.
        # .get(key, default) reads a value if present, else uses the default.
        upstream = inputs.get("upstream", {})
        crystallinity = upstream.get("crystallinity_score", 0.5)

        # The true score is the physical basis; we blend in the upstream
        # crystallinity measurement so this device 'depends on' earlier ones.
        true = landscape.true_score(params)
        pce_basis = 0.7 * true + 0.3 * crystallinity

        # Add measurement noise, then clamp.
        # TASK: make a noisy version of pce_basis (same pattern as XRD).
        pce = pce_basis + self.rng.normal(0, self.noise_sigma)  # replace this
        pce = float(np.clip(pce, 0, 1))

        return device_result(
            "completed",
            outputs={"pce_proxy": round(pce, 4)},
            metadata={"noise_model": "gaussian", "noise_sigma": self.noise_sigma},
        )
    
def build_cdte_devices(rng):
    """Create all CdTe devices and return them keyed by name.

    The executor looks up devices by name (the same names used in the workflow
    YAML), so this registry is the bridge between 'a name in a config file' and
    'an actual device object that can run'.
    """
    devices = [
        XRDSimulator(rng),
        SolarCellJVSimulator(rng),
    ]
    # Build a dict: {"xrd_simulator": <XRD object>, "solar_cell_jv_simulator": ...}
    return {d.name: d for d in devices}