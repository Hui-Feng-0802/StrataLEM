from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
from stratalem.data_parsing import load_configuration
from stratalem import StrataLEM, FoundationInputs, calculate_foundation_height
from stratalem.plotting import plot_foundation, plot_candidates


class PlottingTests(unittest.TestCase):
    def setUp(self):
        _,coords,polys,params=load_configuration(Path(__file__).resolve().parents[1]/'examples/demo.json')
        self.model=StrataLEM(coords,polys,params,entry_segment=-2)

    def test_original_plot_call_exports_tiff_and_vectors(self):
        before=self.model.fs_list.copy()
        with tempfile.TemporaryDirectory() as d:
            files=self.model.plot('min',output=Path(d)/'critical',dpi=300)
            self.assertEqual(len(files),4)
            with Image.open(Path(d)/'critical.tif') as im:
                self.assertEqual(im.mode,'RGB')
                self.assertEqual(im.info['compression'],'tiff_lzw')
                self.assertEqual(tuple(map(float,im.info['dpi'])),(300.,300.))
            self.assertTrue((Path(d)/'critical.pdf').exists())
            self.assertTrue((Path(d)/'critical.svg').exists())
        np.testing.assert_equal(before,self.model.fs_list)

    def test_all_and_threshold_modes(self):
        with tempfile.TemporaryDirectory() as d:
            self.model.plot('all',output=Path(d)/'all',formats=('pdf',))
            self.model.plot('thd',threshold=1.20,output=Path(d)/'thd',formats=('pdf',))
            self.assertTrue((Path(d)/'thd.pdf').exists())

    def test_foundation_and_candidate_outputs(self):
        r=calculate_foundation_height(FoundationInputs(e0=.564,a=.00012,gamma1=18.5,c0=30,phi0=20,q=370))
        with tempfile.TemporaryDirectory() as d:
            plot_foundation(r,output=Path(d)/'height',formats=('pdf',))
            plot_candidates(self.model,output=Path(d)/'candidates',formats=('pdf',))
            self.assertTrue((Path(d)/'height.pdf').exists())

    def test_no_finite_candidate_records_status(self):
        self.model.fs_list[:]=np.nan
        with tempfile.TemporaryDirectory() as d:
            result=self.model.save_plots(d)
            self.assertEqual(result['status'],'no_finite_candidate')

if __name__=='__main__':unittest.main()
