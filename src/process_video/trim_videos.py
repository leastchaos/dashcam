import logging
import numpy as np
import scipy.signal as signal
from pydub import AudioSegment
from pathlib import Path
from typing import Tuple, Optional
import tempfile
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def detect_beep(
    audio_path: Path,
    threshold_db: float = -30.0,  # Corrected to negative dBFS value
    freq_range: Tuple[float, float] = (5000.0, 7000.0),
    min_duration_ms: float = 200.0,
    search_window_s: float = 20.0,
) -> float:
    """
    Scientifically valid beep detection with proper signal processing

    Parameters:
    threshold_db: Negative dBFS value (0 = maximum digital level)
    freq_range: Target frequency range in Hz
    min_duration_ms: Minimum beep duration in milliseconds
    search_window_s: Search duration in seconds from start
    """
    try:
        audio = AudioSegment.from_file(str(audio_path))
    except Exception as e:
        logger.error(f"Failed to load audio file: {e}")
        return 0.0

    # Convert to mono and normalize samples to [-1, 1]
    audio = audio.set_channels(1)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    samples /= np.iinfo(audio.array_type).max  # Proper normalization

    fs = audio.frame_rate
    nperseg = 1024  # FFT window size
    noverlap = 512  # 50% overlap for better time resolution

    # Compute power spectral density
    freqs, times, Sxx = signal.spectrogram(
        samples,
        fs=fs,
        nperseg=nperseg,
        noverlap=noverlap,
        window="hann",
        scaling="spectrum",
    )

    # Find frequency bins in target range
    freq_mask = (freqs >= freq_range[0]) & (freqs <= freq_range[1])
    Sxx_filtered = Sxx[freq_mask]

    # Calculate energy in target band (power sum)
    energy = np.sum(Sxx_filtered, axis=0)

    # Convert to dBFS (10*log10 for power values)
    energy_db = 10 * np.log10(energy + 1e-12)  # Avoid log(0)

    # Calculate time parameters
    frame_duration = (nperseg - noverlap) / fs  # Time between frames
    required_frames = max(1, int(round(min_duration_ms / 1000 / frame_duration)))
    search_frames = min(len(times), int(search_window_s / frame_duration))

    # Find first valid beep sequence
    consecutive_count = 0
    for i in range(search_frames):
        if energy_db[i] > threshold_db:
            consecutive_count += 1
            if consecutive_count >= required_frames:
                # Calculate exact start time accounting for windowing
                start_index = max(0, i - required_frames + 1)
                return max(0.0, times[start_index] - (nperseg / (2 * fs)))
        else:
            consecutive_count = 0

    logger.warning("No valid beep found in the specified time range")
    return 0.0


def extract_audio(video_path: Path, audio_path: Path) -> bool:
    """Extract audio to WAV format using ffmpeg"""
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "44100",
        "-acodec",
        "pcm_s16le",
        str(audio_path),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Audio extraction failed: {e.stderr.decode().strip()}")
        return False


def trim_video(input_path: Path, output_path: Path, start_time: float) -> bool:
    """Trim video using ffmpeg stream copy"""
    if input_path.resolve() == output_path.resolve():
        logger.error("Input and output paths must be different")
        return False

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        str(start_time),
        "-i",
        str(input_path),
        "-c",
        "copy",
        "-avoid_negative_ts",
        "1",
        str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Video trimming failed: {e.stderr.decode().strip()}")
        return False


def process_video(input_path: Path, output_path: Optional[Path] = None) -> bool:
    """Main processing function"""
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return False

    output_path = output_path or input_path.with_stem(f"{input_path.stem}_trimmed")

    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path = Path(tmp_dir) / "audio.wav"
        if not extract_audio(input_path, audio_path):
            return False

        beep_time = detect_beep(audio_path)

        logger.info(f"Detected beep at {beep_time:.3f} seconds")
        return trim_video(input_path, output_path, beep_time)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Video synchronization beep trimmer")
    parser.add_argument("input", type=Path, help="Input video file")
    parser.add_argument("-o", "--output", type=Path, help="Output video file")
    args = parser.parse_args()

    if process_video(args.input, args.output):
        logger.info(f"Successfully created trimmed video: {args.output}")
    else:
        logger.error("Processing failed")
        exit(1)
