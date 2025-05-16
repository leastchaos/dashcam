import logging
import subprocess

def safely_eject_drive(drive_letter: str):
    """
    Safely ejects a USB drive using diskpart on Windows.
    
    Args:
        drive_letter (str): The drive letter (e.g., 'E:')
    """
    # if not drive_letter.endswith("\\"):
    #     drive_letter += "\\"
        
    try:
        # Use wmic to get the VolumeName for the drive
        wmic_cmd = ['wmic', 'volume', 'get', 'DriveLetter,Label']
        result = subprocess.run(wmic_cmd, capture_output=True, text=True, check=True)
        
        volume_name = None
        for line in result.stdout.splitlines():
            if drive_letter in line:
                parts = line.strip().split()
                if len(parts) >= 2:
                    volume_name = parts[1]
                break

        if not volume_name:
            logging.warning(f"Could not find volume name for {drive_letter}. Skipping eject.")
            return

        # Create diskpart script as a string
        diskpart_script = f"""
        select volume {volume_name}
        remove all dismount
        """

        # Run diskpart with the script
        subprocess.run(
            ['diskpart'],
            input=diskpart_script,
            text=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logging.info(f"Successfully ejected drive: {drive_letter}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to eject drive {drive_letter}: {e}")

if __name__ == "__main__":
    safely_eject_drive("E:")