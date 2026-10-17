"""Read-only checks of explicit toe/crest vertices; never reshape a section."""
from dataclasses import asdict, dataclass
import math
import numbers
import numpy as np


@dataclass(frozen=True)
class SectionReference:
    toe_index: int
    crest_index: int
    elevation_offset: float = 0.0
    target_base: float | None = None
    target_crest: float | None = None
    tolerance: float = 0.05


def check_section(surface, reference):
    surface = np.asarray(surface, dtype=float)
    span = float(np.ptp(surface[:, 1]))
    if reference is None:
        return {"status": "reference_not_supplied", "surface_vertical_span_m": span,
                "actual_dumping_height_m": None}
    if not isinstance(reference, SectionReference):
        raise TypeError("section_reference must be SectionReference or None.")
    for name in ("toe_index", "crest_index"):
        value = getattr(reference, name)
        if isinstance(value, bool) or not isinstance(value, numbers.Integral):
            raise ValueError(f"{name} must be an integer vertex index.")
        if not -len(surface) <= value < len(surface):
            raise ValueError(f"{name} is outside the surface vertex range.")
    if not math.isfinite(reference.tolerance) or reference.tolerance < 0:
        raise ValueError("Section tolerance must be finite and nonnegative.")
    if not math.isfinite(reference.elevation_offset):
        raise ValueError("Elevation offset must be finite.")
    if (reference.target_base is None) != (reference.target_crest is None):
        raise ValueError("Supply target_base and target_crest together.")
    toe = surface[reference.toe_index]
    crest = surface[reference.crest_index]
    base = float(toe[1] + reference.elevation_offset)
    top = float(crest[1] + reference.elevation_offset)
    height = float(crest[1] - toe[1])
    if height <= 0:
        raise ValueError("The selected crest must be above the selected toe.")
    target_match = None
    if reference.target_base is not None:
        if not all(math.isfinite(v) for v in (reference.target_base, reference.target_crest)):
            raise ValueError("Target elevations must be finite.")
        if reference.target_crest <= reference.target_base:
            raise ValueError("target_crest must exceed target_base.")
        target_match = bool(abs(base - reference.target_base) <= reference.tolerance
                            and abs(top - reference.target_crest) <= reference.tolerance)
    horizontal = float(abs(crest[0] - toe[0]))
    return {"status": "target_mismatch" if target_match is False else "reference_checked",
            "reference": asdict(reference), "surface_vertical_span_m": span,
            "actual_dumping_height_m": height, "base_elevation_m": base,
            "crest_elevation_m": top, "target_elevations_match": target_match,
            "toe_x": float(toe[0]), "crest_x": float(crest[0]),
            "toe_to_crest_angle_degrees": math.degrees(math.atan2(height, horizontal))}
