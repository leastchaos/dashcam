import librosa
import numpy as np
import matplotlib.pyplot as plt  # For visualization (optional)

def find_beep_frequency_range(audio_path, top_n_frequencies=5): #top_n_frequencies: number of dominant frequencies to display
    """Finds dominant frequencies in an audio file."""
    y, sr = librosa.load(audio_path)
    frequencies = np.fft.fftfreq(len(y), d=1/sr)
    spectrum = np.abs(np.fft.fft(y))

    # Find the indices of the top N dominant frequencies
    top_indices = np.argsort(spectrum)[::-1][:top_n_frequencies]

    dominant_frequencies = frequencies[top_indices]

    # Filter out negative frequencies (due to FFT symmetry)
    positive_frequencies = [f for f in dominant_frequencies if f > 0]

    if positive_frequencies:
        print("Dominant Frequencies (Hz):", positive_frequencies)

        # (Optional) Plot the spectrum
        plt.figure(figsize=(10, 4))
        plt.plot(frequencies, spectrum)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Amplitude")
        plt.title("Frequency Spectrum")

        # Highlight the dominant frequencies on the plot
        for freq in positive_frequencies:
            plt.axvline(x=freq, color='r', linestyle='--') #visualize the dominant frequencies
        plt.grid(True)
        plt.show()

        # You can determine a range based on the dominant frequencies and the spectrum plot
        # Example: If you see a cluster of frequencies around your beep, use min and max of that cluster as your range

        # Example range determination (you might need to adjust this based on the plot or dominant_frequencies output):
        min_freq = min(positive_frequencies) - 100 # Subtract a small amount to get lower bound
        max_freq = max(positive_frequencies) + 100 # Add a small amount to get upper bound
        print(f"Estimated frequency range: ({min_freq}, {max_freq})")
        return (min_freq, max_freq)

    else:
      print("No positive dominant frequencies found.")
      return None

# Example usage:
audio_file = "0130.MP3"  # Replace with your audio file
find_beep_frequency_range(audio_file)