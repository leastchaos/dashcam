from datetime import datetime, timedelta
import fitparse
import cv2
import numpy as np
from moviepy import VideoFileClip
from pathlib import Path

def parse_fit_file(fit_path: Path):
    """Extracts cycling data from FIT file with timestamps"""
    fitfile = fitparse.FitFile(str(fit_path))
    data = []
    
    for record in fitfile.get_messages("record"):
        entry = {
            "timestamp": None,
            "speed": None,
            "heart_rate": None,
            "cadence": None,
            "power": None
        }
        
        for field in record:
            if field.name == "timestamp":
                entry["timestamp"] = field.value
            elif field.name == "speed":
                entry["speed"] = field.value * 3.6  # Convert m/s to km/h
            elif field.name == "heart_rate":
                entry["heart_rate"] = field.value
            elif field.name == "cadence":
                entry["cadence"] = field.value
            elif field.name == "power":
                entry["power"] = field.value
        
        data.append(entry)
    
    return data

def create_overlay_frame(data, video_time, base_size=(1920, 1080)):
    """Creates a transparent overlay image with metrics"""
    overlay = np.zeros((base_size[1], base_size[0], 4), dtype=np.uint8)
    
    # Find closest data point to video timestamp
    closest = min(data, key=lambda x: abs(x["timestamp"] - video_time))
    
    # Dashboard configuration
    dashboard = {
        "position": (50, 50),
        "font_scale": 1.2,
        "color": (255, 255, 255, 255),
        "thickness": 2
    }
    
    y_offset = dashboard["position"][1]
    x_offset = dashboard["position"][0]
    
    # Speed
    cv2.putText(overlay, f"Speed: {closest['speed']:.1f} km/h", 
                (x_offset, y_offset), cv2.FONT_HERSHEY_SIMPLEX,
                dashboard["font_scale"], dashboard["color"], dashboard["thickness"])
    
    # Heart Rate
    cv2.putText(overlay, f"HR: {closest['heart_rate']} bpm", 
                (x_offset, y_offset + 40), cv2.FONT_HERSHEY_SIMPLEX,
                dashboard["font_scale"], dashboard["color"], dashboard["thickness"])
    
    # Cadence
    cv2.putText(overlay, f"Cadence: {closest['cadence']} rpm", 
                (x_offset, y_offset + 80), cv2.FONT_HERSHEY_SIMPLEX,
                dashboard["font_scale"], dashboard["color"], dashboard["thickness"])
    
    # Power
    cv2.putText(overlay, f"Power: {closest['power']} W", 
                (x_offset, y_offset + 120), cv2.FONT_HERSHEY_SIMPLEX,
                dashboard["font_scale"], dashboard["color"], dashboard["thickness"])
    
    return overlay

def process_video(video_path: Path, fit_data, output_path: Path):
    """Adds data overlays to video"""
    video_clip = VideoFileClip(str(video_path))
    fit_start_time = fit_data[0]["timestamp"]
    
    def make_frame(original_frame, t):
        # Convert video time to FIT file time
        video_time = fit_start_time + timedelta(seconds=t)
        overlay = create_overlay_frame(fit_data, video_time)
        
        # Get original frame
        # original_frame = video_clip.get_frame(t)
        original_frame = cv2.cvtColor(original_frame, cv2.COLOR_RGB2BGRA)
        
        # Combine frames
        combined = cv2.addWeighted(original_frame, 1, overlay, 0.7, 0)
        return cv2.cvtColor(combined, cv2.COLOR_BGRA2BGR)
    
    # Create output video
    processed_clip = video_clip.transform(make_frame)
    processed_clip.write_videofile(str(output_path), codec="libx264", audio_codec="aac")

if __name__ == "__main__":
    # Configuration
    video_path = Path("test.mp4")
    fit_path = Path("test.fit")
    output_path = Path("output_with_overlays.mp4")
    
    # Process data and video
    fit_data = parse_fit_file(fit_path)
    process_video(video_path, fit_data, output_path)