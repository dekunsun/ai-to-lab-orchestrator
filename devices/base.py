"""Shared contract for all virtual lab devices.

Every device — deposition, annealing, XRD, etc. — returns the SAME shape of
result via device_result(). This uniformity lets the executor treat the lab as
a sequence of interchangeable instruments instead of hard-coding each one.
"""


def device_result(status, outputs=None, metadata=None,
                  data_quality_score=1.0, failure_category=None):
    """Build the standard result dict that every device returns.

    Args:
        status: "completed" or "failed".
        outputs: dict of measurements, e.g. {"crystallinity_score": 0.83}.
        metadata: dict of notes, e.g. the noise level used.
        data_quality_score: 0..1, how trustworthy this measurement is.
        failure_category: a string reason if status is "failed", else None.
    """
    return {
        "status": status,
        "outputs": outputs or {},          # `or {}` means: if None, use empty dict
        "metadata": metadata or {},
        "data_quality_score": data_quality_score,
        "failure_category": failure_category,
    }


class BaseDevice:
    """Parent class for all devices. Each real device subclasses this and
    implements its own run() method."""

    name = "base_device"   # each device overrides this with its own name

    def run(self, inputs):
        # Subclasses MUST implement this. If one forgets, calling run() raises
        # this clear error instead of silently doing nothing.
        raise NotImplementedError