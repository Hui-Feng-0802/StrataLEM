# Automatic calculation plots

Run `python run_analysis.py` with the original script-based inputs, or use
`python -m stratalem --config examples/demo.json --output results/demo`.
Both entry points now save numerical outputs and calculation figures automatically.

The original calls remain available:

```python
slp.plot('min', output='results/critical_surface')
slp.plot('all', output='results/all_surfaces')
slp.plot('thd', threshold=1.20, output='results/below_threshold')
slp.save_plots('results/case')
```

`save_plots` exports the critical surface with vertical slices, finite-candidate
safety factors, and foundation-height results when the optional stage is enabled.
Each figure is saved as RGB/LZW TIFF at600dpi, PNG, editable PDF and SVG.
Actual input coordinates and material polygons determine the drawing; safety
factors are read directly from the calculation. `material_names` and
`material_colors` may be supplied in polygon order. The default names are
Material1, Material2, etc. No geological identity is inferred from polygon order.

The `examples` folder contains an explicitly synthetic software example.
Manuscript figures are generated separately by `make_manuscript_figures.py`.

## Software-workflow acknowledgment

Figure-production guidance used Scientific Agent Skills: Kassis T, Agarwal V,
He Y, Patel D, Brueckner AM (2026), *Scientific Agent Skills: A Library of
Procedural Knowledge for Research Agents*. https://doi.org/10.48550/arXiv.2609.00065.
This is a software-workflow reference, not evidence for the engineering results.
