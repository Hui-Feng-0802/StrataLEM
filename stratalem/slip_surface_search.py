"""Numerical methods extracted from the author's existing calculation."""
from __future__ import annotations
import numpy as np
from math import atan, sqrt, sin, cos

class SlipSurfaceSearch:

    def _generate_entry_exit_points(self, entry_location: np.ndarray, exit_location: np.ndarray, interp_num: int):
        entry_points = np.linspace(entry_location[0], entry_location[1], interp_num)
        exit_points = np.linspace(exit_location[0], exit_location[1], interp_num)
        return (entry_points, exit_points)

    def _generate_slips_circles(self, entry_points: np.ndarray, exit_points: np.ndarray, slips_num: int):
        slips_circles = np.full(shape=(len(entry_points) * len(exit_points) * slips_num, 6), dtype=float, fill_value=None)
        total = len(entry_points) * len(exit_points)
        current = 0
        for i, entry_point in enumerate(entry_points):
            for j, exit_point in enumerate(exit_points):
                current += 1
                chord_vect = entry_point - exit_point
                chord_mid_pt_vect = 0.5 * (entry_point + exit_point)
                chord_length = np.linalg.norm(chord_vect)
                chord_slope_angle = atan(chord_vect[1] / chord_vect[0])
                init_radius = chord_length / (2 * cos(chord_slope_angle))
                init_chord_to_center = sqrt(init_radius ** 2 - 0.25 * chord_length ** 2)
                init_chord_to_circum = init_radius - init_chord_to_center
                for m in range(slips_num):
                    chord_to_circum = init_chord_to_circum * (1 - m / slips_num)
                    radius = (0.25 * chord_length ** 2 + chord_to_circum ** 2) / (2 * chord_to_circum)
                    chord_to_center = radius - chord_to_circum
                    circle_center = chord_mid_pt_vect + chord_to_center * np.array([-sin(chord_slope_angle), cos(chord_slope_angle)])
                    slips_circles[(i * len(exit_points) + j) * slips_num + m, 0] = i
                    slips_circles[(i * len(exit_points) + j) * slips_num + m, 1] = j
                    slips_circles[(i * len(exit_points) + j) * slips_num + m, 2] = m
                    slips_circles[(i * len(exit_points) + j) * slips_num + m, 3:5] = circle_center
                    slips_circles[(i * len(exit_points) + j) * slips_num + m, 5] = radius
        return slips_circles
