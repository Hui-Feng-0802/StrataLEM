"""Parse external surface data and explicitly mapped material geometries."""
from pathlib import Path
import json
import numpy as np
from shapely.geometry import Polygon


def load_surface_csv(filename):
    surface = np.loadtxt(filename, delimiter=',')
    if (surface.ndim != 2 or surface.shape[1] != 2 or len(surface) < 3
            or not np.isfinite(surface).all() or np.any(np.diff(surface[:, 0]) <= 0)):
        raise ValueError('Surface CSV requires >=3 finite x,y pairs in strictly increasing x order.')
    return surface


def load_dxf_materials(filename, entity_indices=None):
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise RuntimeError('DXF input requires requirements-dxf.txt.') from exc
    entities = gpd.read_file(filename).geometry
    if entity_indices is None:
        entity_indices = range(len(entities))
    return [entities.iloc[int(i)].convex_hull for i in entity_indices]


def load_configuration(filename):
    path = Path(filename).resolve()
    cfg = json.loads(path.read_text(encoding="utf-8"))
    surface = load_surface_csv(path.parent / cfg["surface_csv"])
    if surface.ndim != 2 or surface.shape[1] != 2 or len(surface) < 3:
        raise ValueError("Surface CSV must contain at least three x,y coordinate pairs.")
    if not np.isfinite(surface).all() or np.any(np.diff(surface[:, 0]) < 0):
        raise ValueError("Surface coordinates must be finite and ordered by nondecreasing x.")
    materials = cfg["materials"]
    if not materials:
        raise ValueError("At least one material is required.")
    if "dxf" in cfg:
        try:
            import geopandas as gpd
        except ImportError as exc:
            raise RuntimeError("DXF input requires requirements-dxf.txt.") from exc
        entities = gpd.read_file(path.parent / cfg["dxf"]).geometry
        polys = [entities.iloc[int(m["dxf_entity"])].convex_hull for m in materials]
    else:
        polys = [Polygon(m["polygon"]) for m in materials]
    for poly in polys:
        if poly.geom_type != "Polygon" or not poly.is_valid or poly.area <= 0:
            raise ValueError("Material regions must be valid positive-area polygons.")
    params = np.asarray([[m["c"], m["phi"], m["gamma"]] for m in materials], dtype=float)
    if not np.isfinite(params).all() or np.any(params[:,0] < 0) or np.any(params[:,2] <= 0):
        raise ValueError("Material parameters must be finite; cohesion >= 0 and unit weight > 0.")
    if np.any((params[:,1] < 0) | (params[:,1] >= 90)):
        raise ValueError("Friction angle must be in [0,90) degrees.")
    return cfg, surface, polys, params
