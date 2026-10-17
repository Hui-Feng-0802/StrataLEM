"""Edit variables below, then run this file in an IDE or with Python.

Default: synthetic stability-only example. No mine data are included.
"""
from pathlib import Path
import json
import numpy as np
from shapely.geometry import Polygon
from stratalem import Slope, FoundationInputs, FoundationClassification, FoundationMaterialMap, SectionReference
from stratalem.data_parsing import load_surface_csv, load_dxf_materials
from stratalem.result_management import export_results


if __name__ == '__main__':
    ROOT = Path(__file__).resolve().parent
    USE_SYNTHETIC_EXAMPLE = True
    ENABLE_FOUNDATION = False      # False: original stability-only path
    FS_CRITERION = 1.20            # Strict comparison: Fs > 1.20

    if USE_SYNTHETIC_EXAMPLE:
        slope_coords = load_surface_csv(ROOT / 'examples/demo_surface.csv')
        strata_polys = [Polygon([(-100,-100),(100,-100),(100,100),(-100,100)])]
        strata_args = np.array([[12.0, 28.0, 19.0]])  # c, phi, gamma
        entry_segment, exit_segment = -2, 0
        # Explicitly selected toe/crest of the synthetic example, height 24m.
        section_reference = SectionReference(toe_index=1, crest_index=4,
                                             target_base=0, target_crest=24)
    else:
        # Replace these LOCAL paths and material rows with your original inputs.
        slope_coords = load_surface_csv(ROOT / 'private_data/surface.csv')
        strata_polys = load_dxf_materials(ROOT / 'private_data/strata.dxf',
                                         entity_indices=[0, 1, 2])
        strata_args = np.array([[30,20,21], [120,28,21], [31,22,18.5]])
        entry_segment, exit_segment = -3, 0
        # Select actual toe/crest vertex indices after inspecting the CSV.
        # No automatic use of max(y)-min(y), and no assumed vertical datum.
        section_reference = None
        # For a verified absolute-elevation 140m design section, for example:
        # section_reference = SectionReference(toe_index=0, crest_index=-1,
        #     target_base=700, target_crest=840, elevation_offset=0)

    foundation = None
    foundation_material_map = None
    if ENABLE_FOUNDATION:
        # Published scalar parameters; these do NOT reshape the input profile.
        foundation = FoundationInputs(
            e0=0.564, a=1.2e-4, gamma1=18.5, c0=30, phi0=20, q=370,
            classification=FoundationClassification(
                e1=0.40, dm=0.60, beta=22, gamma0=21, thickness=10),
            compression_fraction=0.20, height_step=1.0,
            q_basis='Adopted surcharge pressure at foundation level specified for this study: 370kPa.',
            q_basis_confirmed=True)  # Acknowledged input assumption, not field verification.
        if USE_SYNTHETIC_EXAMPLE:
            # For this homogeneous software example, keep scalar properties
            # consistent with its ONE synthetic material, not the mine inputs.
            foundation = FoundationInputs(
                e0=0.564, a=1.2e-4, gamma1=19, c0=12, phi0=28, q=370,
                classification=FoundationClassification(
                    e1=0.40, dm=0.60, beta=45, gamma0=19, thickness=10),
                q_basis='Independent surcharge assumed for the synthetic software example only.',
                q_basis_confirmed=True)
            foundation_material_map = FoundationMaterialMap(waste_index=0, soil_index=0)
        else:
            foundation_material_map = FoundationMaterialMap(waste_index=2, soil_index=0)

    # Original Slope-style input sequence is retained.
    slp = Slope(slope_coords, strata_polys, strata_args,
                slips_num=15, slices_pieces_num=50, iterations=15,
                entry_segment=entry_segment, exit_segment=exit_segment,
                foundation=foundation, section_reference=section_reference,
                fs_criterion=FS_CRITERION, foundation_material_map=foundation_material_map)
    destination = ROOT / 'results' / ('integrated' if ENABLE_FOUNDATION else 'stability_only')
    summary = export_results(slp, {'search': {
        'entry_segment':entry_segment, 'exit_segment':exit_segment,
        'points_per_segment':slp._entry_exit_points_interp_num,
        'sagitta_samples':slp._slips_num}}, destination)
    slp.save_plots(destination)
    print(json.dumps(summary, indent=2, allow_nan=False))
