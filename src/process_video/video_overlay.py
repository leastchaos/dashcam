import os
import datetime
import garminconnect
import fitparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from moviepy import VideoClip
# from moviepy.video.tools.drawing import mplfig_to_npimage
from PIL import Image, ImageDraw, ImageFont


import matplotlib.pyplot as plt
import numpy as np

def mplfig_to_npimage(fig):
    """Converts a Matplotlib figure to a NumPy image array."""
    fig.canvas.draw()  # Important: Draw the figure first
    image_array = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    image_array = image_array.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    return image_array


# Configuration
GARMIN_EMAIL = "leastchaos@gmail.com"
GARMIN_PASSWORD = ""
MAPBOX_ACCESS_TOKEN = "your_mapbox_token"
VIDEO_RESOLUTION = (1920, 1080)
FPS = 30

# 1. Download FIT file from Garmin Connect
def get_garmin_client(email, password):
    client = garminconnect.Garmin(email, password)
    client.login()
    return client

def download_latest_activity(client):
    activities = client.get_activities(0, 1)
    if not activities:
        raise ValueError("No activities found")
    
    activity_id = activities[0]["activityId"]
    fit_data = client.download_activity(activity_id, dl_fmt='fit')
    return fit_data

# 2. Parse FIT file
def parse_fit_file(fit_data):
    fitfile = fitparse.FitFile(fit_data)
    
    records = []
    for record in fitfile.get_messages("record"):
        r = {d.name: d.value for d in record}
        if 'position_lat' in r and 'position_long' in r:
            r['latitude'] = r['position_lat'] * (180 / 2**31)
            r['longitude'] = r['position_long'] * (180 / 2**31)
        records.append(r)
    
    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    return df

# 3. Generate Map Image
def generate_map_image(coords, access_token):
    from urllib.request import urlretrieve
    
    lon, lat = zip(*[(c[1], c[0]) for c in coords])
    center = f"{sum(lon)/len(lon)},{sum(lat)/len(lat)}"
    url = f"https://api.mapbox.com/styles/v1/mapbox/outdoors-v11/static/path-3+f44-0.5({','.join([f'{lon},{lat}' for lon,lat in coords])})/auto/800x600?access_token={access_token}&padding=50"
    
    map_path = "map.png"
    urlretrieve(url, map_path)
    return Image.open(map_path)

# 4. Create Video Overlay
def create_overlay_animation(df, map_img):
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    ax = fig.add_subplot(111)
    ax.imshow(map_img, extent=[0, 100, 0, 100])
    ax.axis('off')
    
    duration = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
    
    def make_frame(t):
        current_idx = int(t / duration * len(df))
        row = df.iloc[current_idx]
        
        # Clear previous frame
        ax.clear()
        ax.imshow(map_img, extent=[0, 100, 0, 100])
        ax.axis('off')
        
        # Plot current position
        ax.plot(row['longitude'], row['latitude'], 'ro', markersize=10)
        
        # Create info overlay
        info_text = f"""
        Speed: {row.get('speed', 0)*3.6:.1f} km/h
        Heart Rate: {row.get('heart_rate', 0)} bpm
        Cadence: {row.get('cadence', 0)} rpm
        Power: {row.get('power', 0)} W
        Elevation: {row.get('altitude', 0):.1f} m
        """
        
        ax.text(5, 95, info_text, fontsize=20, color='white',
                bbox=dict(facecolor='black', alpha=0.7))
        
        return mplfig_to_npimage(fig)
    
    animation = VideoClip(make_frame, duration=duration)
    return animation

# Main execution
if __name__ == "__main__":
    # Download data
    client = get_garmin_client(GARMIN_EMAIL, GARMIN_PASSWORD)
    fit_data = download_latest_activity(client)
    
    # Save FIT file
    with open("activity.fit", "wb") as f:
        f.write(fit_data)
    
    # Parse data
    df = parse_fit_file(fit_data)
    coords = [(lat, lon) for lat, lon in zip(df['latitude'], df['longitude'])]
    
    # Generate map
    map_img = generate_map_image(coords, MAPBOX_ACCESS_TOKEN)
    
    # Create animation
    animation = create_overlay_animation(df, map_img)
    
    # Add audio (optional) and write video
    animation.write_videofile("cycling_overlay.mp4", fps=FPS, codec='libx264')
    
    # Cleanup
    plt.close('all')
    os.remove("map.png")
    os.remove("activity.fit")