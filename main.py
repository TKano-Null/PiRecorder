import os
import subprocess
import time
import cv2
from datetime import datetime

# 設定
SAVE_DIR = "/home/username/monitor_videos"  # 保存先ディレクトリ
MAX_FILES = 96                        # 最大保持ファイル数（1日分）
DURATION = 900                        # 動体検知後の録画秒数
VIDEO_DEVICE = '/dev/video0'          # ビデオデバイス
AUDIO_DEVICE = 'hw:2,0'              # オーディオデバイス
MOTION_THRESHOLD = 5000               # 動体検知の閾値（小さいほど敏感）
MIN_CONTOUR_AREA = 500                # 検知する動体の最小面積

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

def get_video_files():
    files = [os.path.join(SAVE_DIR, f) for f in os.listdir(SAVE_DIR) if f.endswith('.mp4')]
    files.sort(key=os.path.getmtime)
    return files

def manage_storage():
    files = get_video_files()
    while len(files) >= MAX_FILES:
        oldest_file = files.pop(0)
        os.remove(oldest_file)
        print(f"Deleted: {oldest_file}")

def record_video(filename):
    manage_storage()
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'v4l2',
        '-framerate', '10',
        '-video_size', '640x480',
        '-i', VIDEO_DEVICE,
        '-f', 'alsa',
        '-channels', '1',
        '-i', AUDIO_DEVICE,
        '-t', str(DURATION),
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '32',
        '-c:a', 'aac',
        filename
    ]

    print(f"Recording: {filename}")
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if result.returncode == 0:
        print(f"Completed: {filename}")
    else:
        print(f"Error: Recording failed (return code: {result.returncode})")
        print("FFmpeg command failed. Please check your camera and microphone settings.")
        exit(1)

def detect_motion():
    cap = cv2.VideoCapture(VIDEO_DEVICE)
    if not cap.isOpened():
        print("Error: Cannot open camera.")
        exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("Monitoring for motion...")
    prev_frame = None

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Cannot read frame.")
            exit(1)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if prev_frame is None:
            prev_frame = gray
            continue

        delta = cv2.absdiff(prev_frame, gray)
        thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_detected = any(cv2.contourArea(c) > MIN_CONTOUR_AREA for c in contours)

        if motion_detected:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(SAVE_DIR, f"video_{timestamp}.mp4")
            print(f"Motion detected! ({timestamp})")

            cap.release()
            record_video(filename)

            cap = cv2.VideoCapture(VIDEO_DEVICE)
            if not cap.isOpened():
                print("Error: Cannot reopen camera.")
                exit(1)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            prev_frame = None
            print("Monitoring for motion...")
        else:
            prev_frame = gray

        time.sleep(0.1)

    cap.release()

if __name__ == "__main__":
    print("Security System Started (Motion Detection Mode)...")
    try:
        detect_motion()
    except KeyboardInterrupt:
        print("Stopped.")
