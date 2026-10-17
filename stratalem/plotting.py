"""Publication-sized plots of numerical outputs; export .pdf, .svg, .tif and .png."""
from pathlib import Path
import io
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Patch
from matplotlib.path import Path as MplPath
from matplotlib.lines import Line2D
from PIL import Image

BLUE = '#195E83'
RED = '#B53C36'
INK = '#26333B'
COLORS = ('#E6D4A8', '#D4DFE6', '#C4D6C0', '#E4D7E8', '#CCDDE5')


def style():
    plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
                         'font.size': 10, 'axes.labelsize': 10, 'xtick.labelsize': 9,
                         'ytick.labelsize': 9, 'legend.fontsize': 9, 'axes.linewidth': .7,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
                         'mathtext.fontset': 'stix', 'savefig.facecolor': 'white'})


def save_figure(fig, output, formats=('tif', 'pdf', 'svg', 'png'), dpi=600):
    """Save exact physical dimensions; TIFF is flattened RGB with LZW compression."""
    if not 300 <= dpi <= 600:
        raise ValueError('Publication raster resolution must be between 300 and 600dpi.')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    files = []
    fig.canvas.draw()
    for fmt in formats:
        suffix = fmt.lower().lstrip('.')
        if suffix not in ('tif', 'tiff', 'pdf', 'svg', 'png'):
            raise ValueError('Supported formats: tif, tiff, pdf, svg, png.')
        path = output.with_suffix('.' + suffix)
        if suffix in ('tif', 'tiff'):
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=dpi, facecolor='white')
            buf.seek(0)
            with Image.open(buf) as im:
                im.convert('RGB').save(path, compression='tiff_lzw', dpi=(dpi, dpi))
        else:
            fig.savefig(path, dpi=dpi if suffix == 'png' else None, facecolor='white')
        files.append(str(path))
    return files


def _polygon_patch(poly, **kwargs):
    # Orient rings so PDF's nonzero winding rule preserves polygon holes.
    from shapely.geometry.polygon import orient
    poly = orient(poly, sign=1.0)
    vertices, codes = [], []
    for ring in [poly.exterior, *poly.interiors]:
        coords = np.asarray(ring.coords)
        vertices.extend(coords)
        codes.extend([MplPath.MOVETO] + [MplPath.LINETO]*(len(coords)-2) + [MplPath.CLOSEPOLY])
    return PathPatch(MplPath(vertices, codes), **kwargs)


def critical_geometry(model):
    index, circle, fs = model.critical()
    entry = model._entry_points[int(circle[0])]
    exit_ = model._exit_points[int(circle[1])]
    top, bottom, _ = model._generate_slices(entry, exit_, circle[3:], model.slope_coords,
                                            model.strata_polys, model._slices_pieces_num)
    return index, circle, fs, entry, exit_, top, bottom


def _arc(model, circle, n=401):
    entry = model._entry_points[int(circle[0])]
    exit_ = model._exit_points[int(circle[1])]
    xs = np.linspace(exit_[0], entry[0], n)
    radicand = circle[5]**2 - (xs-circle[3])**2
    if np.min(radicand) < -1e-7:
        raise ValueError('Circle does not span its assigned entry and exit points.')
    return xs, circle[4] - np.sqrt(np.maximum(radicand, 0))


def draw_stability(ax, model, *, mode='min', threshold=None, material_names=None,
                   material_colors=None, slices=True, elevation_offset=0, annotate=True,
                   axis_labels=True, full_material_extent=False):
    """Render model geometry without translating, stretching or normalizing it."""
    if mode not in ('min', 'all', 'thd'):
        raise ValueError("mode must be 'min', 'all' or 'thd'.")
    names = list(material_names) if material_names else [f'Material {i+1}' for i in range(len(model.strata_polys))]
    colors = list(material_colors) if material_colors else [COLORS[i % len(COLORS)] for i in range(len(names))]
    if len(names) != len(model.strata_polys) or len(colors) != len(names):
        raise ValueError('Supply one material name and color per polygon.')
    surface = model.slope_coords
    bounds = np.array([p.bounds for p in model.strata_polys])
    floor = min(bounds[:,1].min(), surface[:,1].min()) + elevation_offset
    left, right = min(bounds[:,0].min(),surface[:,0].min()), max(bounds[:,2].max(),surface[:,0].max())
    ground=np.vstack([[left,floor],[right,floor],[right,surface[-1,1]+elevation_offset],
                      np.c_[surface[::-1,0],surface[::-1,1]+elevation_offset],
                      [left,surface[0,1]+elevation_offset],[left,floor]])
    i, circle, fs, entry, exit_, top, bottom = critical_geometry(model)
    xmin = min(surface[:,0].min(), bounds[:,0].min()) if full_material_extent else surface[:,0].min()
    xmax = max(surface[:,0].max(), bounds[:,2].max()) if full_material_extent else surface[:,0].max()
    ymin = (min(bottom[:,1].min(), bounds[:,1].min()) if full_material_extent else
            min(bottom[:,1].min(),surface[:,1].min())-.15*np.ptp(surface[:,1])) + elevation_offset
    ymax = (max(surface[:,1].max(), bounds[:,3].max()) if full_material_extent else surface[:,1].max()) + elevation_offset
    dx,dy=xmax-xmin,ymax-ymin
    from shapely.geometry import Polygon as GeoPolygon, box as geo_box
    window=geo_box(xmin-.025*dx,ymin-.03*dy,xmax+.025*dx,ymax+.12*dy)
    domain=GeoPolygon(ground).intersection(window)
    for poly, color in zip(model.strata_polys, colors):
        from shapely.affinity import translate
        visible=translate(poly,yoff=elevation_offset).intersection(domain)
        pieces=[visible] if visible.geom_type=='Polygon' else getattr(visible,'geoms',[])
        for piece in pieces:
            if piece.geom_type=='Polygon' and not piece.is_empty:
                ax.add_patch(_polygon_patch(piece,facecolor=color,edgecolor='#89959C',lw=.55,zorder=1))
    ax.plot(surface[:,0], surface[:,1]+elevation_offset, color=BLUE, lw=1.2, zorder=4)
    valid = np.flatnonzero(np.isfinite(model.fs_list))
    if mode == 'thd':
        threshold = model.fs_criterion if threshold is None else threshold
        if threshold is None or not np.isfinite(threshold):
            raise ValueError('Threshold plotting requires a finite threshold.')
        valid = valid[model.fs_list[valid] <= threshold]
    if mode in ('all', 'thd'):
        for j in valid:
            x, y = _arc(model, model.slips_circles[j])
            ax.plot(x, y+elevation_offset, color='#98ABB5', alpha=.5, lw=.5, zorder=2)
    if slices:
        for t, b in zip(top, bottom):
            ax.plot([t[0], b[0]], [t[1]+elevation_offset, b[1]+elevation_offset],
                    color='#687D8A', lw=.35, alpha=.55, zorder=2)
    x, y = _arc(model, circle)
    ax.plot(x, y+elevation_offset, color=RED, lw=1.35, zorder=5)
    ax.scatter([exit_[0], entry[0]], [exit_[1]+elevation_offset, entry[1]+elevation_offset],
               color=[INK, RED], s=13, zorder=6)
    # Extents include complete material polygons, not the circle's unused upper arc.
    bounds = np.array([p.bounds for p in model.strata_polys])
    xmin = min(surface[:,0].min(), bounds[:,0].min()) if full_material_extent else surface[:,0].min()
    xmax = max(surface[:,0].max(), bounds[:,2].max()) if full_material_extent else surface[:,0].max()
    ymin = (min(bottom[:,1].min(), bounds[:,1].min()) if full_material_extent else
            min(bottom[:,1].min(),surface[:,1].min())-.15*np.ptp(surface[:,1])) + elevation_offset
    ymax = (max(surface[:,1].max(), bounds[:,3].max()) if full_material_extent else surface[:,1].max()) + elevation_offset
    dx, dy = xmax-xmin, ymax-ymin
    ax.set_xlim(xmin-.025*dx, xmax+.025*dx)
    ax.set_ylim(ymin-.03*dy, ymax+.12*dy)
    ax.set_aspect('equal', adjustable='box')
    ax.grid(False)
    if annotate:
        ax.text(.02, .97, f'Minimum Fs = {fs:.3f}', ha='left', va='top', transform=ax.transAxes,
                fontsize=10, color=INK)
    if axis_labels:
        ax.set_xlabel('Horizontal distance (m)')
        ax.set_ylabel('Vertical coordinate (m)' if elevation_offset == 0 else 'Displayed elevation (m)')
    handles = [Patch(facecolor=c, edgecolor='#89959C', label=n) for n,c in zip(names,colors)]
    handles += [Line2D([],[],color=BLUE,lw=1.2,label='Surface'),
                Line2D([],[],color=RED,lw=1.35,label='Critical slip surface')]
    return handles


def plot_stability(model, mode='min', *, output='results/critical_surface', formats=('tif','pdf','svg','png'),
                    dpi=600, show=False, **kwargs):
    style()
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    fig.subplots_adjust(left=.11, right=.98, top=.95, bottom=.23)
    handles = draw_stability(ax, model, mode=mode, **kwargs)
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5,.015),
               ncol=min(3,len(handles)), frameon=False, fontsize=9)
    files = save_figure(fig, output, formats, dpi)
    if show:
        plt.show()
    plt.close(fig)
    return files


def plot_candidates(model, *, output='results/candidate_safety_factors', formats=('tif','pdf','svg','png'), dpi=600):
    style()
    fig, ax = plt.subplots(figsize=(5.2,3.5),layout='constrained')
    valid = np.flatnonzero(np.isfinite(model.fs_list))
    ax.scatter(valid+1, model.fs_list[valid], color=BLUE, s=17)
    index, _, fs = model.critical()
    ax.scatter([index+1],[fs],color=RED,s=32,zorder=3)
    if model.fs_criterion is not None:
        ax.axhline(model.fs_criterion,color=RED,ls='--',lw=.8,label=f'Criterion: Fs > {model.fs_criterion:.2f}')
        ax.legend(loc='best',frameon=False)
    ax.set_xlabel('Candidate index')
    ax.set_ylabel('Factor of safety, Fs')
    ax.text(.02,.98,f'{len(valid)} finite / {len(model.fs_list)} candidates',transform=ax.transAxes,
            va='top',fontsize=9)
    files = save_figure(fig,output,formats,dpi)
    plt.close(fig)
    return files


def plot_foundation(result, *, output='results/foundation_heights', formats=('tif','pdf','svg','png'), dpi=600):
    style()
    fig, ax = plt.subplots(figsize=(5.2,3.3),layout='constrained')
    values = [result['compression_height_m'], result['bearing_height_m']]
    ax.barh([1,0],values,color=[BLUE,'#A7B5BD'],height=.36)
    for y,v in zip([1,0],values):
        ax.text(v+max(values)*.015,y,f'{v:.3f}m',va='center',fontsize=10)
    adopted = result['adopted_height_m']
    ax.axvline(adopted,color=RED,lw=.8,ls='--')
    ax.set_yticks([1,0],['Compression','Bearing capacity'])
    ax.set_xlabel('Limiting dumping height (m)')
    ax.set_xlim(0,max(values)*1.24)
    ax.text(.03,.5,f'Adopted height:{adopted:g}m',transform=ax.transAxes,va='center',fontsize=9,color=RED)
    files = save_figure(fig,output,formats,dpi)
    plt.close(fig)
    return files


def export_plots(model, destination, **kwargs):
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    if not np.isfinite(model.fs_list).any():
        paths={'status':'no_finite_candidate'}
        if model.foundation_result is not None:
            paths['foundation']=plot_foundation(model.foundation_result,output=destination/'foundation_heights')
        (destination/'plots.json').write_text(json.dumps(paths,indent=2),encoding='utf-8')
        return paths
    paths = {'critical_surface': plot_stability(model, output=destination/'critical_surface', **kwargs),
             'candidate_factors': plot_candidates(model, output=destination/'candidate_safety_factors')}
    if model.foundation_result is not None:
        paths['foundation'] = plot_foundation(model.foundation_result,output=destination/'foundation_heights')
    (destination/'plots.json').write_text(json.dumps(paths,indent=2),encoding='utf-8')
    return paths
