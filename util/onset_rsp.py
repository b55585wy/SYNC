import numpy as np


def find_respiratory_pauses_and_onsets(resp, my_peaks, my_troughs, n_bins=100):
    """
    Finds each breath onset and respiratory pause in the data, given the peaks and troughs.

    Parameters:
    resp (numpy array): Respiratory data
    my_peaks (numpy array): Indices of peaks in the respiratory data
    my_troughs (numpy array): Indices of troughs in the respiratory data
    n_bins (int): Number of bins for histogram, default is 100

    Returns:
    tuple: inhaleOnsets, exhaleOnsets, inhalePauseOnsets, exhalePauseOnsets
    """

    # Initialize output arrays
    inhale_onsets = np.zeros(len(my_peaks))
    exhale_onsets = np.zeros(len(my_troughs))
    inhale_pause_onsets = np.full(len(my_peaks), np.nan)
    exhale_pause_onsets = np.full(len(my_troughs), np.nan)

    # Constants
    max_pause_bins = 5 if n_bins >= 100 else 2
    maximum_bin_threshold = 5
    upper_threshold = round(n_bins * 0.7)
    lower_threshold = round(n_bins * 0.3)
    simple_zero_cross = np.mean(resp)
    tail_onset_lims = int(np.floor(np.mean(np.diff(my_peaks))))

    if my_peaks[0] > tail_onset_lims:
        first_zero_cross_boundary = my_peaks[0] - tail_onset_lims
    else:
        first_zero_cross_boundary = 0

    this_window = resp[first_zero_cross_boundary:my_peaks[0]]
    amplitude_values, window_bins = np.histogram(this_window, bins=n_bins)
    mode_bin = np.argmax(amplitude_values)
    zero_cross_threshold = window_bins[mode_bin]

    if mode_bin < lower_threshold or mode_bin > upper_threshold:
        zero_cross_threshold = simple_zero_cross

    possible_inhale_inds = this_window < zero_cross_threshold
    if np.sum(possible_inhale_inds) > 0:
        inhale_onset = np.where(possible_inhale_inds)[0][-1]
        inhale_onsets[0] = first_zero_cross_boundary + inhale_onset
    else:
        inhale_onsets[0] = first_zero_cross_boundary

    for this_breath in range(len(my_peaks) - 1):
        inhale_window = resp[my_troughs[this_breath]:my_peaks[this_breath + 1]]
        amplitude_values, window_bins = np.histogram(inhale_window, bins=n_bins)
        mode_bin = np.argmax(amplitude_values)
        max_bin_ratio = amplitude_values[mode_bin] / np.mean(amplitude_values)

        is_exhale_pause = not (
                    mode_bin < lower_threshold or mode_bin > upper_threshold or max_bin_ratio < maximum_bin_threshold)

        if not is_exhale_pause:
            inhale_threshold = simple_zero_cross
            possible_inhale_inds = inhale_window > inhale_threshold
            inhale_onset = np.where(possible_inhale_inds == 0)[0][-1]
            inhale_onsets[this_breath + 1] = my_troughs[this_breath] + inhale_onset
        else:
            min_pause_range = window_bins[mode_bin]
            max_pause_range = window_bins[mode_bin + 1]
            max_bin_total = amplitude_values[mode_bin]
            binning_threshold = 0.25

            for additional_bin in range(1, max_pause_bins):
                this_bin = mode_bin - additional_bin
                if amplitude_values[this_bin] > max_bin_total * binning_threshold:
                    min_pause_range = window_bins[this_bin]

            for additional_bin in range(1, max_pause_bins):
                this_bin = mode_bin + additional_bin
                if amplitude_values[this_bin] > max_bin_total * binning_threshold:
                    max_pause_range = window_bins[this_bin]

            putative_pause_inds = np.where((inhale_window > min_pause_range) & (inhale_window < max_pause_range))[0]
            pause_onset = putative_pause_inds[0] - 1
            inhale_onset = putative_pause_inds[-1] + 1
            exhale_pause_onsets[this_breath] = my_troughs[this_breath] + pause_onset
            inhale_onsets[this_breath + 1] = my_troughs[this_breath] + inhale_onset

        exhale_window = resp[my_peaks[this_breath]:my_troughs[this_breath]]
        amplitude_values, window_bins = np.histogram(exhale_window, bins=n_bins)
        mode_bin = np.argmax(amplitude_values)
        max_bin_ratio = amplitude_values[mode_bin] / np.mean(amplitude_values)

        is_inhale_pause = not (
                    mode_bin < lower_threshold or mode_bin > upper_threshold or max_bin_ratio < maximum_bin_threshold)

        if not is_inhale_pause:
            exhale_threshold = simple_zero_cross
            possible_exhale_inds = exhale_window > exhale_threshold
            exhale_onset = np.where(possible_exhale_inds == 1)[0][-1]
            exhale_onsets[this_breath] = my_peaks[this_breath] + exhale_onset
        else:
            min_pause_range = window_bins[mode_bin]
            max_pause_range = window_bins[mode_bin + 1]
            max_bin_total = amplitude_values[mode_bin]
            binning_threshold = 0.25

            for additional_bin in range(1, max_pause_bins):
                this_bin = mode_bin - additional_bin
                if amplitude_values[this_bin] > max_bin_total * binning_threshold:
                    min_pause_range = window_bins[this_bin]

            for additional_bin in range(1, max_pause_bins):
                this_bin = mode_bin + additional_bin
                if amplitude_values[this_bin] > max_bin_total * binning_threshold:
                    max_pause_range = window_bins[this_bin]

            putative_pause_inds = np.where((exhale_window > min_pause_range) & (exhale_window < max_pause_range))[0]
            pause_onset = putative_pause_inds[0] - 1
            exhale_onset = putative_pause_inds[-1] + 1
            exhale_pause_onsets[this_breath] = my_peaks[this_breath] + pause_onset
            exhale_onsets[this_breath] = my_peaks[this_breath] + exhale_onset

    if len(resp) - my_peaks[-1] > tail_onset_lims:
        last_zero_cross_boundary = my_peaks[-1] + tail_onset_lims
    else:
        last_zero_cross_boundary = len(resp)

    exhale_window = resp[my_peaks[-1]:last_zero_cross_boundary]
    possible_exhale_inds = exhale_window < simple_zero_cross

    if np.sum(possible_exhale_inds) > 0:
        exhale_best_guess = np.where(possible_exhale_inds == 1)[0][0]
        exhale_onsets[-1] = my_peaks[-1] + exhale_best_guess
    else:
        exhale_onsets[-1] = last_zero_cross_boundary

    return inhale_onsets, exhale_onsets, inhale_pause_onsets, exhale_pause_onsets
