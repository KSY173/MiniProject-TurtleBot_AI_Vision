import cv2
import easyocr
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped


class OCRRobotController(Node):

    def __init__(self):
        super().__init__("ocr_robot_controller")

        # =========================================================
        # 1. ROS2 /cmd_vel Publisher
        # =========================================================
        self.cmd_pub = self.create_publisher(
            TwistStamped,
            "/cmd_vel",
            10
        )

        # =========================================================
        # 2. EasyOCR 초기화
        # =========================================================
        print("Loading EasyOCR...")

        # 한글 명령어 인식용
        # 필요하면 ['ko', 'en'] 으로 바꿔도 됨
        self.reader = easyocr.Reader(['ko'])

        print("EasyOCR loaded.")

        # =========================================================
        # 3. TurtleBot Flask 카메라 스트림 주소
        # =========================================================
        self.turtlebot_ip = "10.10.14.23"
        self.stream_url = f"http://{self.turtlebot_ip}:5000/video_feed"

        self.cap = cv2.VideoCapture(self.stream_url)

        if not self.cap.isOpened():
            print("ERROR: Cannot open TurtleBot camera stream.")
            print("Check TurtleBot IP, Flask server, and network.")
            raise RuntimeError("Camera stream open failed")

        print("Connected to TurtleBot stream.")
        print("OCR robot control mode started.")
        print("Press Ctrl + C to stop.")

        # =========================================================
        # 4. 속도 설정
        # =========================================================
        self.forward_speed = 0.06
        self.backward_speed = -0.06
        self.turn_speed = 0.30

        # =========================================================
        # 5. OCR 안정화 설정
        # =========================================================

        # 너무 낮은 OCR 점수는 무시
        # 기존 결과에서 TEXT: 9 | SCORE: 0.13 처럼 낮은 점수가 나왔으므로
        # 이런 오인식은 명령어 판단에서 제외
        self.min_score = 0.40

        # OCR은 매 프레임 돌리면 느릴 수 있으므로 N프레임마다 한 번만 수행
        self.ocr_interval_frames = 10
        self.frame_count = 0

        # 마지막으로 인식된 명령 저장
        self.last_command = "STOP"
        self.last_command_time = time.time()

        # 명령이 오래 안 보이면 자동 정지
        self.command_timeout = 1.0

    # =============================================================
    # /cmd_vel 명령 전송
    # =============================================================
    def send_cmd(self, linear_x, angular_z):
        msg = TwistStamped()

        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = ""

        msg.twist.linear.x = float(linear_x)
        msg.twist.angular.z = float(angular_z)

        self.cmd_pub.publish(msg)

    # =============================================================
    # 정지
    # =============================================================
    def stop_robot(self):
        self.send_cmd(0.0, 0.0)

    # =============================================================
    # OCR용 전처리
    # =============================================================
    def preprocess_frame(self, frame):
        # OCR 속도를 위해 크기 줄이기
        frame = cv2.resize(frame, (640, 480))

        # 회색조 변환
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 글자 대비 향상
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        return gray

    # =============================================================
    # OCR 결과에서 명령어 추출
    # =============================================================
    def extract_command(self, results):
        detected_text = ""

        for result in results:
            bbox, text, score = result

            print(f"TEXT: {text} | SCORE: {score:.2f}")

            # 점수가 너무 낮으면 무시
            if score < self.min_score:
                continue

            detected_text += text + " "

        detected_text = detected_text.replace(" ", "")

        print(f"FILTERED TEXT: {detected_text}")

        # =========================================================
        # 명령어 판단
        # =========================================================
        if "전진" in detected_text:
            return "FORWARD"

        elif "후진" in detected_text:
            return "BACKWARD"

        elif "좌회전" in detected_text or "왼쪽" in detected_text:
            return "LEFT"

        elif "우회전" in detected_text or "오른쪽" in detected_text:
            return "RIGHT"

        elif "정지" in detected_text or "멈춰" in detected_text or "멈춤" in detected_text:
            return "STOP"

        else:
            return None

    # =============================================================
    # 명령어에 따라 로봇 제어
    # =============================================================
    def execute_command(self, command):

        if command == "FORWARD":
            self.send_cmd(self.forward_speed, 0.0)
            print("COMMAND: FORWARD")

        elif command == "BACKWARD":
            self.send_cmd(self.backward_speed, 0.0)
            print("COMMAND: BACKWARD")

        elif command == "LEFT":
            self.send_cmd(0.0, self.turn_speed)
            print("COMMAND: LEFT")

        elif command == "RIGHT":
            self.send_cmd(0.0, -self.turn_speed)
            print("COMMAND: RIGHT")

        elif command == "STOP":
            self.stop_robot()
            print("COMMAND: STOP")

        else:
            self.stop_robot()
            print("NO COMMAND -> STOP")

    # =============================================================
    # 메인 루프
    # =============================================================
    def run(self):

        while rclpy.ok():

            ret, frame = self.cap.read()

            if not ret:
                print("ERROR: Failed to read frame from TurtleBot stream.")
                self.stop_robot()
                break

            self.frame_count += 1

            # =====================================================
            # N프레임마다 OCR 수행
            # =====================================================
            if self.frame_count % self.ocr_interval_frames == 0:

                ocr_frame = self.preprocess_frame(frame)

                results = self.reader.readtext(ocr_frame)

                command = self.extract_command(results)

                if command is not None:
                    self.last_command = command
                    self.last_command_time = time.time()
                    self.execute_command(command)

                else:
                    # 명령어가 인식되지 않으면 정지
                    self.last_command = "STOP"
                    self.last_command_time = time.time()
                    self.stop_robot()
                    print("NO COMMAND -> STOP")

            # =====================================================
            # 명령어가 일정 시간 이상 안 들어오면 안전 정지
            # =====================================================
            current_time = time.time()

            if current_time - self.last_command_time > self.command_timeout:
                self.last_command = "STOP"
                self.stop_robot()
                print("COMMAND TIMEOUT -> STOP")
                self.last_command_time = current_time

            # =====================================================
            # ROS 콜백 처리
            # =====================================================
            rclpy.spin_once(
                self,
                timeout_sec=0.001
            )

        # =========================================================
        # 종료 처리
        # =========================================================
        self.stop_robot()
        self.cap.release()


def main():

    rclpy.init()

    node = None

    try:
        node = OCRRobotController()
        node.run()

    except KeyboardInterrupt:
        print("KeyboardInterrupt: stopping robot...")

    except Exception as e:
        print(f"ERROR: {e}")

    finally:
        if node is not None:
            try:
                node.stop_robot()
            except Exception:
                pass

            node.destroy_node()

        rclpy.shutdown()

        print("Program finished.")


if __name__ == "__main__":
    main()
