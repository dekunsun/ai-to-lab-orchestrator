"""CdTe surrogate 'truth' landscape.

This is NOT a real physical model. It is a deliberately designed 'terrain' with
peaks (good parameters) and valleys (bad parameters). Its job is to give the
optimizer a search space with realistic difficulty to explore.
"""

import math


def _bell(x, center, width):
    """Bell curve (Gaussian bump).

    Returns 1.0 when x is exactly at `center` (the peak), and a value that gets
    closer to 0 the further x is from center. This is the basic building block
    we use to construct the 'terrain'.

    Examples:
        _bell(388, 388, 14)  should equal 1.0
        _bell(420, 388, 14)  should be clearly less than 1
    """
    return math.exp(-((x - center) ** 2) / (2 * (width ** 2)))

def _cliff(x, threshold, sharpness):
    """A 'cliff' penalty using a sigmoid (S-shaped) curve.

    Returns ~0 when x is well below `threshold`, and rises toward ~1 as x goes
    past it. We'll use this so that 'too hot' CdCl2 treatment sharply destroys
    the score, instead of degrading smoothly.

    Example: _cliff(440, threshold=428, sharpness=3) should be close to 1
             _cliff(400, threshold=428, sharpness=3) should be close to 0
    """
    return 1.0 / (1.0 + math.exp(-(x - threshold) / sharpness))


def true_score(params):
    """Noise-free 'true' score in [0, 1] for a set of CdTe process parameters.

    The optimizer never sees this directly — devices add noise on top. This is
    the ground truth we're hiding from the optimizer.
    """
    thickness = params["cdte_thickness_nm"]
    substrate = params["substrate_temp_c"]
    treat_temp = params["cdcl2_treatment_temp_c"]

    # Each parameter has an optimum, expressed as a bell curve.
    # TASK 1: fill in the center/width for each (reasonable guesses are fine).
    thickness_term = _bell(thickness, center=2000, width=480)
    substrate_term = _bell(substrate, center=460, width=80)
    treatment_term = _bell(treat_temp, center=388, width=14)

    # Combine the 'good' terms into a base score (weighted sum).
    base = 0.34 * treatment_term + 0.24 * thickness_term + 0.20 * substrate_term

    # The over-treatment cliff: if treat_temp is too high, crash the score.
    overtreatment = _cliff(treat_temp, threshold=428, sharpness=3)

    # TASK 2: apply the cliff penalty to `base`.
    # We want: when overtreatment is ~0, score stays ~= base;
    #          when overtreatment is ~1, score drops to about 15% of base.
    # Hint: multiply base by (1 - 0.85 * overtreatment)
    score = base * (1 - 0.85 * overtreatment)  # replace this

    # Clamp to [0, 1] just in case.
    return max(0.0, min(1.0, score))

def failure_for(params):
    """Decide whether a parameter set causes an OUTRIGHT experiment failure.

    Returns a failure-category string if the experiment fails, or None if it
    runs successfully. A failure means we get no usable measurement at all —
    this is different from (and worse than) just a low score.

    Returning a category (not just True/False) matters: in a real lab, failures
    are first-class data — we want to know WHY it failed, not just that it did.
    """
    treat_temp = params["cdcl2_treatment_temp_c"]
    treat_time = params["cdcl2_treatment_time_min"]
    substrate = params["substrate_temp_c"]

    # Hot AND long -> the sample degrades into something unmeasurable.
    if treat_temp > 450 and treat_time > 45:
        return "sample_degraded"

    # Substrate too cold -> the film never crystallizes enough to measure.
    if substrate < 285:
        return "low_crystallinity"

    # Otherwise the experiment runs fine.
    return None
