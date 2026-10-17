"""Original Slope constructor and script-driven parameter assignment."""
import math
import numbers
import warnings
from .framework import StrataLEM


def _legacy_range(name, value, lower, upper):
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise ValueError(f"{name} must be an integer.")
    clamped = max(lower, min(value, upper))
    if clamped != value:
        warnings.warn(f"{name}={value} was clamped to {clamped}, as in the original script.",
                      UserWarning, stacklevel=3)
    return clamped


class Slope(StrataLEM):
    def __init__(self, slope_coords, strata_polys, strata_args, slips_num=15,
                 slices_pieces_num=50, iterations=15, *, entry_segment=-3,
                 exit_segment=0, foundation=None, section_reference=None,
                 fs_criterion=None, foundation_material_map=None):
        slips = _legacy_range('slips_num', slips_num, 15, 30)
        slices = _legacy_range('slices_pieces_num', slices_pieces_num, 50, 80)
        iterations = _legacy_range('iterations', iterations, 15, 100)
        points = int(math.sqrt(iterations / slips)) + 1
        if points < 2:
            raise ValueError("The original iterations/slips_num combination creates only one search point per segment; increase iterations to at least slips_num.")
        self._slips_num = slips
        self._iterations = iterations
        self._entry_exit_points_interp_num = points
        super().__init__(slope_coords, strata_polys, strata_args, slices=slices,
                         entry_segment=entry_segment, exit_segment=exit_segment,
                         points_per_segment=points, sagitta_samples=slips,
                         foundation=foundation, section_reference=section_reference,
                         fs_criterion=fs_criterion, foundation_material_map=foundation_material_map)
