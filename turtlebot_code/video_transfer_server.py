import cv2
import time
import threading
from flask import Flask, Response, render_template_string

app = Flask(__name__)

# =========================================================
# 1. USB 웹캠 설정
# =========================================================
CAMERA_INDEX = 0

camera = cv2.VideoCapture(CAMERA_INDEX)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
camera.set(cv2.CAP_PROP_FPS, 15)

if not camera.isOpened():
    print("ERROR: USB camera open failed.")
    print("Check CAMERA_INDEX or /dev/video*")
else:
    print("USB camera opened successfully.")

# =========================================================
# 2. 최신 프레임 저장 변수
# =========================================================
global_frame = None
frame_lock = threading.Lock()

encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]

# =========================================================
# 3. 카메라 프레임 캡처
# =========================================================
def capture_frames():
    global global_frame

    while True:
        success, frame_data = camera.read()

        if not success:
            print("ERROR: camera.read() failed")
            time.sleep(0.5)
            continue

        ret, buffer = cv2.imencode(
            ".jpg",
            frame_data,
            encode_param
        )

        if not ret:
            print("ERROR: JPEG encoding failed")
            time.sleep(0.1)
            continue

        frame = buffer.tobytes()

        with frame_lock:
            global_frame = frame

        time.sleep(0.03)

# =========================================================
# 4. 백그라운드 스레드 시작
# =========================================================
capture_thread = threading.Thread(target=capture_frames)
capture_thread.daemon = True
capture_thread.start()

# =========================================================
# 5. 웹 스트리밍
# =========================================================
def gen_frames():
    while True:
        with frame_lock:
            frame = global_frame

        if frame is None:
            time.sleep(0.05)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )

        time.sleep(0.03)

# =========================================================
# 6. Flask 라우터
# =========================================================
@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>TurtleBot Camera Stream</title>
    </head>
    <body>
        <h1>TurtleBot Camera Stream</h1>
        <img src="/video_feed" width="640">
    </body>
    </html>
    """)

@app.route("/video_feed")
def video_feed():
    return Response(
        gen_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

# =========================================================
# 7. 서버 실행
# =========================================================
if __name__ == "__main__":
    try:
        app.run(
            host="10.10.14.23",
            port=5000,
            debug=False,
            threaded=True,
            use_reloader=False
        )

    finally:
        camera.release()
        print("USB camera released.")
