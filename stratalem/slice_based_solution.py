"""Numerical methods extracted from the author's existing calculation."""
from __future__ import annotations
import numpy as np
from shapely.geometry import Point
from math import atan2, radians, sin, cos, tan

class SliceBasedSolution:

    def _claculate_fs_ordinary(self, slices_strata_list: np.array, slices_bot_points: np.ndarray, strata_args: np.ndarray):
        pushing_force = 0
        resistance_force = 0
        for slice_idx, slice_with_strata in enumerate(slices_strata_list):
            w_slice = 0
            mask = slice_with_strata != None
            exist_stratum_indices = np.argwhere(mask).flatten()
            for exist_stratum_idx in exist_stratum_indices:
                gamma = strata_args[exist_stratum_idx, 2]
                w_slice_stratum = gamma * slice_with_strata[exist_stratum_idx].area
                w_slice += w_slice_stratum
            p1 = slices_bot_points[slice_idx]
            p2 = slices_bot_points[slice_idx + 1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            alpha = atan2(dy, dx)
            bottom_length = np.hypot(dx, dy)
            mid_point = 0.5 * (p1 + p2)
            stratum_idx = self._determine_stratum(mid_point, exist_stratum_indices, slice_with_strata)
            if stratum_idx is None:
                continue
            c = strata_args[stratum_idx, 0]
            phi = radians(strata_args[stratum_idx, 1])
            cohesion_force_slice = c * bottom_length
            friction_slice = w_slice * cos(alpha) * tan(phi)
            resistance_force_slice = cohesion_force_slice + friction_slice
            pushing_force_slice = w_slice * sin(alpha)
            resistance_force += resistance_force_slice
            pushing_force += pushing_force_slice
        if pushing_force < 1e-06:
            return np.nan
        return resistance_force / pushing_force

    def _determine_stratum(self, point, stratum_indices, slice_with_strata):
        for idx in stratum_indices:
            if slice_with_strata[idx] is not None and slice_with_strata[idx].contains(Point(point)):
                return idx
        if stratum_indices.size > 0:
            return stratum_indices[-1]
        return None
