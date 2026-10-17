from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import unittest
import numpy as np
from stratalem import (StrataLEM, Slope, FoundationInputs, FoundationClassification,
                      FoundationMaterialMap, SectionReference, calculate_foundation_height)
from stratalem.data_parsing import load_configuration
from stratalem.result_management import export_results


def paper_inputs():
    return FoundationInputs(e0=.564,a=1.2e-4,gamma1=18.5,c0=30,phi0=20,q=370,
        classification=FoundationClassification(e1=.4,dm=.6,beta=22,gamma0=21,thickness=10))


class FoundationTests(unittest.TestCase):
    def test_compression_formula(self):
        result=calculate_foundation_height(paper_inputs())
        expected=(1+.564)/(5*1.2e-4*18.5)
        self.assertAlmostEqual(result['compression_height_m'],expected,places=12)
        self.assertEqual(result['adopted_height_m'],140)

    def test_bearing_formula_full_precision(self):
        result=calculate_foundation_height(paper_inputs())
        nq=math.exp(math.pi*math.tan(math.radians(20)))*math.tan(math.radians(55))**2
        nc=(nq-1)/math.tan(math.radians(20))
        self.assertAlmostEqual(result['Nq'],nq,places=12)
        self.assertAlmostEqual(result['Nc'],nc,places=12)
        self.assertAlmostEqual(result['bearing_height_m'],(30*nc+370*nq)/18.5,places=12)
        self.assertAlmostEqual(result['bearing_height_m'],152.0441597913224,places=10)

    def test_printed_intermediate_factors_reproduce_reported_height(self):
        printed_path=(30*14.834+370*6.399)/18.5
        self.assertEqual(round(printed_path,3),152.035)

    def test_classification_matches_explicit_sum(self):
        result=calculate_foundation_height(paper_inputs())['classification']
        self.assertEqual(result['n'],3)
        h1=sum(.6*(.4/1.4)**i for i in range(1,4))
        self.assertAlmostEqual(result['h1_m'],h1,places=14)
        self.assertAlmostEqual(result['h0_m'],7.306079056408077,places=12)
        self.assertEqual(result['status'],'thick')

    def test_classification_is_not_forced(self):
        source=paper_inputs()
        result=calculate_foundation_height(replace(source,classification=replace(source.classification,thickness=1)))
        self.assertEqual(result['classification']['status'],'not_thick')
        self.assertTrue(result['issues'])

    def test_zero_friction_limit(self):
        result=calculate_foundation_height(replace(paper_inputs(),phi0=0))
        self.assertEqual(result['Nq'],1)
        self.assertAlmostEqual(result['Nc'],math.pi+2,places=14)

    def test_q_confirmation_requires_documentation(self):
        with self.assertRaises(ValueError):
            calculate_foundation_height(replace(paper_inputs(),q_basis_confirmed=True))

    def test_invalid_inputs_are_rejected(self):
        for changes in ({'a':0},{'a':-1},{'gamma1':0},{'e0':-1},{'phi0':60},
                        {'q':-1},{'c0':-1},{'height_step':0},
                        {'compression_fraction':1},{'e0':float('nan')}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                calculate_foundation_height(replace(paper_inputs(),**changes))

    def test_minimum_can_be_bearing_controlled(self):
        result=calculate_foundation_height(replace(paper_inputs(),q=0))
        self.assertEqual(result['controlling_method'],'bearing_capacity')
        self.assertLessEqual(result['adopted_height_m'],result['bearing_height_m'])

    def test_classification_can_be_skipped(self):
        result=calculate_foundation_height(replace(paper_inputs(),classification=None))
        self.assertEqual(result['classification']['status'],'not_evaluated')


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).resolve().parents[1]/'examples/demo.json'
        cls.cfg,cls.coords,cls.polys,cls.params=load_configuration(path)
        cls.base=StrataLEM(cls.coords,cls.polys,cls.params,**cls.cfg['search'])

    def integrated(self,**kwargs):
        options=dict(foundation=FoundationInputs(e0=.564,a=1.2e-4,gamma1=19,
            c0=12,phi0=28,q=370,
            classification=FoundationClassification(.4,.6,45,19,10),
            q_basis='Independent synthetic test surcharge.',q_basis_confirmed=True),
            section_reference=SectionReference(1,4,target_base=0,target_crest=24),
            foundation_material_map=FoundationMaterialMap(0,0),fs_criterion=.5)
        options.update(kwargs)
        return StrataLEM(self.coords,self.polys,self.params,**self.cfg['search'],**options)

    def test_stability_only_does_not_require_foundation_inputs(self):
        self.assertIsNone(self.base.foundation_result)
        self.assertEqual(self.base.assessment()['mode'],'stability_only')

    def test_integrated_preprocessor_does_not_change_fs_or_geometry(self):
        model=self.integrated()
        np.testing.assert_equal(model.slips_circles,self.base.slips_circles)
        np.testing.assert_equal(model.fs_list,self.base.fs_list)
        np.testing.assert_equal(model.slope_coords,self.coords)
        self.assertEqual(model.assessment()['status'],'meets_adopted_numerical_criteria')

    def test_original_constructor_retained(self):
        model=Slope(self.coords,self.polys,self.params,15,50,15,entry_segment=-2)
        np.testing.assert_equal(model.fs_list,self.base.fs_list)
        np.testing.assert_equal(model.slips_circles,self.base.slips_circles)

    def test_target_geometry_mismatch_is_recorded(self):
        model=self.integrated(section_reference=SectionReference(1,4,target_base=0,target_crest=140))
        self.assertIn('target_geometry_mismatch',model.assessment()['reasons'])
        self.assertEqual(model.assessment()['section']['actual_dumping_height_m'],24)
        np.testing.assert_equal(model.slope_coords,self.coords)

    def test_exceeding_height_is_recorded(self):
        model=self.integrated(foundation=replace(paper_inputs(),a=.01))
        self.assertIn('foundation_height_exceeded',model.assessment()['reasons'])

    def test_missing_reference_does_not_pass(self):
        model=self.integrated(section_reference=None)
        self.assertIn('section_reference_missing',model.assessment()['reasons'])
        self.assertIsNone(model.assessment()['height_within_adopted_limit'])

    def test_material_mismatch_does_not_pass(self):
        model=self.integrated(foundation=paper_inputs())
        self.assertIn('foundation_material_mismatch',model.assessment()['reasons'])

    def test_unconfirmed_q_does_not_pass(self):
        model=self.integrated()
        source=FoundationInputs(**{k:v for k,v in model.foundation_result['inputs'].items() if k!='classification'},
                                classification=FoundationClassification(.4,.6,45,19,10))
        model=self.integrated(foundation=replace(source,q_basis_confirmed=False))
        self.assertIn('q_basis_unconfirmed',model.assessment()['reasons'])

    def test_stability_threshold_is_strict(self):
        model=self.integrated(fs_criterion=self.base.critical()[2])
        self.assertFalse(model.assessment()['stability_criterion_met'])

    def test_invalid_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            self.integrated(section_reference=SectionReference(4,1))

    def test_relative_vertical_datum_is_explicit(self):
        model=self.integrated(section_reference=SectionReference(1,4,elevation_offset=700,
                                target_base=700,target_crest=724))
        self.assertTrue(model.section_check['target_elevations_match'])
        self.assertEqual(model.section_check['actual_dumping_height_m'],24)

    def test_export_contains_all_stages(self):
        with tempfile.TemporaryDirectory() as folder:
            report=export_results(self.integrated(),self.cfg,folder)
            self.assertTrue((Path(folder)/'foundation.json').exists())
            self.assertEqual(json.loads((Path(folder)/'summary.json').read_text())['assessment']['mode'],
                             'foundation_and_stability')
            self.assertEqual(report['assessment']['status'],'meets_adopted_numerical_criteria')

    def test_numpy_elevation_scalars_export(self):
        model=self.integrated(section_reference=SectionReference(1,4,
            target_base=np.float64(0),target_crest=np.float64(24)))
        with tempfile.TemporaryDirectory() as folder:
            export_results(model,self.cfg,folder)

    def test_no_finite_candidate_has_an_explicit_report(self):
        model=self.integrated()
        model.fs_list[:]=np.nan
        with tempfile.TemporaryDirectory() as folder:
            report=export_results(model,self.cfg,folder)
            self.assertIsNone(report['minimum_factor_of_safety'])
            self.assertIn('no_finite_stability_result',report['assessment']['reasons'])

    def test_inactive_stage_does_not_leave_stale_foundation_results(self):
        with tempfile.TemporaryDirectory() as folder:
            export_results(self.integrated(),self.cfg,folder)
            export_results(self.base,self.cfg,folder)
            stage=json.loads((Path(folder)/'foundation.json').read_text())
            self.assertEqual(stage,{'status':'not_performed','mode':'stability_only'})


if __name__=='__main__':
    unittest.main()
