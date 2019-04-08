import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

### Plotting
def plotSpectrum(times, files, peak_intensity, resolution = 1/300, buffer = 5,
                 min_time = None, max_time = None, ax = None, clip = 1E4):
    """
    Plots the spectrum of peak across the different chromatograms
    
    Arguments:
        times -- pandas Series giving the times of the peaks
        files -- pandas Series of the file each peak belonged to
        peak_intensity -- pandas Series of the maximum values of each peak
        resolution -- minutes per time index step for the chromatogram
        buffer -- Int: Extra time steps to add to each end of the spectrum output
        min_time -- Float: Minumum time to draw the spectrum from (excluding buffer). Helps align several spectrum together
        max_time -- Float: Maximum time to draw the spectrum from (excluding buffer)
        ax -- matplotlib axis to draw the spectrum into
        clip -- Int or Float: Maximum value of the intensity. Values above this are clipped
        
    Returns:
        pcm - matplotlib axis
    """
    if min_time is None:
        min_time = min(times)
    timeIndex = np.round((times - min_time) / resolution).astype(int)
    if max_time is None:
        max_time_index = max(timeIndex)
    else:
        max_time_index = np.ceil((max_time - min_time) / resolution).astype(int)
    
    number_of_files = files.max() + 1
    spectrum = np.zeros((number_of_files, max_time_index + buffer * 2))
#    spectrum[files, timeIndex + buffer] = 1
    # Get the maximum value when multiple peaks from the same file are assigned to the same time point
    timeIndexValues = pd.concat([timeIndex, files, peak_intensity], axis = 1)
    timeIndexValues.columns = ['Index', 'File', 'Value']
    timeIndexValues = timeIndexValues.groupby(['File', 'Index'], as_index = False).max()
    spectrum[timeIndexValues['File'], timeIndexValues['Index'] + buffer] = np.clip(timeIndexValues['Value'], 0, clip)
#    spectrum[files, timeIndex + buffer] = peak_intensity
    
    if ax is None:
        ax = plt.axes()
#    pcm = ax.imshow(spectrum, norm=colors.LogNorm(vmin=1, vmax=peak_intensity.max()), cmap = 'hot', aspect = 'auto',
    pcm = ax.imshow(spectrum, cmap = 'inferno', aspect = 'auto',
                extent = [min_time - buffer * resolution, max_time + buffer * resolution, 0, 1])
    ax.set_axis_off()  # Turn off the display of the axis lines and ticks
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    
    return pcm

def plotSpectrumTogether(info_df, peak_intensity, with_real = False, save_name = None):
    """
    Plots several spectra stacked together, to compare the prediction output with the input and groundtruth
    
    Arguments:
        info_df -- DataFrame containing information about each peak, including aligned and unaligned peak times and file number
        peak_intensity -- pandas Series of the maximum values of each peak
        with_real -- If True, include the groundtruth as a third spectrum (subplot)
        save_name -- None or String: Name to save the figure
    """
    # Get min_time and max_time to pass into each call of plotSpectrum, so that each spectrum is aligned
    min_time = min(info_df['startTime'])
    max_time = max(info_df['endTime'])
    
    if with_real:
        fig, axes = plt.subplots(3,1)
    else:
        fig, axes = plt.subplots(2,1)
    axes[0].set_title('Unaligned', fontdict = {'fontsize': 11})
    plotSpectrum(info_df['peakMaxTime'], info_df['File'], peak_intensity,
                 min_time = min_time, max_time = max_time, ax = axes[0])
    axes[1].set_title('Aligned', fontdict = {'fontsize': 11})
    pcm = plotSpectrum(info_df['AlignedTime'], info_df['File'], peak_intensity,
                 min_time = min_time, max_time = max_time, ax = axes[1])
    if with_real:
        axes[2].set_title('Truth', fontdict = {'fontsize': 11})
        plotSpectrum(info_df['RealAlignedTime'], info_df['File'], peak_intensity,
                     min_time = min_time, max_time = max_time, ax = axes[2])
        
    # Put retention time as x axis on the bottom-most plot
    axes[-1].set_axis_on()
    axes[-1].get_xaxis().set_visible(True)  # Only set the bottom axis line to be visible
    axes[-1].spines['top'].set_visible(False)
    axes[-1].spines['right'].set_visible(False)
    axes[-1].spines['left'].set_visible(False)
    axes[-1].set_xlabel('Retention Time (min)', fontdict = {'fontsize': 11})
    
    plt.tight_layout()
#    fig.subplots_adjust(hspace = 0.3, wspace = 10)
#    fig.colorbar(pcm, ax=axes.ravel().tolist(), fraction = 0.05, pad = 0.01)
    
    if save_name is not None:
        plt.savefig(save_name + '.png', dpi = 250, format = 'png', bbox_inches = 'tight')
        plt.savefig(save_name + '.eps', dpi = 500, format = 'eps', bbox_inches = 'tight')
    else:
        plt.show()


def plotPeaks(times, info_df, peak_df, min_time, max_time, resolution = 1/300, buffer = 10):
    """
    Recreates chromatograms from the individual peaks, each at their associated times
    
    Arguments:
        times -- pandas Series giving the times of the peaks
        info_df -- DataFrame containing information about each peak, including aligned and unaligned peak times and file number
        peak_df -- Dataframe of the peak profile of each peak
        min_time -- Float: Minumum time of the chromatogram (excluding buffer)
        max_time -- Float: Maximum time of the chromatogram (excluding buffer)
        resolution -- minutes per time index step for the chromatogram
        buffer -- Int: Extra time steps to add to each end of the output chromatogram
    
    Returns:
        peaks -- 2D numpy array with each row as a reconstructed chromatogram
        times -- 1D numpy array of the times corresponding to each column of the peaks array
    """
    number_of_files = info_df['File'].max() + 1
    time_steps = np.ceil((max_time - min_time) / resolution + buffer * 2).astype(int)
    peaks = np.zeros((time_steps, number_of_files))
    for row in info_df.iterrows():
        peak = peak_df.loc[row[0]]  # Peak profile
        peak = peak[np.flatnonzero(peak)]  # Remove the zeros (which were added during the preprocessing)
        peak_length = len(peak)
        steps_from_peak = np.round((row[1]['peakMaxTime'] - row[1]['startTime']) / resolution).astype(int)  # Number of timesteps from the start of the peak profile to its highest intensity
        peak_steps_from_beginning = np.round((times.loc[row[0]] - min_time) / resolution).astype(int)  # Index corresponding to the peak time (highest intensity)
        idx_start = peak_steps_from_beginning - steps_from_peak + buffer
        idx_end = peak_steps_from_beginning - steps_from_peak + peak_length + buffer
        current_values = peaks[idx_start : idx_end, int(row[1]['File'])]
        peaks[idx_start : idx_end, int(row[1]['File'])] = np.maximum(peak, current_values)  # Replace the default zeros of the reconstructed chromatogram with the peak profile at the appropriate time
    
    times = np.linspace(min_time - resolution * buffer, max_time + resolution * buffer, time_steps)
    return peaks, times


def plotPeaksTogether(info_df, peak_df, with_real = False, save_name = None, save_data = False):
    """
    Plots several reconstructed chromatograms stacked together, to compare the prediction output with the input and groundtruth
    
    Arguments:
        info_df -- DataFrame containing information about each peak, including aligned and unaligned peak times and file number
        peak_df -- Dataframe of the peak profile of each peak
        with_real -- Boolean: To include the groundtruth as a third plot or not
        save_name -- None or String: Name to save the figure
        save_data -- If True, all plot data are saved as csv files
                     Time data for the x values and the unaligned, aligned, and ground truth intensities as y values
    """
    # Get min_time and max_time to pass into each call of plotPeaks, so that each plot is aligned
    min_time = min(info_df['startTime'])
    max_time = max(info_df['endTime'])
    peaks, _ = plotPeaks(info_df['AlignedTime'], info_df, peak_df, min_time, max_time)
    orig_peaks, time = plotPeaks(info_df['peakMaxTime'], info_df, peak_df, min_time, max_time)
    if with_real:
        real_peaks, _ = plotPeaks(info_df['RealAlignedTime'], info_df, peak_df, min_time, max_time)
        fig, axes = plt.subplots(3,1)
        axes[2].plot(time, real_peaks)
        axes[2].set_title('Truth', fontdict = {'fontsize': 11})
    else:
        fig, axes = plt.subplots(2,1)
    axes[0].plot(time, orig_peaks)
    axes[0].set_title('Unaligned', fontdict = {'fontsize': 11})
    axes[1].plot(time, peaks)
    axes[1].set_title('Aligned', fontdict = {'fontsize': 11})
    for ax in axes[:-1]:
        ax.set_axis_off()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.set_xlim(time[0], time[-1])
    
    # Put retention time as x axis on the bottom-most plot
    axes[-1].spines['top'].set_visible(False)  # Only set the bottom axis line to be visible
    axes[-1].spines['right'].set_visible(False)
    axes[-1].spines['left'].set_visible(False)
    axes[-1].get_yaxis().set_visible(False)
    axes[-1].set_xlim(time[0], time[-1])
    axes[-1].set_xlabel('Retention Time (min)', fontdict = {'fontsize': 11})
    
    plt.tight_layout()
    fig.subplots_adjust(hspace = 0.3, wspace = 10)
    
    if save_name is not None:
        plt.savefig(save_name + '.png', dpi = 250, format = 'png', bbox_inches = 'tight')
        plt.savefig(save_name + '.eps', dpi = 250, format = 'eps', bbox_inches = 'tight')
    else:
        plt.show()
        
    # save the data
    if save_data:
        df_tmp = pd.DataFrame(orig_peaks)
        df_tmp.to_csv("peaksUnaligned.csv", index=False)
        df_tmp = pd.DataFrame(peaks)
        df_tmp.to_csv("peaksAligned.csv", index=False)
        df_tmp = pd.DataFrame(real_peaks)
        df_tmp.to_csv("peaksTruth.csv", index=False)        
        df_tmp = pd.DataFrame(time)
        df_tmp.to_csv("time.csv", index=False)        

