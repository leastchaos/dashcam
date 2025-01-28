import subprocess
import datetime
import sys
from datetime import timedelta

def parse_timestamp(filename):
    timestamp_str = filename.split('_')[-2] + '_' + filename.split('_')[-1].split('.')[0]
    return datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

def get_video_info(filename):
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
           '-show_entries', 'stream=width,height,r_frame_rate',
           '-of', 'csv=p=0', filename]
    output = subprocess.check_output(cmd).decode('utf-8').strip()
    width, height, fps_str = output.split(',')
    fps = eval(fps_str)
    return int(width), int(height), fps

def get_duration(filename):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
           '-of', 'default=noprint_wrappers=1:nokey=1', filename]
    output = subprocess.check_output(cmd).decode('utf-8').strip()
    return float(output)

def main(video1_path, video2_path, output_path):
    # Parse timestamps from filenames
    s1 = parse_timestamp(video1_path)
    s2 = parse_timestamp(video2_path)

    # Get video durations
    duration1 = get_duration(video1_path)
    duration2 = get_duration(video2_path)

    # Calculate time parameters
    end1 = s1 + timedelta(seconds=duration1)
    end2 = s2 + timedelta(seconds=duration2)
    s_common = max(s1, s2)
    end_common = min(end1, end2)
    final_duration = (end_common - s_common).total_seconds()

    if final_duration <= 0:
        print("Error: Videos do not overlap in time")
        return

    trim_start1 = (s_common - s1).total_seconds() if s_common > s1 else 0.0
    trim_start2 = (s_common - s2).total_seconds() if s_common > s2 else 0.0

    # Get first video's properties
    width1, height1, fps1 = get_video_info(video1_path)
    scaled_w = width1 // 2
    scaled_h = height1 // 2

    # Generate timecode string
    timecode_str = s_common.strftime("%H:%M:%S:00")  # Assumes non-drop frame

    # Build filter complex
    filter_complex = f"""
        [0:v]trim=start={trim_start1}:duration={final_duration},setpts=PTS-STARTPTS[base];
        [0:a]atrim=start={trim_start1}:duration={final_duration},asetpts=PTS-STARTPTS[audio];
        [1:v]trim=start={trim_start2}:duration={final_duration},setpts=PTS-STARTPTS,scale={scaled_w}:{scaled_h}[overlay];
        [base][overlay]overlay=W-w-10:H-h-10:format=auto[outv];
    """

    # Build FFmpeg command
    cmd = [
        'ffmpeg',
        '-y',
        '-i', video1_path,
        '-i', video2_path,
        '-filter_complex', filter_complex,
        '-map', '[outv]',
        '-map', '[audio]',
        '-c:v', 'libx264',
        '-preset', 'slow',
        '-crf', '18',
        '-movflags', '+faststart',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-r', str(fps1),
        '-s', f'{width1}x{height1}',
        '-timecode', timecode_str,
        output_path
    ]

    # Run FFmpeg command
    try:
        subprocess.run(cmd, check=True)
        print(f"Successfully created output video: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error processing video: {e}")

if __name__ == "__main__":
    # if len(sys.argv) != 4:
    #     print("Usage: python script.py <video1> <video2> <output>")
    #     sys.exit(1)
    
    # main(sys.argv[1], sys.argv[2], sys.argv[3])
    