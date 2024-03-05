from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

import probeinterface

import spikeinterface.full as si


base_folder = Path("/home/samuel/DataSpikeSorting/WIRED/")


# probe_type = "AdTech"
# subject_id = "sub-001"
# session_id = "sess-001"

# probe_type = "AdTech"
# subject_id = "sub-002"
# session_id = "sess-001"

probe_type ="DIXI"
subject_id = "sub-003"
session_id = "sess-001"

# probe_type ="DIXI"
# subject_id = "sub-004"
# session_id = "sess-001"




rec_folder = base_folder / "Binary" / probe_type / subject_id / session_id / "ieeg"

rec = si.load_extractor(rec_folder)


probe = probeinterface.generate_tetrode()
probe.set_device_channel_indices(np.arange(4))
rec = rec.set_probe(probe)
rec

rec = si.bandpass_filter(rec, freq_min=150., freq_max=10000.)

si.plot_traces(rec, backend="ephyviewer")

