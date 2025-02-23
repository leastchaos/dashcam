from pathlib import Path
import numpy as np
import librosa
from moviepy import VideoFileClip

def find_audio_spike_time(video_path: Path, threshold: float = 0.5, search_window: int = 10) -> float:
    """Detect the first significant audio spike in the first few seconds"""
    # Extract audio from video
    video = VideoFileClip(str(video_path))
    audio: np.ndarray = video.audio.to_soundarray(fps=22050)[:, 0]  # Convert to mono
    
    # Get first 'search_window' seconds of audio
    max_samples: int = int(search_window * 22050)
    audio_segment: np.ndarray = audio[:max_samples]
    
    # Find the first peak that exceeds the threshold
    peaks: np.ndarray = np.where(audio_segment > threshold)[0]
    if len(peaks) == 0:
        raise ValueError(f"No significant audio spike detected in {video_path.name}")
    
    first_peak_time: float = peaks[0] / 22050
    video.close()
    return first_peak_time

def sync_and_trim_videos(
    video1_path: Path,
    video2_path: Path,
    output1_path: Path,
    output2_path: Path,
    threshold: float = 0.3,
    search_window: int = 5
) -> None:
    # Find spike times in both videos
    spike1: float = find_audio_spike_time(video1_path, threshold, search_window)
    spike2: float = find_audio_spike_time(video2_path, threshold, search_window)
    
    # Calculate time difference
    time_diff: float = spike1 - spike2
    
    # Load video clips
    clip1 = VideoFileClip(str(video1_path))
    clip2 = VideoFileClip(str(video2_path))
    
    # Trim videos based on spike difference
    if time_diff > 0:
        synced_clip1 = clip1.subclipped(time_diff, clip1.duration)
        synced_clip2 = clip2.subclipped(0, clip2.duration - time_diff)
    else:
        synced_clip1 = clip1.subclipped(0, clip1.duration + time_diff)
        synced_clip2 = clip2.subclipped(-time_diff, clip2.duration)
    
    # Write output files
    synced_clip1.write_videofile(str(output1_path))
    synced_clip2.write_videofile(str(output2_path))
    
    # Close clips
    clip1.close()
    clip2.close()

if __name__ == "__main__":
    # Example usage
    video_dir = Path("path/to/videos")
    outputs_dir = Path("C:\Video\Input\Test")
    
    sync_and_trim_videos(
        video1_path=Path("C:/Video/Input/OA4/DJI_20250130052441_0044_D_001.MP4"),
        video2_path=Path("C:/Video/Input/C300/20250130052509_000617.MP4"),
        output1_path=outputs_dir / "synced_video1.mp4",
        output2_path=outputs_dir / "synced_video2.mp4",
        threshold=0.4,
        search_window=30
    )