from pathlib import Path
import shutil

def move_all_files_in_folder(input_folder: Path, output_folder: Path) -> None:
    """
    Moves all files from the input folder to the output folder, renaming files
    in the destination if conflicts occur while preserving original files.

    Args:
        input_folder: Source directory containing files to move
        output_folder: Target directory for moved files
    """
    # Create output directory if it doesn't exist
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Get all files in input directory (excluding directories)
    files_to_move = [f for f in input_folder.iterdir() if f.is_file()]
    
    for src_path in files_to_move:
        # Skip the output folder if it's inside input folder
        if src_path == output_folder:
            continue
            
        # Create destination path and handle name conflicts
        dest_path = output_folder / src_path.name
        conflict_number = 0
        
        # Find first available filename
        while dest_path.exists():
            conflict_number += 1
            stem = src_path.stem
            suffix = src_path.suffix
            dest_path = output_folder / f"{stem}_{conflict_number}{suffix}"
        
        # Perform the move
        shutil.move(str(src_path), str(dest_path))
        print(f"Moved '{src_path.name}' to '{dest_path.relative_to(output_folder.parent)}'")

if __name__ == "__main__":
    input_folder = Path("C:/Video/OA4")
    output_folder = Path("C:/Video/OA4/test")
    
    move_all_files_in_folder(input_folder, output_folder)