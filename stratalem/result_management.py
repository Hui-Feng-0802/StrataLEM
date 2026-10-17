"""Export candidate and critical-slice records without hardcoded result values."""
from pathlib import Path
import csv
import json
import math
import numpy as np
from shapely.geometry import Point, Polygon


def _json_numeric(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Cannot encode {type(value).__name__} as a result value.")


def critical_slice_records(model):
    _, circle, _ = model.critical()
    top,bottom,areas = model._generate_slices(
        model._entry_points[int(circle[0])],model._exit_points[int(circle[1])],
        circle[3:],model.slope_coords,model.strata_polys,model._slices_pieces_num)
    records=[]
    for i,row in enumerate(areas):
        indices = np.argwhere(row != None).flatten()
        weights=[model.strata_args[k,2]*row[k].area for k in indices]
        weight=float(sum(weights))
        p1,p2=bottom[i],bottom[i+1]
        dx,dy=p2-p1
        alpha=math.atan2(float(dy),float(dx));length=float(np.hypot(dx,dy))
        midpoint=0.5*(p1+p2)
        k=model._determine_stratum(midpoint,indices,row)
        strict=[int(j) for j in indices if row[j].contains(Point(midpoint))]
        assignment='strict_contains' if strict else ('no_material' if k is None else 'last_intersected_fallback')
        slice_polygon=Polygon([top[i],top[i+1],bottom[i+1],bottom[i]])
        if not slice_polygon.is_valid:
            slice_polygon=slice_polygon.buffer(0)
        slice_area=float(slice_polygon.area)
        covered=float(sum(row[j].area for j in indices))
        if k is None:
            resisting=driving=0.0
        else:
            c,phi=model.strata_args[k,0],math.radians(model.strata_args[k,1])
            resisting=float(c*length+weight*math.cos(alpha)*math.tan(phi))
            driving=float(weight*math.sin(alpha))
        records.append({'slice':i+1,'weight':weight,'base_length':length,
                        'base_angle_radians':alpha,'basal_material':None if k is None else int(k),
                        'basal_assignment':assignment,'slice_area':slice_area,
                        'summed_material_area':covered,
                        'area_balance_error':covered-slice_area,
                        'resisting':resisting,'driving':driving})
    return records


def export_results(model, config, destination):
    out=Path(destination);out.mkdir(parents=True,exist_ok=True)
    finite=np.isfinite(model.fs_list).any()
    i,circle,fs=model.critical() if finite else (None,None,None)
    payload={'minimum_factor_of_safety':fs,'critical_candidate':i,
             'valid_candidates':int(np.isfinite(model.fs_list).sum()),
             'total_candidates':len(model.fs_list),'slices':model._slices_pieces_num,
             'center_x':None if circle is None else float(circle[3]),
             'center_y':None if circle is None else float(circle[4]),
             'radius':None if circle is None else float(circle[5]),
             'search':config.get('search',{}),'geometry_units':'m',
             'force_units':'kN per unit out-of-plane thickness',
             'assessment':model.assessment(),'foundation':model.foundation_result}
    (out/'summary.json').write_text(json.dumps(payload,indent=2,allow_nan=False,default=_json_numeric),encoding='utf-8')
    with (out/'candidates.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['candidate','entry_index','exit_index','sagitta_index','center_x','center_y','radius','geometric_filter','factor_of_safety'])
        for j,(c,value) in enumerate(zip(model.slips_circles,model.fs_list)):
            writer.writerow([j,int(c[0]),int(c[1]),int(c[2]),*map(float,c[3:]),model.geometric_filter[j],float(value) if np.isfinite(value) else ''])
    records=critical_slice_records(model) if finite else []
    with (out/'critical_slices.csv').open('w',newline='',encoding='utf-8') as f:
        fields=records[0].keys() if records else ['slice','weight','base_length','base_angle_radians','basal_material','basal_assignment','slice_area','summed_material_area','area_balance_error','resisting','driving']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(records)
    stage=model.foundation_result if model.foundation_result is not None else {'status':'not_performed','mode':'stability_only'}
    (out/'foundation.json').write_text(json.dumps(stage,indent=2,allow_nan=False,default=_json_numeric),encoding='utf-8')
    return payload
