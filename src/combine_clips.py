import logging
import subprocess
from pathlib import Path
from typing import List
from tqdm import tqdm

def combine_clips(
    input_folder: Path, output_file_path: Path, file_type: str = ".mp4"
) -> None:
    """
    Combines video clips of a specific type into a single output file using FFmpeg.

    Args:
        input_folder: Path to the folder containing the source clips
        output_file_path: Path to the destination video file (extension will be forced to match file_type)
        file_type: File extension to process (case-insensitive), must include leading dot

    Raises:
        ValueError: If no matching files are found in the input folder
        subprocess.CalledProcessError: If FFmpeg command fails
    """
    # Normalize file type to lowercase and validate
    file_type = file_type.lower()
    if not file_type.startswith("."):
        raise ValueError("File type must start with a dot (e.g., .mp4)")

    # Check if output file already exists
    if output_file_path.exists():
        raise FileExistsError(f"Output file already exists: {output_file_path}")

    # Create output folder if it doesn't exist
    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Enforce correct output file extension
    output_file_path = output_file_path.with_suffix(file_type)

    # Get and validate input files
    input_files: List[Path] = sorted(
        [file for file in input_folder.iterdir() if file.suffix.lower() == file_type],
        key=lambda f: f.name.lower(),  # Case-insensitive sort
    )

    if not input_files:
        raise ValueError(f"No {file_type} files found in {input_folder}")

    # Create temporary concat list with absolute paths
    concat_list = input_folder / "concat.txt"

    try:
        # Write concat file with absolute paths
        with concat_list.open("w") as f:
            for file in input_files:
                f.write(f"file '{file.resolve()}'\n")

        logging.info(f"Concat list created: {concat_list}")
        logging.info(f"Running FFmpeg command for {output_file_path}")
        # Run FFmpeg command
        # Calculate total size of input files
        total_size = sum(f.stat().st_size for f in input_files)
        with tqdm(total=total_size, unit="B", unit_scale=True, unit_divisor=1024, desc="Combining Clips") as pbar:
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
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            while True:
                line = process.stdout.readline().decode().strip()
                if not line:
                    break
                if line.startswith("size="):
                    try:
                        frame_number = int(line.split("=")[1])
                        # Estimate processed size based on frame number (simplification)
                        processed_size = frame_number * (file.stat().st_size / len(input_files))
                        pbar.update(processed_size)
                    except ValueError:
                        pass  # Ignore lines without frame number
            stdout, stderr = process.communicate()

            # Check for errors
            if process.returncode != 0:
                print(f"FFmpeg command failed with exit code {process.returncode}")
                print(f"Error output:\n{stderr.decode()}")
                raise subprocess.CalledProcessError(process.returncode, cmd=process.args)


    except subprocess.CalledProcessError as e:
        print(f"FFmpeg command failed with exit code {e.returncode}")
        print(f"Error output:\n{e.stderr.decode()}")
        raise
    finally:
        # Clean up temporary concat file
        concat_list.unlink(missing_ok=True)


if __name__ == "__main__":
    input_folder = Path("C:/Video/OA4")
    output_file_path = Path("C:/Video/combined_video")
    combine_clips(input_folder, output_file_path)
