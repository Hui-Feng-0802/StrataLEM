# StrataLEM

Stratigraphy-Resolved Limit-Equilibrium Modeling Framework

StrataLEM reads cross-section geometry and material regions, searches candidate circular slip surfaces, and evaluates the Swedish (ordinary/Fellenius) method of slices. Version1.2 supports optional foundation-height preprocessing, toe/crest checks, material correspondence checks and automatic figure export. Stability-only calculations remain independent of foundation inputs.

## Script-driven use

Edit `run_analysis.py`, then run it in your IDE or with `python run_analysis.py`.
It retains the original `Slope(slope_coords, strata_polys, strata_args, ...)`
input order and the `slips_num`, `slices_pieces_num`, and `iterations` settings.
`ENABLE_FOUNDATION = False` selects stability only. Set it to `True` to evaluate
the adopted foundation-height equations before the same stability calculation.
CSV/DXF paths and `[c, phi, gamma]` rows are assigned directly in the script.
JSON and command-line arguments are optional alternatives, not requirements.

The default script uses a synthetic 24m homogeneous section. Its foundation
properties, when enabled, match that synthetic material. `run_foundation_only.py`
separately evaluates the scalar parameters printed in the manuscript.

See `README.zh-CN.md` for the Chinese operating guide.

## Installation

Python 3.10 or later is recommended.

```bash
python -m pip install -r requirements.txt
```

Install GeoPandas and a GDAL build with DXF support when using DXF input:

```bash
python -m pip install -r requirements-dxf.txt
```

## Demonstration

From the repository root:

```bash
python -m stratalem --config examples/demo.json --output results/demo
python -m unittest discover -s tests -v
```

The included example is an explicitly synthetic software demonstration.

## Input configuration

A JSON configuration specifies:

- `surface_csv`: headerless CSV with two columns, x and y in meters. Coordinates must follow the surface in strictly increasing x order; vertical or repeated-x segments require a different interpolation treatment.
- `materials`: material names, cohesion in kPa, friction angle in degrees, unit weight in kN/m3, and material geometry.
- `dxf`: optional DXF file. Each material must specify its `dxf_entity` index, explicitly mapping file entities to material properties. As in the source calculation, DXF geometries are converted to convex hulls. Inspect the reconstructed polygons before analyzing a real case.
- `search`: entry and exit segment indices, points per segment, and sagitta samples per point pair.
- `slices`: number of vertical slices.

Material geometry can instead be supplied directly as polygon coordinates, as in the example. Relative paths are resolved against the configuration file, not the working directory. Units must be consistent. Results are evaluated per unit out-of-plane thickness.

The default search has two entry points, two exit points, and 15 sagitta samples per pair, producing 60 candidates. The default slice count is 50. The entry segment must be explicitly selected for the supplied profile; different section geometries need not use the same vertex indices.

## Computational components

| Component | File |
|---|---|
| Data Parsing | `stratalem/data_parsing.py` |
| Computational Geometry | `stratalem/computational_geometry.py` |
| Slip-Surface Search | `stratalem/slip_surface_search.py` |
| Slice-Based Solution | `stratalem/slice_based_solution.py` |
| Result Management | `stratalem/result_management.py` |

`stratalem/framework.py` coordinates these components. The numerical circle generation, slice interpolation, multi-material weight integration, signed driving-force sum, and midpoint-based material assignment were extracted from the author's existing calculation code. Parallel unordered result collection was replaced by deterministic candidate order so each factor of safety remains associated with its circle.

## Optional foundation preprocessor

`stratalem/foundation.py` implements the equations adopted in the manuscript:

```text
Hd = compression_fraction * (1 + e0) / (a * gamma1)
Nq = exp(pi*tan(phi0)) * tan(pi/4 + phi0/2)^2
Nc = (Nq - 1) / tan(phi0)
Hb = (c0*Nc + q*Nq) / gamma1
H_adopted = floor(min(Hd,Hb) / height_step) * height_step
```

Angles are supplied in degrees and converted internally. Units are m, kPa,
kN/m3, and kPa^-1. The default compression fraction is 0.20 and the downward
rounding step is 1m. The zero-friction limit uses Nc=pi+2 and Nq=1 for the
adopted factors; this is an algebraic edge-case extension, not a new field result.
The supported bearing-factor input range is 0<=phi0<60 degrees.

The optional classification implements Eqs. (1)-(4), recording its assumed beta.
If classification is absent or h<=h0, the integrated assessment is not confirmed.
The bearing calculation uses the adopted TWO-TERM relation only. It does not
add a width/self-weight term, bearing-capacity safety factor, groundwater model,
or settlement calibration. q is an independently specified surcharge pressure;
it is never generated from the unknown dumping height. `q_basis_confirmed`
acknowledges the user's stated input assumption, not verification of field data.

`SectionReference` identifies explicit toe and crest vertices and, optionally,
target elevations such as 700m and 840m. An explicit elevation offset is used
only to check a local datum; it does not transform the calculation geometry.
The surface's total vertical span is reported separately, not treated as a
universal definition of dumping height. `FoundationMaterialMap` associates the
foundation inputs with the waste and soil rows in the stability material array.

No geometry is generated, raised, flattened, or relabeled by this module. A
target mismatch, excessive height, unmatched material properties, missing
classification/reference, or unacknowledged q assumption is recorded separately
from the factor of safety. `meets_adopted_numerical_criteria` refers only to the
entered equations, geometry references, and strict factor-of-safety criterion.
It is not a site safety certification or an automatic slope-angle optimizer.

With e0=.564, a=1.2e-4, gamma1=18.5, c0=30, phi0=20 and q=370, full-precision
evaluation gives Hd=140.9009009009m and Hb=152.0441597913m, adopting 140m.
Using the manuscript's printed intermediate factors Nq=6.399 and Nc=14.834
instead gives Hb=152.0351351351m, reproducing the reported 152.035m. This
intermediate-precision path explains the approximately 0.00902m difference
from the full-precision result (about 0.00916m relative to the displayed
three-decimal height). The code evaluates the factors at full precision and
does not hardcode a correction to reproduce the printed height.

## Outputs

- `summary.json`: settings, minimum factor of safety, critical-circle geometry and candidate counts.
- `candidates.csv`: every candidate, geometric-filter status and calculated factor of safety.
- `critical_slices.csv`: slice weights, base lengths and inclinations, basal material indices, and resisting/driving terms for the selected candidate.
- `foundation.json`: complete scalar inputs, classification and height estimates when enabled; an explicit `not_performed` record when disabled, replacing any previous stage output in the same destination.

`summary.json` also records mode, toe/crest checks, material correspondence,
height and stability criteria. The critical-slice CSV records use of the original
last-intersected-material fallback and the summed-material-area balance. These
diagnostics report source behavior without changing its numerical formula.

No output contains a preassigned manuscript factor of safety. Each value is calculated from the supplied geometry, materials, and search settings.

## Method and scope

The calculation uses circular slip surfaces, vertical slices, zero pore-water pressure, and no interslice forces. Slice weights are integrated over material overlaps. Basal strength is identified at each base midpoint; the source calculation's last-intersected-material fallback is retained when strict point containment fails. Results depend on material ordering in those fallback cases.

The source geometry filter counts surface segments whose endpoint distances straddle the trial radius. Its treatment of tangencies and two intersections within a segment follows the original implementation. The reported minimum is taken over the valid evaluated candidates.

## Automatic figure export

The entry points save the critical surface with vertical slices, finite-candidate
safety factors and optional foundation-height comparisons. Each graph is saved
as600dpi RGB/LZW TIFF, PNG, PDF and SVG. The original `slp.plot('min')` call remains
available, together with `plot('all')`, `plot('thd',threshold=1.20)` and
`slp.save_plots('results/case')`. Plotting options and workflow references are
documented in `FIGURES.md`.

## License

MIT. See `LICENSE`.
