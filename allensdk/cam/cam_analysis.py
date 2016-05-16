# Copyright 2016 Allen Institute for Brain Science
# This file is part of Allen SDK.
#
# Allen SDK is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# Allen SDK is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Allen SDK.  If not, see <http://www.gnu.org/licenses/>.

from allensdk.cam.static_grating import StaticGrating
from allensdk.cam.locally_sparse_noise import LocallySparseNoise
from allensdk.cam.natural_scenes import NaturalScenes
from allensdk.cam.drifting_grating import DriftingGrating
from allensdk.cam.natural_movie import NaturalMovie

from allensdk.core.cam_nwb_data_set import CamNwbDataSet

import allensdk.cam.cam_plotting as cp
import argparse, logging, os
import sys
import numpy as np

def multi_dataframe_merge(dfs):
    out_df = None
    for i,df in enumerate(dfs):
        if out_df is None:
            out_df = df
        else:
            out_df = out_df.merge(df, left_index=True, right_index=True, suffixes=['','_%d' % i])
    return out_df

class CamAnalysis(object):
    _log = logging.getLogger('allensdk.cam.cam_analysis')    
    SESSION_A = 'three_session_A'
    SESSION_B = 'three_session_B'
    SESSION_C = 'three_session_C'

    def __init__(self, nwb_path, save_path, metadata=None):
        self.nwb = CamNwbDataSet(nwb_path)                        
        self.save_path = save_path

        self.metrics_a = {}
        self.metrics_b = {}
        self.metrics_c = {}

        if metadata is None:
            metadata = {}

        self.metadata = self.nwb.get_metadata()
        for k,v in metadata.iteritems():
            self.metadata[k] = v

    def append_metadata(self, df):
        for k,v in self.metadata.iteritems():
            df[k] = v

    def save_session_a(self, dg, nm1, nm3, peak):
        nwb = CamNwbDataSet(self.save_path)
        nwb.save_analysis_dataframes(
            ('stim_table_dg', dg.stim_table),
            ('sweep_response_dg', dg.sweep_response),
            ('mean_sweep_response_dg', dg.mean_sweep_response),
            ('peak', peak),        
            ('sweep_response_nm1', nm1.sweep_response),
            ('stim_table_nm1', nm1.stim_table),
            ('sweep_response_nm3', nm3.sweep_response))
        
        nwb.save_analysis_arrays(
            ('celltraces_dff', nm1.celltraces_dff),
            ('response_dg', dg.response),
            ('binned_cells_sp', nm1.binned_cells_sp),
            ('binned_cells_vis', nm1.binned_cells_vis),
            ('binned_dx_sp', nm1.binned_dx_sp),
            ('binned_dx_vis', nm1.binned_dx_vis))
    
        
    def save_session_b(self, sg, nm1, ns, peak): 
        nwb = CamNwbDataSet(self.save_path)
        nwb.save_analysis_dataframes(
            ('stim_table_sg', sg.stim_table),
            ('sweep_response_sg', sg.sweep_response),
            ('mean_sweep_response_sg', sg.mean_sweep_response),
            ('sweep_response_nm1', nm1.sweep_response),
            ('stim_table_nm1', nm1.stim_table),
            ('sweep_response_ns', ns.sweep_response),
            ('stim_table_ns', ns.stim_table),
            ('mean_sweep_response_ns', ns.mean_sweep_response),
            ('peak', peak))

        nwb.save_analysis_arrays(
            ('celltraces_dff', nm1.celltraces_dff),
            ('response_sg', sg.response),
            ('response_ns', ns.response),
            ('binned_cells_sp', nm1.binned_cells_sp),
            ('binned_cells_vis', nm1.binned_cells_vis),
            ('binned_dx_sp', nm1.binned_dx_sp),
            ('binned_dx_vis', nm1.binned_dx_vis))
    
    
    def save_session_c(self, lsn, nm1, nm2, peak):                
        nwb = CamNwbDataSet(self.save_path)
        nwb.save_analysis_dataframes(
            ('stim_table_lsn', lsn.stim_table),
            ('sweep_response_nm1', nm1.sweep_response),
            ('peak', peak),
            ('sweep_response_nm2', nm2.sweep_response),
            ('sweep_response_lsn', lsn.sweep_response),
            ('mean_sweep_response_lsn', lsn.mean_sweep_response))  
        
        nwb.save_analysis_arrays(
            ('receptive_field_lsn', lsn.receptive_field),
            ('celltraces_dff', nm1.celltraces_dff),
            ('binned_dx_sp', nm1.binned_dx_sp),
            ('binned_dx_vis', nm1.binned_dx_vis),    
            ('binned_cells_sp', nm1.binned_cells_sp),
            ('binned_cells_vis', nm1.binned_cells_vis))
    
    def append_metrics_drifting_grating(self, metrics, dg):
        metrics["osi_dg"] = dg.peak["osi_dg"]
        metrics["dsi_dg"] = dg.peak["dsi_dg"]
        metrics["pref_dir_dg"] = [ dg.orivals[i] for i in dg.peak["ori_dg"].values ]
        metrics["pref_tf_dg"] = [ dg.tfvals[i] for i in dg.peak["tf_dg"].values ]
        metrics["p_dg"] = dg.peak["ptest_dg"]
    
    def append_metrics_static_grating(self, metrics, sg):
        metrics["osi_sg"] = sg.peak["osi_sg"]
        metrics["pref_ori_sg"] = [ sg.orivals[i] for i in sg.peak["ori_sg"].values ]
        metrics["pref_sf_sg"] = [ sg.sfvals[i] for i in sg.peak["sf_sg"].values ]
        metrics["pref_phase_sg"] = [ sg.phasevals[i] for i in sg.peak["phase_sg"].values ]
        metrics["p_sg"] = sg.peak["ptest_sg"]
        metrics["time_to_peak_sg"] = sg.peak["time_to_peak_sg"]

    def append_metrics_natural_scene(self, metrics, ns):
        metrics["pref_image_ns"] = ns.peak["scene_ns"]
        metrics["p_ns"] = ns.peak["ptest_ns"]
        metrics["time_to_peak_ns"] = ns.peak["time_to_peak_ns"]

    def verify_roi_lists_equal(self, roi1, roi2):
        if len(roi1) != len(roi2):
            raise CamAnalysisException("Error -- ROI lists are of different length")
        for i in range(len(roi1)):
            if roi1[i] != roi2[i]:
                raise CamAnalysisException("Error -- ROI lists have different entries")
    
    def session_a(self, plot_flag=False, save_flag=True):
        nm1 = NaturalMovie(self, 'natural_movie_one')      
        nm3 = NaturalMovie(self, 'natural_movie_three')    
        dg = DriftingGrating(self)

        CamAnalysis._log.info("Session A analyzed")
        peak = multi_dataframe_merge([nm1.peak_run, dg.peak, nm1.peak, nm3.peak])
        

        self.append_metrics_drifting_grating(self.metrics_a, dg)
        self.metrics_a["roi_id"] = dg.roi_id

        self.append_metadata(peak)

        if plot_flag:
            cp.plot_3sa(dg, nm1, nm3)
            cp.plot_drifting_grating_traces(dg)
    
        if save_flag:
            self.save_session_a(dg, nm1, nm3, peak)
    
    def session_b(self, plot_flag=False, save_flag=True):
        sg = StaticGrating(self)    
        ns = NaturalScenes(self)
        nm1 = NaturalMovie(self, 'natural_movie_one')            
        CamAnalysis._log.info("Session B analyzed")
        peak = multi_dataframe_merge([nm1.peak_run, sg.peak, ns.peak, nm1.peak])
        self.append_metadata(peak)

        self.append_metrics_static_grating(self.metrics_b, sg)
        self.append_metrics_natural_scene(self.metrics_b, ns)
        self.verify_roi_lists_equal(sg.roi_id, ns.roi_id)
        self.metrics_b["roi_id"] = sg.roi_id
                
        if plot_flag:
            cp.plot_3sb(sg, nm1, ns)
            cp.plot_ns_traces(ns)
            cp.plot_sg_traces(sg)
                    
        if save_flag:
            self.save_session_b(sg, nm1, ns, peak)
    
    def session_c(self, plot_flag=False, save_flag=True):
        lsn = LocallySparseNoise(self)
        nm2 = NaturalMovie(self, 'natural_movie_two')
        nm1 = NaturalMovie(self, 'natural_movie_one')
        CamAnalysis._log.info("Session C analyzed")
        peak = multi_dataframe_merge([nm1.peak_run, nm1.peak, nm2.peak])
        self.append_metadata(peak)
                
        #self.append_metrics_natural_scene(self.metrics_c, nm1)
        self.metrics_c["roi_id"] = nm1.roi_id
                
        if plot_flag:
            cp.plot_3sc(lsn, nm1, nm2)
            cp.plot_lsn_traces(lsn)
    
        if save_flag:
            self.save_session_c(lsn, nm1, nm2, peak)
    
                    
def run_cam_analysis(session, nwb_path, save_path, metadata=None, plot_flag=False):
    save_dir = os.path.dirname(save_path)

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    cam_analysis = CamAnalysis(nwb_path, save_path, metadata)
    try:
        session = cam_analysis.nwb.get_session_type()
        print("** Able to read session type from NWB file. Deprecate 'session' argument from run_cam_analysis()")
    except:
        pass

    if session == CamAnalysis.SESSION_A:
        cam_analysis.session_a(plot_flag)
        metrics = cam_analysis.metrics_a
    elif session == CamAnalysis.SESSION_B:
        cam_analysis.session_b(plot_flag)
        metrics = cam_analysis.metrics_b
    elif session == CamAnalysis.SESSION_C:
        cam_analysis.session_c(plot_flag)
        metrics = cam_analysis.metrics_c
    else:
        raise IndexError("Unknown session: %s" % session)

    return metrics
    
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_nwb", required=True)
    parser.add_argument("--output_nwb", default=None)

    # TODO: unhardcode
    parser.add_argument("--session", default=CamAnalysis.SESSION_A)
    parser.add_argument("--plot", action='store_true')

    # meta data
    # TODO: remove
    parser.add_argument("--depth", type=int, default=None)
    parser.add_argument("--experiment_id", type=int, default=None)
    parser.add_argument("--area", type=str, default=None)

    args = parser.parse_args()

    if args.output_nwb is None:
        args.output_nwb = args.input_nwb

    metadata = {}
    if args.experiment_id is not None:
        metadata['experiment_id'] = args.experiment_id
    if args.area is not None:
        metadata['area'] = args.area
    if args.depth is not None:
        metadata['depth'] = args.depth

    run_cam_analysis(args.session, args.input_nwb, args.output_nwb, metadata, args.plot)


if __name__=='__main__': main()
    
