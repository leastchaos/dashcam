import subprocess
import datetime
import sys
import logging
import numpy as np
import tempfile
from scipy.signal import correlate
from datetime import timedelta

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('video_merge.log')
    ]
)

def extract_audio(video_path, output_path):
    """Extract audio to WAV format for processing"""
    cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-vn', '-ac', '1', '-ar', '44100',
        '-acodec', 'pcm_s16le', output_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        logging.info(f"Extracted audio to {output_path}")
    except subprocess.CalledProcessError as e:
        logging.error("Audio extraction failed", exc_info=True)
        raise

def find_audio_offset(audio1_path, audio2_path, max_offset=10):
    """Find time offset between two audio files using cross-correlation"""
    logging.info("Calculating audio offset...")
    
    # Read audio files
    cmd = ['ffmpeg', '-i', audio1_path, '-f', 's16le', '-']
    audio1 = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, dtype=np.int16)
    
    cmd = ['ffmpeg', '-i', audio2_path, '-f', 's16le', '-']
    audio2 = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, dtype=np.int16)

    # Trim to first 60 seconds for faster processing
    max_samples = 44100 * max_offset
    audio1 = audio1[:max_samples]
    audio2 = audio2[:max_samples]

    # Normalize
    audio1 = (audio1 - audio1.mean()) / audio1.std()
    audio2 = (audio2 - audio2.mean()) / audio2.std()

    # Compute cross-correlation
    corr = correlate(audio1, audio2, mode='full')
    lag = np.argmax(corr) - (len(audio2) - 1)
    offset_seconds = lag / 44100

    logging.info(f"Calculated audio offset: {offset_seconds:.3f} seconds")
    return offset_seconds

def sync_videos(video1_path, video2_path):
    """Synchronize videos using audio alignment"""
    with tempfile.NamedTemporaryFile(suffix='_1.wav') as f1, \
         tempfile.NamedTemporaryFile(suffix='_2.wav') as f2:
        
        extract_audio(video1_path, f1.name)
        extract_audio(video2_path, f2.name)
        
        try:
            offset = find_audio_offset(f1.name, f2.name)
            return offset
        except Exception as e:
            logging.warning("Audio sync failed, falling back to timestamp")
            return None
def parse_timestamp(filename):
    timestamp_str = filename.split('_')[-3] + '_' + filename.split('_')[-2]
    return datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

def main(video1_path, video2_path, output_path):
    logging.info("Starting video merge process")
    
    # Get initial timestamp offset
    # ts_offset = (parse_timestamp(video2_path) - parse_timestamp(video1_path)).total_seconds()
    # logging.info(f"Initial timestamp offset: {ts_offset:.2f}s")

    # Get audio-based offset
    audio_offset = sync_videos(video1_path, video2_path)
    
    # Determine final offset
    if audio_offset is not None and abs(audio_offset) < 5:  # Only trust small offsets
        final_offset = audio_offset
        logging.info(f"Using audio offset: {final_offset:.3f}s")


if __name__ == "__main__":

    main("C:/Video/Output/20250126_051428_C300.mp4", "C:/Video/Output/20250125_211100_OA4.mp4", "C:/Video/Output/test.mp4" )