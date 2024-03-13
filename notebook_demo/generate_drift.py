import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path


import probeinterface
import probeinterface.plotting

import spikeinterface.full as si
from spikeinterface.core.generate import generate_unit_locations

from spikeinterface.generation import interpolate_templates, move_dense_templates, DriftingTemplates, make_linear_displacement, InjectDriftingTemplatesRecording
from spikeinterface.core.generate import generate_templates, generate_unit_locations
from spikeinterface.core import Templates


from spikeinterface.generation.tests.test_drift_tools import make_some_templates

from probeinterface.plotting import plot_probe

from spikeinterface.generation import interpolate_templates, move_dense_templates, DriftingTemplates
from spikeinterface.core.generate import generate_templates, default_unit_params_range
from spikeinterface.core import Templates



def generate_drift_on_tetrode(num_units=5, drift_amplitude=20., duration=300., noise_level=5., seed=2406):
    rng = np.random.default_rng(seed=seed)

    sampling_frequency = 30000.
    ms_before = 1.
    ms_after = 3.

    nbefore = int(sampling_frequency * ms_before / 1000.)

    probe = probeinterface.generate_tetrode()
    probe.set_device_channel_indices(np.arange(probe.get_contact_count()))

    channel_locations = probe.contact_positions

    

    unit_locations = generate_unit_locations(
        num_units,
        channel_locations,
        margin_um=20.0,
        minimum_z=5.0,
        maximum_z=35.0,
        minimum_distance=20.0,
        max_iteration=100,
        distance_strict=False,
        seed=seed,
    )

    channel_locations = probe.contact_positions

    if drift_amplitude > 0:
        start = np.array([0, -drift_amplitude/2])
        stop = np.array([0, drift_amplitude/2])
        num_step = int(drift_amplitude) * 2 + 1
        # print('num_step', num_step)
        displacements = make_linear_displacement(start, stop, num_step=num_step)
    else:
        displacements = np.zeros((1, 2))
        start = np.array([0, 0])
        stop = np.array([0, 0])

    # print(displacements.shape)

    

    unit_params = dict()

    my_unit_params_range=dict(
        alpha=(8_000., 14_000.),
    )

    for k in default_unit_params_range.keys():
        if k in my_unit_params_range:
            lims = my_unit_params_range[k]
        else:
            lims = default_unit_params_range[k]
        lim0, lim1 = lims
        v = rng.random(num_units)
        unit_params[k] = v * (lim1 - lim0) + lim0

    generate_templates_kwargs = dict(
        sampling_frequency=sampling_frequency,
        ms_before=ms_before,
        ms_after=ms_after,
        seed=seed,
        unit_params=unit_params
    )
    templates_array = si.generate_templates(channel_locations, unit_locations, **generate_templates_kwargs)

    num_displacement = displacements.shape[0]
    templates_array_moved = np.zeros(shape=(num_displacement, ) + templates_array.shape, dtype=templates_array.dtype)
    for i in range(num_displacement):
        unit_locations_moved = unit_locations.copy()
        unit_locations_moved[:, :2] += displacements[i, :][np.newaxis, :]
        templates_array_moved[i, :, :, :] = si.generate_templates(channel_locations, unit_locations_moved, **generate_templates_kwargs)

    templates = si.Templates(
        templates_array=templates_array,
        sampling_frequency=sampling_frequency,
        nbefore=nbefore,
        probe=probe,
    )

    # fig, ax = plt.subplots()
    # probeinterface.plotting.plot_probe(probe, ax=ax)
    # ax.scatter(unit_locations[:, 0], unit_locations[:, 1], marker='*')
    # plt.show()

    drifting_templates = DriftingTemplates.from_static(templates)

    firing_rates_range = (1., 8.)
    lim0, lim1 = firing_rates_range
    firing_rates = rng.random(num_units) * (lim1 - lim0) + lim0    

    sorting = si.generate_sorting(
        num_units=num_units,
        sampling_frequency=sampling_frequency,
        durations = [duration,],
        firing_rates=firing_rates,
        seed=seed)


    displacement_sampling_frequency = 5.

    times = np.arange(0, duration, 1 / displacement_sampling_frequency)
    times

    mid = (start + stop) / 2
    freq0 = 0.01
    displacement_vector0 = np.sin(2 * np.pi * freq0 *times)[:, np.newaxis] * (start - stop) / 2 + mid
    displacement_vectors = displacement_vector0[:, :, np.newaxis]


    num_unit = sorting.unit_ids.size
    num_motion = displacement_vectors.shape[2]

    displacement_unit_factor = np.zeros((num_unit, num_motion))
    displacement_unit_factor[:, 0] = 1


    # fig, ax = plt.subplots()
    # ax.plot(times, displacement_vector0[:, 0], label='x0')
    # ax.plot(times, displacement_vector0[:, 1], label='y0')
    # ax.legend()
    # plt.show()

    ## Important precompute displacement do not work on border and so do not work for tetrode
    # here we bypass the interpolation and regenrate templates at severals positions.
    ## drifting_templates.precompute_displacements(displacements)
    # shape (num_displacement, num_templates, num_samples, num_channels)
    drifting_templates.templates_array_moved = templates_array_moved
    drifting_templates.displacements = displacements

    noise = si.NoiseGeneratorRecording(
        num_channels=probe.get_contact_count(),
        sampling_frequency=sampling_frequency,
        durations=[duration],
        noise_level=noise_level,
        dtype="float32",
        strategy="on_the_fly",
    )

    recording = InjectDriftingTemplatesRecording(
        sorting=sorting,
        parent_recording=noise,
        drifting_templates=drifting_templates,
        displacement_vectors=[displacement_vectors],
        displacement_sampling_frequency=displacement_sampling_frequency,
        displacement_unit_factor=displacement_unit_factor,
        num_samples=[int(duration*sampling_frequency)],
        amplitude_factor=None,
    )

    return recording, sorting



if __name__ == "__main__":
    import shutil

    base_folder = Path("/home/samuel/DataSpikeSorting/WIRED_SI_tutos/")
    folder = base_folder / "generated_recording"

    recording_drift, sorting = generate_drift_on_tetrode(drift_amplitude=0., duration=300., noise_level=5., seed=2205)

    # si.plot_traces(recording_drift, backend='ephyviewer')



    sorter_name = "tridesclous2"

    sorter_folder = folder / f"drift_{sorter_name}"
    if sorter_folder.exists():
        shutil.rmtree(sorter_folder)

    job_kwargs = dict(n_jobs=-1)

    sorting_tdc_drift = si.run_sorter(sorter_name, recording_drift, output_folder=sorter_folder, verbose=True, job_kwargs=job_kwargs, raise_error=True)



    tdc_analyzer_drift = si.create_sorting_analyzer(sorting_tdc_drift, recording_drift, sparse=False)
    tdc_analyzer_drift.compute(["random_spikes", "waveforms", "templates", "noise_levels"], **job_kwargs)
    tdc_analyzer_drift.compute(["spike_amplitudes", "unit_locations", "principal_components", "correlograms", "template_similarity"], **job_kwargs)
    tdc_analyzer_drift.compute("quality_metrics", metric_names=["snr", "amplitude_cutoff", "rp_violation"])
    tdc_analyzer_drift

    si.plot_sorting_summary(tdc_analyzer_drift, backend="spikeinterface_gui")



    