"""Numerical methods extracted from the author's existing calculation."""
from __future__ import annotations
import numpy as np
from . import geometry_utils as utils

class ComputationalGeometry:

    def _generate_slices(self, entry_point, exit_point, circle, slope_coords, strata_polys, slices_pieces_num):
        slices_top_points = self._generate_slices_top_points(entry_point, exit_point, slope_coords, slices_pieces_num)
        slices_bot_points = self._generate_slices_bottom_points(slices_top_points, circle)
        slices_strata_list = np.full(shape=(slices_pieces_num, len(strata_polys)), dtype=object, fill_value=None)
        for i in range(slices_pieces_num):
            slices_coords = np.array([slices_top_points[i], slices_top_points[i + 1], slices_bot_points[i + 1], slices_bot_points[i]])
            for j in range(len(strata_polys)):
                slices_strata_list[i, j] = utils.check_and_compute_intersection(slices_coords, strata_polys[j])
        return (slices_top_points, slices_bot_points, slices_strata_list)

    def _generate_slices_top_points(self, entry_point: np.ndarray, exit_point: np.ndarray, slope_coords: np.ndarray, slice_pieces: int):
        slice_top_points = np.zeros(shape=[slice_pieces + 1, 2])
        slip_block_top = np.copy(slope_coords)
        slip_block_top[-1] = entry_point
        slip_block_top[0] = exit_point
        slip_block_top_x = slip_block_top[:, 0]
        slice_top_points_x = np.linspace(slip_block_top_x[0], slip_block_top_x[-1], slice_pieces + 1)
        slice_top_points[0] = np.copy(slip_block_top[0])
        for slice_pt_idx, x in enumerate(slice_top_points_x[1:]):
            for slip_pt_idx in range(len(slip_block_top) - 1):
                p1, p2 = (slip_block_top[slip_pt_idx], slip_block_top[slip_pt_idx + 1])
                if (p1[0] < x) & (x <= p2[0]):
                    t = (x - p1[0]) / (p2[0] - p1[0])
                    y = p1[1] + t * (p2[1] - p1[1])
                    slice_top_points[slice_pt_idx + 1] = np.array([x, y])
                    break
                elif x == p1[0]:
                    y = p1[1]
                    slice_top_points[slice_pt_idx + 1] = np.array([x, y])
                    break
                elif x == p2[0] and slip_pt_idx == len(slip_block_top) - 2:
                    y = p2[1]
                    slice_top_points[slice_pt_idx + 1] = np.array([x, y])
                    break
        return slice_top_points

    def _generate_slices_bottom_points(self, slices_top_points: np.ndarray, circle):
        slice_bottom_points = np.zeros(shape=slices_top_points.shape)
        top_x = slices_top_points[:, 0]
        top_y = slices_top_points[:, 1]
        dy = circle[2] ** 2 - (circle[0] - top_x) ** 2
        dy[dy < 0] = 0
        bot_y = circle[1] - np.sqrt(dy)
        slice_bottom_points[:, 0] = np.copy(top_x)
        slice_bottom_points[:, 1] = bot_y
        return slice_bottom_points
