from flask import Flask, Response, render_template, request
import cv2
import os
from datetime import datetime

app = Flask(__name__)

# Global variables
video_capture = None  # To manage video capture
video_writer = None  # To manage video recording
video_source = None  # To track the active video source ('camera', 'stream', 'file')
file_path = None  # To store the path of the uploaded video file
video_url = None  # To store the stream URL (if applicable)

# Directory for saving videos
SAVE_DIRECTORY = os.path.join(os.getcwd(), "static/videos")
os.makedirs(SAVE_DIRECTORY, exist_ok=True)  # Ensure the directory exists

# Video stream generator function
def generate_video():
    global video_capture, video_writer

    if not video_capture or not video_capture.isOpened():
        print("Error: Unable to open video stream.")
        return

    # Initialize the video writer if not already initialized
    if video_writer is None:
        filename = datetime.now().strftime("video_%Y%m%d_%H%M%S.mp4")
        filepath = os.path.join(SAVE_DIRECTORY, filename)

        # Configure the codec and output settings
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for MP4
        fps = 20.0  # Frames per second
        width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Create the video writer object
        video_writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
        print(f"Recording video to: {filepath}")

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Error: Unable to read video stream.")
            break

        # Write the frame to the video file
        if video_writer:
            video_writer.write(frame)

        # Encode the frame for streaming
        ret, jpeg = cv2.imencode('.jpg', frame)
        if not ret:
            print("Error: Unable to encode frame.")
            continue

        # Yield the encoded frame
        frame_data = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n\r\n')


@app.route('/', methods=['GET', 'POST'])
def index():
    global video_capture, video_writer, video_source, file_path, video_url

    if request.method == 'POST':
        action = request.form.get('action')

        # Start Camera
        if action == 'start_camera':
            video_source = 'camera'
            video_capture = cv2.VideoCapture(0)  # Open default camera

        # Stop Camera
        elif action == 'stop_camera':
            video_source = None
            if video_writer:
                video_writer.release()
                video_writer = None
            if video_capture:
                video_capture.release()
                video_capture = None

        # Start Stream
        elif action == 'start_stream':
            video_source = 'stream'
            video_url = request.form.get('video_url')  # Get the stream URL
            if video_url:
                video_capture = cv2.VideoCapture(video_url)
                if not video_capture.isOpened():
                    print("Error: Unable to open video stream.")
                    video_source = None
                    video_url = None

        # Stop Stream
        elif action == 'stop_stream':
            video_source = None
            video_url = None
            if video_writer:
                video_writer.release()
                video_writer = None
            if video_capture:
                video_capture.release()
                video_capture = None

        # Start File
        elif action == 'start_file':
            video_source = 'file'
            uploaded_file = request.files['file']
            file_path = os.path.join(SAVE_DIRECTORY, uploaded_file.filename)
            uploaded_file.save(file_path)
            video_capture = cv2.VideoCapture(file_path)

        # Stop File
        elif action == 'stop_file':
            video_source = None
            if video_writer:
                video_writer.release()
                video_writer = None
            if video_capture:
                video_capture.release()
                video_capture = None

    # List recorded videos
    recorded_videos = []
    if os.path.exists(SAVE_DIRECTORY):
        recorded_videos = [f for f in os.listdir(SAVE_DIRECTORY)]

    # Return the updated page (no redirection)
    return render_template(
        'index.html',
        video_source=video_source,
        video_url=video_url,  # This ensures the stream URL is passed to the template
        camera_active=(video_source == 'camera'),
        stream_active=(video_source == 'stream'),
        recorded_videos=recorded_videos
    )


@app.route('/video_feed')
def video_feed():
    global video_capture
    if video_capture and video_capture.isOpened():
        return Response(generate_video(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return "Error: No video stream available", 400


# Run the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
