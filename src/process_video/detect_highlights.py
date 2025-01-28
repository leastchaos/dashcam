import cv2
import numpy as np
from moviepy import VideoFileClip
import os
from ultralytics import YOLO  # For object detection

# Load YOLO model (small version for speed)
model = YOLO('yolov8n.pt')  # Detects cars, people, etc.

# =============================================
# Step 1: Detect Obstacles/Near-Misses with YOLO
# =============================================
def detect_objects(frame):
    results = model(frame, verbose=False)
    objects = []
    for box in results[0].boxes:
        class_id = int(box.cls)
        label = model.names[class_id]
        if label in ['car', 'person', 'bicycle', 'motorcycle']:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            objects.append((label, (x1, y1, x2, y2)))
    return objects

# =============================================
# Step 2: Detect Sudden Motion (Optical Flow)
# =============================================
def detect_sudden_motion(prev_frame, current_frame, threshold=30):
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
    motion_score = np.mean(magnitude)
    return motion_score > threshold

# =============================================
# Step 3: Scenic View Detection (Color Analysis)
# =============================================
def is_scenic_view(frame, saturation_threshold=100):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    avg_saturation = np.mean(hsv[:, :, 1])
    return avg_saturation > saturation_threshold  # High saturation = vibrant scenery

# =============================================
# Main Processing Loop (Efficient for Long Videos)
# =============================================
def analyze_video(video_path, output_dir="highlights", clip_duration=5):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_skip = int(fps * 2)  # Process every 2 seconds to reduce load
    highlights = []
    prev_frame = None
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % frame_skip != 0:
            continue

        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000

        # Detect objects (cars, pedestrians)
        objects = detect_objects(frame)
        if objects:
            print(f"Objects detected at {current_time}s: {objects}")
            highlights.append(current_time)

        # Detect sudden motion (e.g., swerving)
        if prev_frame is not None:
            if detect_sudden_motion(prev_frame, frame):
                print(f"Sudden motion at {current_time}s")
                highlights.append(current_time)

        # Detect scenic views (vibrant colors)
        if is_scenic_view(frame):
            print(f"Scenic view at {current_time}s")
            highlights.append(current_time)

        prev_frame = frame

    cap.release()

    # Extract clips around highlights
    highlights = sorted(set(highlights))
    video = VideoFileClip(video_path)
    os.makedirs(output_dir, exist_ok=True)

    for i, timestamp in enumerate(highlights):
        start = max(0, timestamp - clip_duration/2)
        end = start + clip_duration
        highlight = video.subclipped(start, end)
        highlight.write_videofile(
            os.path.join(output_dir, f"highlight_{i+1}.mp4"),
            codec="libx264",
            audio_codec="aac"
        )

# =============================================
# Run the Script
# =============================================
if __name__ == "__main__":
    video_path = "test.mp4"  # Replace with your video
    analyze_video(video_path, clip_duration=10)  # 10-second clips