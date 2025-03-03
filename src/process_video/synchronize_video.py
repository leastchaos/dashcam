import subprocess
import numpy as np
from scipy.io import wavfile
from scipy import signal
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_audio_ffmpeg_fixed_sr(input_video, output_audio, target_sr=48000):
    """Extracts audio using FFmpeg with a fixed sample rate."""
    command = [
        'ffmpeg',
        '-i', input_video,
        '-vn',
        '-acodec', 'pcm_s16le',
        '-ar', str(target_sr),
        output_audio
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info(f"Audio extracted to {output_audio} with sample rate {target_sr}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error: {e}")
        return False

def load_audio_numpy(audio_file):
    """Loads audio from WAV file into NumPy."""
    try:
        sample_rate, audio_data = wavfile.read(audio_file)
        return sample_rate, audio_data
    except Exception as e:
        logging.error(f"Error loading audio: {e}")
        return None, None

def synchronize_audio_numpy(front_audio_data, rear_audio_data, sample_rate):
    """Synchronizes audio using scipy.signal.correlate."""
    match front_audio_data.ndim:
        case 1:
            front_audio_mono = front_audio_data.astype(np.float32)
        case 2:
            front_audio_mono = front_audio_data[:, 0].astype(np.float32)
        case _:
            raise ValueError("Front audio data has unexpected dimensions.")

    match rear_audio_data.ndim:
        case 1:
            rear_audio_mono = rear_audio_data.astype(np.float32)
        case 2:
            rear_audio_mono = rear_audio_data[:, 0].astype(np.float32)
        case _:
            raise ValueError("Rear audio data has unexpected dimensions.")

    correlation = signal.correlate(front_audio_mono, rear_audio_mono, mode='full')
    lag = np.argmax(correlation) - (len(rear_audio_mono) - 1)
    time_offset = lag / sample_rate

    return time_offset

def synchronize_videos(front_video, rear_video, target_sample_rate=48000):
    front_audio = "front_audio.wav"
    rear_audio = "rear_audio.wav"

    if not (extract_audio_ffmpeg_fixed_sr(front_video, front_audio, target_sample_rate) and
            extract_audio_ffmpeg_fixed_sr(rear_video, rear_audio, target_sample_rate)):
        logging.error("Audio extraction failed")
        return None

    front_sr, front_data = load_audio_numpy(front_audio)
    rear_sr, rear_data = load_audio_numpy(rear_audio)

    if not (front_sr and rear_sr):
        logging.error("Error loading audio data")
        return None

    if front_sr != rear_sr:
        logging.error("Error: Sample rates do not match after fixed extraction.")
        return None

    try:
        offset = synchronize_audio_numpy(front_data, rear_data, front_sr)
        logging.info(f"Rear video is {offset} seconds behind front video.")
        return offset
    except ValueError as e:
        logging.error(f"Error during synchronization: {e}")
        return None

def crop_video(input_video, output_video, start_time):
    """Crops a video using FFmpeg to start at a specified time."""
    command = [
        'ffmpeg',
        '-i', input_video,
        '-ss', str(abs(start_time)),
        '-c:v', 'copy',
        '-c:a', 'copy',
        output_video
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info(f"Video cropped to {output_video} starting at {start_time} seconds.")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error during cropping: {e}")
        return False

def synchronize_and_crop_videos(front_video, rear_video, offset):
    """Synchronizes videos by cropping based on the calculated offset."""
    front_cropped = "front_cropped.mp4"
    rear_cropped = "rear_cropped.mp4"

    if offset > 0:
        if crop_video(rear_video, rear_cropped, offset):
            logging.info("Rear video successfully cropped.")
        else:
            logging.error("Rear video cropping failed.")
            return None, None
        if crop_video(front_video, front_cropped, 0):
            logging.info("Front video successfully copied.")
        else:
            logging.error("Front video copying failed.")
            return None, None
    elif offset < 0:
        if crop_video(front_video, front_cropped, abs(offset)):
            logging.info("Front video successfully cropped.")
        else:
            logging.error("Front video cropping failed.")
            return None, None
        if crop_video(rear_video, rear_cropped, 0):
            logging.info("Rear video successfully copied.")
        else:
            logging.error("Rear video copying failed.")
            return None, None
    else:
        if crop_video(front_video, front_cropped, 0) and crop_video(rear_video, rear_cropped, 0):
            logging.info("No offset, front and rear videos copied.")
        else:
            logging.error("Error copying front or rear videos.")
            return None, None

    logging.info("Video synchronization and cropping complete.")
    return front_cropped, rear_cropped

# Example usage:
front_video = r"C:\Video\Uploaded\20250302_052904_DJI_Action4.mp4"
rear_video = r"C:\Video\Uploaded\20250302_133309_Fly6Pro.mp4"

offset = synchronize_videos(front_video, rear_video)

if offset is not None:
    front_cropped, rear_cropped = synchronize_and_crop_videos(front_video, rear_video, offset)
    if front_cropped and rear_cropped:
        logging.info(f"Cropped front video: {front_cropped}")
        logging.info(f"Cropped rear video: {rear_cropped}")