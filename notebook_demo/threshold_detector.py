from spikeinterface.sortingcomponents.peak_detection import PeakDetectorWrapper
from spikeinterface.core import get_noise_levels
import numpy as np

class DetectThresholdCrossing(PeakDetectorWrapper):
    
    name = "threshold_crossings"
    preferred_mp_context = None
    
    @classmethod
    def check_params(
        cls,
        recording,
        detect_threshold=5,
        noise_levels=None,
        random_chunk_kwargs={},
    ):
        if noise_levels is None:
            noise_levels = get_noise_levels(recording, return_scaled=False, **random_chunk_kwargs)
        abs_thresholds = noise_levels * detect_threshold
        return (abs_thresholds, )

    @classmethod
    def get_method_margin(cls, *args):
        return 0

    @classmethod
    def detect_peaks(cls, traces, abs_thresholds):
        z =  (traces - abs_thresholds).mean(1)
        threshold_mask = np.diff((z > 0) != 0)
        indices,  = np.where(threshold_mask)
        peak_sample_ind = np.zeros(0, dtype=np.int64)
        peak_chan_ind = np.zeros(0, dtype=np.int64)
        onsets = indices[:-1]
        offsets = indices[1:]
        peak_sample_ind = np.concatenate((peak_sample_ind, onsets))
        peak_chan_ind = np.concatenate((peak_chan_ind, np.zeros(len(onsets), dtype=np.int64)))
        peak_sample_ind = np.concatenate((peak_sample_ind, offsets))
        peak_chan_ind = np.concatenate((peak_chan_ind, np.ones(len(offsets), dtype=np.int64)))
        return peak_sample_ind, peak_chan_ind


def detect_artefacts(enveloppe, detect_threshold=5, **job_kwargs):

    from spikeinterface.core.node_pipeline import (
        run_node_pipeline,
    )

    node0 = DetectThresholdCrossing(enveloppe, **{'detect_threshold' : detect_threshold})
    
    times = run_node_pipeline(
        enveloppe,
        [node0],
        job_kwargs,
        job_name="detecting threshold crossings",
        )

    mask = times["channel_index"] == 0
    onsets = times[mask]

    mask = times["channel_index"] == 1
    offsets = times[mask]
    
    periods = []
    
    if onsets['sample_index'][0] > offsets['sample_index'][0]:
        periods += [(0, offsets['sample_index'][0])]
        offsets = offsets[1:]
    
    for i in range(len(onsets)):
        periods += [(onsets['sample_index'][i], offsets['sample_index'][i])]

    if len(onsets) > len(offsets):
        periods += [(onsets['sample_index'][0], enveloppe.get_num_samples())]

    return periods
