import logging
import subprocess
import re
from pathlib import Path
from typing import List
from tqdm import tqdm


def get_duration(file_path: Path) -> float:
    """
    Returns the duration of a video file using FFprobe.

    Args:
        file_path: Path to the video file

    Returns:
        Duration in seconds as a float

    Raises:
        subprocess.CalledProcessError: If FFprobe command fails
    """
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def parse_time(time_str: str) -> float:
    """
    Converts FFmpeg time string (hh:mm:ss.ms) to seconds.

    Args:
        time_str: Time string in FFmpeg format

    Returns:
        Total time in seconds as a float
    """
    hours, minutes, seconds = map(float, time_str.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def combine_clips(
    input_folder: Path, output_file_path: Path, file_type: str = ".mp4"
) -> None:
    """
    Combines video clips of a specific type into a single output file using FFmpeg with a progress bar.

    Args:
        input_folder: Path to the folder containing the source clips
        output_file_path: Path to the destination video file (extension will be forced to match file_type)
        file_type: File extension to process (case-insensitive), must include leading dot

    Raises:
        ValueError: If no matching files are found in the input folder
        subprocess.CalledProcessError: If FFmpeg command fails
        FileExistsError: If output file already exists
    """
    # Normalize file type to lowercase and validate
    file_type = file_type.lower()
    if not file_type.startswith("."):
        raise ValueError("File type must start with a dot (e.g., .mp4)")

    if output_file_path.exists():
        raise FileExistsError(f"Output file already exists: {output_file_path}")

    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    output_file_path = output_file_path.with_suffix(file_type)

    input_files: List[Path] = sorted(
        [file for file in input_folder.iterdir() if file.suffix.lower() == file_type],
        key=lambda f: f.name.lower(),
    )

    if not input_files:
        raise ValueError(f"No {file_type} files found in {input_folder}")

    # Calculate total duration of all input files
    total_duration = 0.0
    invalid_files = []
    for file in input_files:
        try:
            total_duration += get_duration(file)
        except ValueError as e:
            logging.error(f"Error getting duration for {file}: {e}")
            invalid_files.append(file)

    if invalid_files:
        logging.warning(f"Invalid files found: {invalid_files}")
    # Remove invalid files from list
    input_files = [file for file in input_files if file not in invalid_files]

    if not input_files:
        raise ValueError(f"No valid {file_type} files found in {input_folder}")

    concat_list = input_folder / (output_file_path.stem + "concat.txt")
    progress_bar = None

    try:
        with concat_list.open("w") as f:
            for file in input_files:
                f.write(f"file '{file.resolve()}'\n")

        logging.info(f"Concat list created: {concat_list}")
        logging.info(f"Running FFmpeg command for {output_file_path}")

        # Initialize progress bar
        progress_bar = tqdm(
            total=round(total_duration, 2),
            unit="s",
            desc="Combining clips",
            bar_format="{l_bar}{bar}| {n:.2f}/{total:.2f}s [{elapsed}<{remaining}, {rate_fmt}{postfix}]",
        )
        # Run FFmpeg process
        process = subprocess.Popen(
            [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                "-y",
                str(output_file_path),
            ],
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )

        stderr_lines = []
        for line in process.stderr:
            line = line.strip()
            stderr_lines.append(line)

            # Update progress from time markers
            time_match = re.search(r"time=(\d+:\d+:\d+\.\d+)", line)
            if time_match:
                current_time = parse_time(time_match.group(1))
                progress_bar.update(round(current_time - progress_bar.n, 2))

        process.wait()
        progress_bar.close()

        if process.returncode != 0:
            error_output = "\n".join(stderr_lines)
            raise subprocess.CalledProcessError(
                process.returncode, process.args, stderr=error_output
            )

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg command failed with exit code {e.returncode}")
        print(f"Error output:\n{e.stderr}")
        raise
    finally:
        if progress_bar is not None:
            progress_bar.close()
        concat_list.unlink(missing_ok=True)


if __name__ == "__main__":
    input_folder = Path("C:/Video/Input/OA4")
    output_file_path = Path("C:/Video/combined_video")
    combine_clips(input_folder, output_file_path)
