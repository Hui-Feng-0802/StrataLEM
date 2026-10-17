import json
import math
from pathlib import Path
import unittest
import numpy as np
from shapely.geometry import Polygon
from stratalem.data_parsing import load_configuration
from stratalem.framework import StrataLEM
from stratalem.result_management import critical_slice_records


class StrataLEMTests(unittest.TestCase):
    def setUp(self):
        p=Path(__file__).resolve().parents[1]/'examples/demo.json'
        self.cfg,self.coords,self.polys,self.params=load_configuration(p)
        self.model=StrataLEM(self.coords,self.polys,self.params,slices=50,**self.cfg['search'])

    def test_candidate_and_slice_counts(self):
        self.assertEqual(len(self.model.slips_circles),60)
        self.assertEqual(len(critical_slice_records(self.model)),50)

    def test_deterministic_candidate_mapping(self):
        second=StrataLEM(self.coords,self.polys,self.params,slices=50,**self.cfg['search'])
        np.testing.assert_equal(second.fs_list,self.model.fs_list)
        np.testing.assert_equal(second.slips_circles,self.model.slips_circles)

    def test_force_reassembly(self):
        rows=critical_slice_records(self.model)
        ratio=sum(r['resisting'] for r in rows)/sum(r['driving'] for r in rows)
        self.assertAlmostEqual(ratio,self.model.critical()[2],places=12)

    def test_homogeneous_closed_form(self):
        row=np.empty((1,1),dtype=object)
        row[0,0]=Polygon([(0,0),(3,0),(3,2),(0,2)])
        bottom=np.asarray([[0,0],[3,4]],dtype=float)
        params=np.asarray([[12,28,19]],dtype=float)
        value=self.model._claculate_fs_ordinary(row,bottom,params)
        weight=6*19;alpha=math.atan2(4,3)
        expected=(12*5+weight*math.cos(alpha)*math.tan(math.radians(28)))/(weight*math.sin(alpha))
        self.assertAlmostEqual(value,expected,places=12)


if __name__=='__main__':unittest.main()
