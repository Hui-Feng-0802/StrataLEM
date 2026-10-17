"""Run a single configured stability analysis."""
import argparse
import json
from .data_parsing import load_configuration
from .framework import StrataLEM
from .result_management import export_results
from .foundation import FoundationInputs, FoundationClassification, FoundationMaterialMap
from .section_checks import SectionReference


def main():
    parser=argparse.ArgumentParser(description='StrataLEM layered-slope stability analysis')
    parser.add_argument('--config',required=True,help='JSON configuration file')
    parser.add_argument('--output',default='results/case',help='Output directory')
    args=parser.parse_args()
    cfg,coords,polys,params=load_configuration(args.config)
    foundation=cfg.get('foundation')
    if foundation is not None:
        foundation=dict(foundation)
        if foundation.get('classification') is not None:
            foundation['classification']=FoundationClassification(**foundation['classification'])
        foundation=FoundationInputs(**foundation)
    reference=cfg.get('section_reference')
    reference=None if reference is None else SectionReference(**reference)
    mapping=cfg.get('foundation_material_map')
    mapping=None if mapping is None else FoundationMaterialMap(**mapping)
    model=StrataLEM(coords,polys,params,slices=cfg.get('slices',50),
                    foundation=foundation,section_reference=reference,
                    fs_criterion=cfg.get('fs_criterion'),foundation_material_map=mapping,
                    **cfg.get('search',{}))
    print(json.dumps(export_results(model,cfg,args.output),indent=2,allow_nan=False))
    if cfg.get('plots', True):
        model.save_plots(args.output)


if __name__=='__main__':
    main()
