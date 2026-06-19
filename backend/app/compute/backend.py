from typing import Literal


ComputeMode = Literal["cpu", "gpu_auto", "gpu_force"]


class ComputeUnavailableError(RuntimeError):
    """Raised when a requested compute backend cannot be satisfied."""


def resolve_compute_backend(requested_mode: ComputeMode, *, gpu_enabled: bool) -> str:
    if requested_mode == "cpu":
        return "cpu"

    if requested_mode == "gpu_auto":
        return "gpu" if gpu_enabled else "cpu"

    if requested_mode == "gpu_force":
        if gpu_enabled:
            return "gpu"
        raise ComputeUnavailableError(
            "GPU mode was forced, but GPU support is not enabled in this environment."
        )

    raise ComputeUnavailableError(f"Unsupported compute mode: {requested_mode}")
