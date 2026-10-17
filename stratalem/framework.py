"""Deterministic coordinator for the extracted numerical calculation."""
import numpy as np
import math
import numbers
from .foundation import calculate_foundation_height, check_foundation_materials
from .section_checks import check_section
from .computational_geometry import ComputationalGeometry
from .slip_surface_search import SlipSurfaceSearch
from .slice_based_solution import SliceBasedSolution


class StrataLEM(ComputationalGeometry, SlipSurfaceSearch, SliceBasedSolution):
    def __init__(self, surface, polygons, parameters, *, slices=50,
                 entry_segment=-3, exit_segment=0, points_per_segment=2,
                 sagitta_samples=15, foundation=None, section_reference=None,
                 fs_criterion=None, foundation_material_map=None):
        self.slope_coords = np.asarray(surface, dtype=float)
        self.strata_polys = list(polygons)
        self.strata_args = np.asarray(parameters, dtype=float)
        if (self.slope_coords.ndim != 2 or self.slope_coords.shape[1] != 2
                or len(self.slope_coords) < 3 or not np.isfinite(self.slope_coords).all()
                or np.any(np.diff(self.slope_coords[:, 0]) <= 0)):
            raise ValueError("Surface requires >=3 finite x,y pairs in strictly increasing x order.")
        if self.strata_args.shape != (len(self.strata_polys), 3) or not len(self.strata_polys):
            raise ValueError("Supply one [c, phi, gamma] row per material polygon.")
        if (not np.isfinite(self.strata_args).all() or np.any(self.strata_args[:, 0] < 0)
                or np.any(self.strata_args[:, 2] <= 0)
                or np.any((self.strata_args[:, 1] < 0) | (self.strata_args[:, 1] >= 90))):
            raise ValueError("Material parameters require c>=0, gamma>0 and 0<=phi<90 degrees.")
        for poly in self.strata_polys:
            if poly.geom_type != 'Polygon' or not poly.is_valid or poly.area <= 0:
                raise ValueError("Material regions must be valid positive-area polygons.")
        for name, value in [('slices', slices), ('points_per_segment', points_per_segment),
                            ('sagitta_samples', sagitta_samples)]:
            if isinstance(value, bool) or not isinstance(value, numbers.Integral):
                raise ValueError(f"{name} must be an integer.")
        if fs_criterion is not None and (not math.isfinite(fs_criterion) or fs_criterion <= 0):
            raise ValueError("fs_criterion must be finite and positive, or None.")
        self.fs_criterion = fs_criterion
        self.section_check = check_section(self.slope_coords, section_reference)
        self.foundation_result = None if foundation is None else calculate_foundation_height(foundation)
        self.foundation_material_check = None if foundation is None else check_foundation_materials(
            foundation, self.strata_args, foundation_material_map)
        self._slices_pieces_num = int(slices)
        if self._slices_pieces_num < 1:
            raise ValueError("Slice count must be positive.")
        if points_per_segment < 2 or sagitta_samples < 1:
            raise ValueError("Search requires >=2 points per segment and >=1 sagitta sample.")
        self.entry_location = self._segment(entry_segment)
        self.exit_location = self._segment(exit_segment)
        self._entry_points, self._exit_points = self._generate_entry_exit_points(
            self.entry_location, self.exit_location, int(points_per_segment))
        if np.min(self._entry_points[:,0]) <= np.max(self._exit_points[:,0]):
            raise ValueError("Entry range must lie to the right of the exit range.")
        if np.min(self._entry_points[:,1]) <= np.max(self._exit_points[:,1]):
            raise ValueError("This original circle generator requires entry points above exit points.")
        self.slips_circles = self._generate_slips_circles(
            self._entry_points, self._exit_points, int(sagitta_samples))
        self.fs_list = []
        self.geometric_filter = []
        for circle in self.slips_circles:
            from . import geometry_utils as utils
            admissible = utils.check_if_circle_slp_intersect(circle[3:], self.slope_coords) == 2
            self.geometric_filter.append(admissible)
            if not admissible:
                self.fs_list.append(np.nan)
                continue
            top, bottom, intersections = self._generate_slices(
                self._entry_points[int(circle[0])], self._exit_points[int(circle[1])],
                circle[3:], self.slope_coords, self.strata_polys, self._slices_pieces_num)
            fs = self._claculate_fs_ordinary(intersections, bottom, self.strata_args)
            self.fs_list.append(float(fs))
        self.fs_list = np.asarray(self.fs_list, dtype=float)

    def _segment(self, index):
        if isinstance(index, bool) or not isinstance(index, numbers.Integral):
            raise ValueError("Search segment index must be an integer.")
        index = int(index)
        if index < 0:
            index += len(self.slope_coords)
        if not 0 <= index < len(self.slope_coords)-1:
            raise ValueError("Search segment index must identify two successive vertices.")
        return self.slope_coords[index:index+2]

    def critical(self):
        if not np.isfinite(self.fs_list).any():
            raise ValueError("No valid candidate produced a finite factor of safety.")
        i = int(np.nanargmin(self.fs_list))
        return i, self.slips_circles[i], float(self.fs_list[i])

    def plot(self, all_min_thd_fs='min', **kwargs):
        """Retain the original plot('min'/'all'/'thd') call and save files."""
        from .plotting import plot_stability
        return plot_stability(self, all_min_thd_fs, **kwargs)

    def save_plots(self, destination='results', **kwargs):
        from .plotting import export_plots
        return export_plots(self, destination, **kwargs)

    def assessment(self):
        """Separate formula limits, geometry and stability; never infer certification."""
        finite = np.isfinite(self.fs_list).any()
        stability_met = None if self.fs_criterion is None or not finite else self.critical()[2] > self.fs_criterion
        result = {'mode': 'stability_only' if self.foundation_result is None else 'foundation_and_stability',
                  'stability_criterion': self.fs_criterion, 'stability_comparison': '>',
                  'stability_criterion_met': stability_met, 'section': self.section_check,
                  'foundation_material_check': self.foundation_material_check,
                  'height_within_adopted_limit': None,
                  'status': 'stability_only' if self.foundation_result is None else 'incomplete'}
        if self.foundation_result is None:
            return result
        reasons = []
        foundation = self.foundation_result
        classification = foundation['classification']['status']
        if classification != 'thick':
            reasons.append('foundation_classification_' + classification)
        if not foundation['q_basis_confirmed']:
            reasons.append('q_basis_unconfirmed')
        if self.foundation_material_check['status'] != 'matched':
            reasons.append('foundation_material_' + self.foundation_material_check['status'])
        actual = self.section_check['actual_dumping_height_m']
        if actual is None:
            reasons.append('section_reference_missing')
        else:
            # Compare at arithmetic precision; geometry tolerance is not a height allowance.
            within = actual <= foundation['adopted_height_m']
            result['height_within_adopted_limit'] = bool(within)
            if not within:
                reasons.append('foundation_height_exceeded')
            if self.section_check['target_elevations_match'] is False:
                reasons.append('target_geometry_mismatch')
        if not finite:
            reasons.append('no_finite_stability_result')
        elif stability_met is None:
            reasons.append('stability_criterion_not_supplied')
        elif not stability_met:
            reasons.append('stability_criterion_not_met')
        result['status'] = 'criteria_not_confirmed' if reasons else 'meets_adopted_numerical_criteria'
        result['reasons'] = reasons
        return result
