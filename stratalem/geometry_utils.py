"""Geometric helper functions from the author's calculation."""
from __future__ import annotations
import numpy as np
from shapely.geometry import Polygon

def check_and_compute_intersection(quad_points: np.ndarray, other_polygon: Polygon):
    _, qd_pd_idx = np.unique(quad_points, axis=0, return_index=True)
    quad_poly = Polygon(quad_points[np.sort(qd_pd_idx)])
    try:
        intersection = quad_poly.intersection(other_polygon)
        if intersection.is_empty:
            return None
        return intersection
    except:
        intersection = quad_poly.buffer(0).intersection(other_polygon.buffer(0))
        if intersection.is_empty:
            return None
        return intersection

def check_if_circle_slp_intersect(circle, slope_coords):
    counter = 0
    center = circle[:2]
    for slp_pt_idx in range(len(slope_coords) - 1):
        p1 = slope_coords[slp_pt_idx]
        p2 = slope_coords[slp_pt_idx + 1]
        d1 = np.linalg.norm(p1 - center)
        d2 = np.linalg.norm(p2 - center)
        d_min = min(d1, d2)
        d_max = max(d1, d2)
        if (d_min < circle[2]) & (d_max > circle[2]):
            counter += 1
    return counter
