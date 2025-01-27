FFmpeg

1. Download FFmpeg:

Go to the official FFmpeg website: https://www.ffmpeg.org/download.html
Under "Get packages & executable files," click on the Windows icon.
Click on "Windows builds from gyan.dev."
Download the latest "ffmpeg-git-full.7z" release.
2. Extract the Downloaded Files:

Right-click the downloaded .7z file and select "Extract Here" or "Extract to ffmpeg-git-full" using 7-Zip or your preferred file archiver.
Rename the extracted folder to "FFmpeg" for easier reference.
3. Move the FFmpeg Folder:

Move the "FFmpeg" folder to the root of your C: drive (e.g., C:\FFmpeg).
4. Add FFmpeg to the System Path:

Search for "Edit the system environment variables" in the Windows search bar and open it.
In the "System Properties" window, go to Advanced → Environment Variables.
Under1 "System variables," select "Path" and click "Edit."   
Click "New" and enter the path to the FFmpeg bin folder: C:\FFmpeg\bin
Click "OK" to save the changes.
5. Verify FFmpeg Installation:

Set up OAuth 2.0 Credentials
Open Command Prompt as administrator.
Type ffmpeg -version and press Enter.
If FFmpeg is installed correctly, you'll see the FFmpeg version information.

Set Up OAuth 2.0 Credentials:

Go to the Google Cloud Console.

Navigate to APIs & Services > Credentials.

Click "Create Credentials" and select "OAuth 2.0 Client ID".

Choose "Desktop App" as the application type.

Download the JSON file containing your OAuth 2.0 credentials and save it as client_secret.json.