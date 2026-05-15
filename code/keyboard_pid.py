import cv2
import time
from ultralytics import YOLO

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped


# =========================================================
# PID Controller
# =========================================================
class PID:
    def __init__(self, kp, ki, kd, output_limit, integral_limit=10000.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.output_limit = output_limit
        self.integral_limit = integral_limit

        self.prev_error = 0.0
        self.integral = 0.0
        self.prev_time = time.time()

    def reset(self):
        self.prev_error = 0.0
        self.integral = 0.0
        self.prev_time = time.time()

    def update(self, error):
        now = time.time()
        dt = now - self.prev_time

        if dt <= 0.0:
            dt = 1e-6

        # P
        p = self.kp * error

        # I
        self.integral += error * dt

        if self.integral > self.integral_limit:
            self.integral = self.integral_limit
        elif self.integral < -self.integral_limit:
            self.integral = -self.integral_limit

        i = self.ki * self.integral

        # D
        derivative = (error - self.prev_error) / dt
        d = self.kd * derivative

        output = p + i + d

        # 출력 제한
        if output > self.output_limit:
            output = self.output_limit
        elif output < -self.output_limit:
            output = -self.output_limit

        self.prev_error = error
        self.prev_time = now

        return output


class KeyboardFollower(Node):
    def __init__(self):
        super().__init__("keyboard_follower_yolo_pid")

        # =========================================================
        # 1. /cmd_vel 속도 명령 Publisher
        # =========================================================
        self.cmd_pub = self.create_publisher(TwistStamped, "/cmd_vel", 10)

        # =========================================================
        # 2. YOLOv11 모델 로드
        # =========================================================
        self.model = YOLO("yolo11n.pt")

        print("YOLOv11 model loaded.")
        print("Class names:")
        print(self.model.names)

        # =========================================================
        # 3. 터틀봇 Flask 카메라 스트림 주소
        # =========================================================
        self.turtlebot_ip = "10.10.14.23"
        self.stream_url = f"http://{self.turtlebot_ip}:5000/video_feed"

        self.cap = cv2.VideoCapture(self.stream_url)

        if not self.cap.isOpened():
            print("ERROR: Cannot open TurtleBot camera stream.")
            print("Check TurtleBot IP, Flask server, and network.")
            exit()

        print("Connected to TurtleBot camera stream.")
        print("Keyboard PID following mode started.")

        # =========================================================
        # 4. YOLO 클래스 설정
        # =========================================================
        # COCO 기준 keyboard 클래스 번호 = 66
        self.keyboard_class_id = 66

        # =========================================================
        # 5. PID 추적 제어 파라미터
        # =========================================================

        # 화면 중앙 허용 오차
        self.center_tolerance = 50

        # 화면 중심에서 너무 많이 벗어나면 전진/후진 금지
        self.forward_block_error = 220

        # 최대 속도 제한
        self.max_linear_speed = 0.06
        self.max_reverse_speed = -0.04
        self.max_angular_speed = 0.25

        # ---------------------------------------------------------
        # 거리 제어 기준
        # ---------------------------------------------------------
        # 기존 코드:
        # target_box_area = 45000
        # too_close_box_area = 70000
        #
        # PID에서는 중간값을 목표 거리로 둠
        # area가 작으면 멀다 -> 전진
        # area가 크면 가깝다 -> 후진
        # ---------------------------------------------------------
        self.target_box_area = 55000

        # 거리 허용 오차
        self.area_tolerance = 5000

        # =========================================================
        # 6. PID 객체 생성
        # =========================================================
        # 회전 PID
        # error_x > 0이면 키보드가 오른쪽에 있음
        # TurtleBot은 angular.z 음수일 때 오른쪽 회전
        # 그래서 나중에 - 부호를 붙여서 사용함
        self.angular_pid = PID(
            kp=0.0014,
            ki=0.0,
            kd=0.00025,
            output_limit=self.max_angular_speed,
            integral_limit=3000.0
        )

        # 거리 PID
        # area_error = target_box_area - box_area
        # area_error > 0이면 키보드가 멀다 -> 전진
        # area_error < 0이면 키보드가 가깝다 -> 후진
        self.linear_pid = PID(
            kp=0.0000020,
            ki=0.0,
            kd=0.0000004,
            output_limit=self.max_linear_speed,
            integral_limit=200000.0
        )

        # =========================================================
        # 7. 키보드 인식 확정 및 탐색 회전 파라미터
        # =========================================================
        self.required_detection_time = 2.0
        self.keyboard_detect_start_time = None
        self.keyboard_confirmed = False

        self.searching = False
        self.search_angular_speed = 0.18

        print("PID Control parameters:")
        print(f"center_tolerance = {self.center_tolerance}")
        print(f"target_box_area = {self.target_box_area}")
        print(f"area_tolerance = {self.area_tolerance}")
        print(f"max_linear_speed = {self.max_linear_speed}")
        print(f"max_reverse_speed = {self.max_reverse_speed}")
        print(f"max_angular_speed = {self.max_angular_speed}")
        print(f"forward_block_error = {self.forward_block_error}")
        print(f"required_detection_time = {self.required_detection_time}")
        print(f"search_angular_speed = {self.search_angular_speed}")

    # =========================================================
    # /cmd_vel 명령 전송
    # =========================================================
    def send_cmd(self, linear_x, angular_z):
        msg = TwistStamped()

        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = ""

        msg.twist.linear.x = float(linear_x)
        msg.twist.angular.z = float(angular_z)

        self.cmd_pub.publish(msg)

    def stop_robot(self):
        self.send_cmd(0.0, 0.0)

    def reset_pid(self):
        self.angular_pid.reset()
        self.linear_pid.reset()

    # =========================================================
    # 키보드 탐색 회전 시작
    # =========================================================
    def start_search_rotation(self):
        self.searching = True
        self.reset_pid()
        print("keyboard lost after confirmed detection -> start searching rotation")

    # =========================================================
    # 키보드 탐색 회전 중지
    # =========================================================
    def stop_search_rotation(self):
        self.searching = False
        self.reset_pid()
        self.stop_robot()
        print("keyboard found -> stop searching rotation")

    # =========================================================
    # 키보드 감지 시간 업데이트
    # =========================================================
    def update_detection_confirmation(self):
        current_time = time.time()

        if self.keyboard_detect_start_time is None:
            self.keyboard_detect_start_time = current_time
            print("keyboard detection started")

        detected_duration = current_time - self.keyboard_detect_start_time

        if detected_duration >= self.required_detection_time:
            if not self.keyboard_confirmed:
                print("keyboard confirmed for tracking")
                self.reset_pid()

            self.keyboard_confirmed = True

        return detected_duration

    # =========================================================
    # 속도 제한 함수
    # =========================================================
    def clamp(self, value, min_value, max_value):
        if value > max_value:
            return max_value
        elif value < min_value:
            return min_value
        return value

    # =========================================================
    # 메인 루프
    # =========================================================
    def run(self):
        while rclpy.ok():
            ret, frame = self.cap.read()

            if not ret:
                print("ERROR: Failed to read frame from TurtleBot stream.")
                self.stop_robot()
                break

            frame_height, frame_width = frame.shape[:2]
            frame_center_x = frame_width / 2

            # =====================================================
            # YOLOv11 키보드만 탐지
            # =====================================================
            results = self.model.predict(
                source=frame,
                classes=[self.keyboard_class_id],
                conf=0.25,
                imgsz=640,
                verbose=False
            )

            result = results[0]
            boxes = result.boxes

            selected_box = None
            max_area = 0

            # =====================================================
            # 여러 키보드가 잡히면 가장 크게 보이는 키보드 선택
            # =====================================================
            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                    box_width = x2 - x1
                    box_height = y2 - y1
                    box_area = box_width * box_height

                    if box_area > max_area:
                        max_area = box_area
                        selected_box = (x1, y1, x2, y2)

            # =====================================================
            # 키보드가 감지된 경우
            # =====================================================
            if selected_box is not None:
                detected_duration = self.update_detection_confirmation()

                if self.searching:
                    self.stop_search_rotation()

                x1, y1, x2, y2 = selected_box

                keyboard_center_x = (x1 + x2) / 2
                box_width = x2 - x1
                box_height = y2 - y1
                box_area = box_width * box_height

                error_x = keyboard_center_x - frame_center_x

                # -------------------------------------------------
                # 아직 2초 이상 인식되지 않은 경우
                # -------------------------------------------------
                if not self.keyboard_confirmed:
                    self.stop_robot()
                    self.reset_pid()

                    print(
                        f"keyboard detected but not confirmed yet | "
                        f"detected_time={detected_duration:.1f}/{self.required_detection_time:.1f}s -> stop"
                    )

                # -------------------------------------------------
                # 키보드가 2초 이상 안정적으로 인식된 경우
                # -------------------------------------------------
                else:
                    # =================================================
                    # 1. 회전 PID 제어
                    # =================================================
                    if abs(error_x) < self.center_tolerance:
                        angular_z = 0.0
                        self.angular_pid.reset()
                    else:
                        angular_output = self.angular_pid.update(error_x)

                        # error_x > 0이면 키보드가 오른쪽
                        # 오른쪽으로 돌려야 하므로 angular.z는 음수
                        angular_z = -angular_output

                        angular_z = self.clamp(
                            angular_z,
                            -self.max_angular_speed,
                            self.max_angular_speed
                        )

                    # =================================================
                    # 2. 거리 PID 제어
                    # =================================================
                    area_error = self.target_box_area - box_area

                    if abs(area_error) < self.area_tolerance:
                        linear_x = 0.0
                        self.linear_pid.reset()
                        distance_state = "good distance -> stop"

                    else:
                        linear_x = self.linear_pid.update(area_error)

                        # 전진/후진 속도 제한
                        linear_x = self.clamp(
                            linear_x,
                            self.max_reverse_speed,
                            self.max_linear_speed
                        )

                        if linear_x > 0:
                            distance_state = "far -> PID forward"
                        else:
                            distance_state = "too close -> PID reverse"

                    # =================================================
                    # 3. 화면 중심에서 너무 벗어나면 회전만 수행
                    # =================================================
                    if abs(error_x) > self.forward_block_error:
                        linear_x = 0.0
                        self.linear_pid.reset()
                        distance_state = "off center -> rotate only"

                    self.send_cmd(linear_x, angular_z)

                    print(
                        f"keyboard confirmed PID | "
                        f"error_x={error_x:.1f}, "
                        f"area_error={area_error:.1f}, "
                        f"box_w={box_width:.1f}, "
                        f"box_h={box_height:.1f}, "
                        f"area={box_area:.1f}, "
                        f"state={distance_state}, "
                        f"linear={linear_x:.3f}, "
                        f"angular={angular_z:.3f}"
                    )

            # =====================================================
            # 키보드가 감지되지 않은 경우
            # =====================================================
            else:
                self.keyboard_detect_start_time = None
                self.reset_pid()

                if not self.keyboard_confirmed:
                    self.stop_robot()
                    print("keyboard not confirmed yet and not detected -> stop")

                else:
                    if not self.searching:
                        self.start_search_rotation()

                    self.send_cmd(0.0, self.search_angular_speed)

                    print(
                        f"keyboard lost after confirmation -> searching... "
                        f"linear=0.00, "
                        f"angular={self.search_angular_speed:.2f}"
                    )

            # =====================================================
            # 화면 표시
            # =====================================================
            annotated_frame = result.plot()
            cv2.imshow("YOLOv11 Keyboard PID Following", annotated_frame)

            # ESC 누르면 종료
            if cv2.waitKey(1) & 0xFF == 27:
                self.stop_robot()
                break

            rclpy.spin_once(self, timeout_sec=0.001)

        self.stop_robot()
        self.cap.release()
        cv2.destroyAllWindows()


def main():
    rclpy.init()
    node = KeyboardFollower()

    try:
        node.run()

    except KeyboardInterrupt:
        print("KeyboardInterrupt: stopping robot...")

    finally:
        try:
            node.stop_robot()
        except Exception:
            pass

        node.destroy_node()
        rclpy.shutdown()
        print("Program finished.")


if __name__ == "__main__":
    main()
