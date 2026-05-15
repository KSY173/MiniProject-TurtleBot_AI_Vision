# 🤖 TurtleBot3 YOLO OCR Vision Control

![Python](https://img.shields.io/badge/Language-Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![ROS2 Jazzy](https://img.shields.io/badge/ROS2-Jazzy-22314E?style=for-the-badge&logo=ros&logoColor=white)
![TurtleBot3](https://img.shields.io/badge/Robot-TurtleBot3-00A3E0?style=for-the-badge)
![Raspberry Pi 5](https://img.shields.io/badge/SBC-Raspberry%20Pi%205-C51A4A?style=for-the-badge&logo=raspberrypi&logoColor=white)
![OpenCV](https://img.shields.io/badge/Vision-OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![YOLO](https://img.shields.io/badge/AI-YOLOv11-00FFFF?style=for-the-badge)
![OCR](https://img.shields.io/badge/OCR-EasyOCR-FF6F00?style=for-the-badge)

ROS2 Jazzy 환경에서 TurtleBot3와 Raspberry Pi 5를 기반으로 구현한 **비전 기반 TurtleBot3 제어 미니 프로젝트**입니다.

TurtleBot3에 연결된 USB 카메라 영상을 Flask 서버로 스트리밍하고, Remote PC에서 OpenCV, YOLOv11, EasyOCR을 활용하여 객체와 문자를 인식한 뒤 ROS2 `/cmd_vel` 토픽으로 TurtleBot3를 제어합니다.

본 프로젝트는 크게 두 가지 기능으로 구성됩니다.

1. **YOLOv11 기반 키보드 객체 추적**
2. **EasyOCR 기반 한글 명령어 인식 주행**

TurtleBot3 기본 구동을 위한 bringup은 직접 작성한 코드가 아니라, ROBOTIS 공식 `turtlebot3` 패키지의 `turtlebot3_bringup/launch/robot.launch.py`를 사용했습니다.

<br>

## 📌 1. Project Overview (프로젝트 개요)

* **Robot Platform:** TurtleBot3
* **SBC:** Raspberry Pi 5
* **ROS Version:** ROS2 Jazzy
* **Language:** Python
* **Camera:** USB Camera
* **Object Detection:** YOLOv11 `yolo11n.pt`
* **OCR:** EasyOCR
* **Image Processing:** OpenCV
* **Video Streaming:** Flask MJPEG Streaming
* **Robot Control Topic:** `/cmd_vel`
* **ROS Message Type:** `geometry_msgs/msg/TwistStamped`

<br>

## 🔗 2. External Source / Bringup Reference

TurtleBot3의 기본 구동을 위한 bringup 코드는 직접 작성하지 않고, ROBOTIS 공식 TurtleBot3 ROS2 패키지를 사용했습니다.

### ROBOTIS TurtleBot3 Package

```bash
git clone -b jazzy https://github.com/ROBOTIS-GIT/turtlebot3.git
```

사용한 bringup launch file 경로:

```text
turtlebot3/turtlebot3_bringup/launch/robot.launch.py
```

실행 명령어:

```bash
ros2 launch turtlebot3_bringup robot.launch.py
```

ROBOTIS 공식 TurtleBot3 e-Manual에서도 TurtleBot3 SBC에서 기본 bringup을 실행할 때 아래 명령을 사용하도록 안내합니다.

```bash
ros2 launch turtlebot3_bringup robot.launch.py
```

또한 ROS2 Jazzy 버전부터 TurtleBot3의 `/cmd_vel` 토픽은 기본적으로 `TwistStamped` 타입을 사용합니다.  
따라서 본 프로젝트의 Python 제어 코드도 `geometry_msgs/msg/TwistStamped` 메시지를 사용하여 `/cmd_vel`을 publish하도록 작성했습니다.

> Source: ROBOTIS TurtleBot3 Official Repository / TurtleBot3 e-Manual

<br>

## 💡 3. Core Features (핵심 기능)

### 🎥 [1] TurtleBot3 카메라 실시간 스트리밍

TurtleBot3의 Raspberry Pi 5에 연결된 USB 카메라 영상을 OpenCV로 읽고, Flask 서버를 통해 실시간으로 스트리밍합니다.

* USB 카메라 연결
* OpenCV 기반 프레임 캡처
* JPEG 인코딩
* Flask `/video_feed` 라우터를 통한 MJPEG 스트리밍
* Remote PC에서 TurtleBot3 카메라 영상 확인 가능

실행 파일:

```text
video_transfer_server.py
```

실행 명령어:

```bash
python3 video_transfer_server.py
```

영상 확인 주소 예시:

```text
http://10.10.14.23:5000/video_feed
```

<br>

### ⌨️ [2] YOLOv11 기반 키보드 객체 추적

YOLOv11 모델을 이용하여 TurtleBot3 카메라 영상 속 `keyboard` 객체를 인식하고, TurtleBot3가 키보드를 따라가도록 제어합니다.

* YOLOv11 `yolo11n.pt` 모델 사용
* COCO Dataset 기준 `keyboard` 클래스 ID `66` 탐지
* 여러 개의 키보드가 감지될 경우 가장 크게 보이는 객체 선택
* 객체 중심 좌표를 기준으로 회전 제어
* Bounding Box 면적을 기준으로 전진/후진 제어
* PID 제어를 적용하여 급격한 움직임 완화
* 키보드를 놓치면 제자리 회전으로 재탐색

실행 파일:

```text
keyboard_pid.py
```

실행 명령어:

```bash
python3 keyboard_pid.py
```

<br>

### 🎯 [3] PID 기반 방향 및 거리 제어

YOLO로 검출된 키보드의 위치와 크기를 기반으로 TurtleBot3의 속도를 제어합니다.

#### 방향 제어

* 키보드 중심이 화면 오른쪽에 있으면 오른쪽 회전
* 키보드 중심이 화면 왼쪽에 있으면 왼쪽 회전
* 키보드가 화면 중앙 근처에 있으면 회전 정지

#### 거리 제어

* Bounding Box 면적이 작으면 키보드가 멀다고 판단하여 전진
* Bounding Box 면적이 크면 키보드가 가깝다고 판단하여 후진
* 목표 면적 근처에서는 정지

| 항목 | 설정값 |
|---|---|
| 중심 허용 오차 | `50 px` |
| 전진 차단 기준 | `220 px` |
| 목표 Bounding Box 면적 | `55000` |
| 면적 허용 오차 | `5000` |
| 최대 전진 속도 | `0.06 m/s` |
| 최대 후진 속도 | `-0.04 m/s` |
| 최대 회전 속도 | `0.25 rad/s` |
| 탐색 회전 속도 | `0.18 rad/s` |
| 객체 인식 확정 시간 | `2.0 s` |

<br>

### 🔤 [4] EasyOCR 기반 한글 명령어 주행

EasyOCR을 이용하여 카메라 영상 속 한글 명령어를 인식하고, 인식 결과에 따라 TurtleBot3를 제어합니다.

실행 파일:

```text
ocr_test.py
```

실행 명령어:

```bash
python3 ocr_test.py
```

지원 명령어:

| 인식 문자 | TurtleBot3 동작 |
|---|---|
| `전진` | 앞으로 이동 |
| `후진` | 뒤로 이동 |
| `좌회전` | 왼쪽 회전 |
| `왼쪽` | 왼쪽 회전 |
| `우회전` | 오른쪽 회전 |
| `오른쪽` | 오른쪽 회전 |
| `정지` | 정지 |
| `멈춰` | 정지 |
| `멈춤` | 정지 |

OCR 안정화 로직:

* OCR 신뢰도 `0.40` 미만 결과는 무시
* 매 프레임마다 OCR을 수행하지 않고 10프레임마다 한 번씩 실행
* 명령어가 감지되지 않으면 정지
* 명령어가 1초 이상 갱신되지 않으면 자동 정지

<br>

## 🧠 4. System Architecture (시스템 구조)

```text
[TurtleBot3 + Raspberry Pi 5]
        │
        │ USB Camera
        ▼
[OpenCV Camera Capture]
        │
        ▼
[Flask MJPEG Streaming Server]
        │
        │  http://TURTLEBOT_IP:5000/video_feed
        ▼
[Remote PC / ROS2 Jazzy Python Node]
        │
        ├── YOLOv11 Object Detection
        │       └── Keyboard Detection + PID Tracking
        │
        └── EasyOCR Text Recognition
                └── Korean Command Detection
        │
        ▼
[ROS2 /cmd_vel Publisher]
        │
        │ geometry_msgs/msg/TwistStamped
        ▼
[TurtleBot3 Movement Control]
```

<br>

## 🛠️ 5. Tech Stack (기술 스택)

| 분류 | 사용 기술 |
|---|---|
| Robot | TurtleBot3 |
| SBC | Raspberry Pi 5 |
| OS / Middleware | Ubuntu, ROS2 Jazzy |
| Language | Python |
| Camera Processing | OpenCV |
| Object Detection | YOLOv11, Ultralytics |
| OCR | EasyOCR |
| Video Streaming | Flask |
| ROS2 Topic | `/cmd_vel` |
| ROS2 Message | `geometry_msgs/msg/TwistStamped` |
| Bringup Package | ROBOTIS TurtleBot3 official package |

<br>

## 🚀 6. How to Run (실행 방법)

### 1) ROBOTIS TurtleBot3 패키지 설치

TurtleBot3 bringup을 위해 ROBOTIS 공식 TurtleBot3 패키지를 사용합니다.

```bash
git clone -b jazzy https://github.com/ROBOTIS-GIT/turtlebot3.git
```

워크스페이스 예시:

```bash
mkdir -p ~/turtlebot3_ws/src
cd ~/turtlebot3_ws/src
git clone -b jazzy https://github.com/ROBOTIS-GIT/turtlebot3.git
cd ~/turtlebot3_ws
colcon build
source install/setup.bash
```

<br>

### 2) TurtleBot3 모델 설정

사용하는 TurtleBot3 모델에 맞게 환경 변수를 설정합니다.

```bash
export TURTLEBOT3_MODEL=burger
```

또는 사용하는 모델에 따라 아래 중 하나로 설정할 수 있습니다.

```bash
export TURTLEBOT3_MODEL=burger
export TURTLEBOT3_MODEL=waffle
export TURTLEBOT3_MODEL=waffle_pi
```

본 프로젝트에서는 TurtleBot3 실물 로봇 burger와 Raspberry Pi 5 환경에서 테스트했습니다.

<br>

### 3) TurtleBot3 Bringup 실행

TurtleBot3의 Raspberry Pi 5에서 ROBOTIS 공식 bringup launch file을 실행합니다.

```bash
ros2 launch turtlebot3_bringup robot.launch.py
```

사용한 launch file 경로:

```text
turtlebot3/turtlebot3_bringup/launch/robot.launch.py
```

<br>

### 4) TurtleBot3 카메라 스트리밍 서버 실행

TurtleBot3의 Raspberry Pi 5에서 카메라 스트리밍 서버를 실행합니다.

```bash
python3 video_transfer_server.py
```

브라우저에서 영상 확인:

```text
http://TURTLEBOT_IP:5000/video_feed
```

예시:

```text
http://10.10.14.23:5000/video_feed
```

<br>

### 5) YOLO 키보드 추적 실행

Remote PC에서 YOLO 기반 키보드 추적 코드를 실행합니다.

```bash
python3 keyboard_pid.py
```

실행 후 카메라 화면에 키보드가 2초 이상 안정적으로 인식되면 TurtleBot3가 키보드를 추적합니다.

<br>

### 6) OCR 명령어 제어 실행

Remote PC에서 OCR 기반 한글 명령어 제어 코드를 실행합니다.

```bash
python3 ocr_test.py
```

한글 명령어가 적힌 종이나 화면을 TurtleBot3 카메라에 보여주면, OCR 결과에 따라 TurtleBot3가 움직입니다.

<br>

## 🧩 7. Main Code Description (주요 코드 설명)

### `video_transfer_server.py`

TurtleBot3의 Raspberry Pi 5에 연결된 USB 카메라 영상을 Flask 서버로 전송하는 코드입니다.

주요 기능:

* OpenCV를 이용한 USB 카메라 프레임 캡처
* 320x240 해상도, 15 FPS 설정
* JPEG 인코딩
* Flask `/video_feed` 라우터를 통한 MJPEG 스트리밍
* Remote PC에서 브라우저로 실시간 영상 확인

<br>

### `keyboard_pid.py`

YOLOv11을 이용하여 카메라 영상 속 키보드를 인식하고 TurtleBot3가 키보드를 따라가도록 제어하는 코드입니다.

주요 기능:

* `yolo11n.pt` 모델 로드
* COCO Dataset의 `keyboard` 클래스만 탐지
* 가장 큰 Bounding Box 선택
* 화면 중심 오차 기반 회전 제어
* Bounding Box 면적 기반 전진/후진 제어
* PID 제어 적용
* 키보드 2초 이상 인식 시 추적 시작
* 키보드 미탐지 시 탐색 회전 수행
* `/cmd_vel` 토픽으로 `TwistStamped` 메시지 publish

<br>

### `ocr_test.py`

EasyOCR을 이용해 한글 명령어를 인식하고 TurtleBot3를 제어하는 코드입니다.

주요 기능:

* EasyOCR 한국어 모델 사용
* 카메라 프레임 Grayscale 변환
* Gaussian Blur 기반 전처리
* OCR 신뢰도 기준 이하 결과 제거
* 한글 명령어 분류
* 명령어에 따라 TurtleBot3 이동
* 명령어 미검출 또는 timeout 발생 시 자동 정지
* `/cmd_vel` 토픽으로 `TwistStamped` 메시지 publish

<br>

### `index.html`

카메라 스트리밍 화면을 웹 브라우저에서 확인하기 위한 HTML 템플릿입니다.

주요 기능:

* 스트리밍 영상 출력
* 웹 페이지 기반 카메라 확인
* TurtleBot3 카메라 영상 모니터링용 화면 구성

<br>

## ⚙️ 8. Control Logic (제어 로직)

### YOLO 키보드 추적 로직

```text
1. TurtleBot3 카메라 영상 수신
2. YOLOv11 모델로 keyboard 객체 탐지
3. 여러 객체 중 가장 큰 Bounding Box 선택
4. 키보드가 2초 이상 안정적으로 감지되면 추적 시작
5. 키보드 중심이 화면 중심에서 벗어나면 PID 기반 회전 제어
6. Bounding Box 면적이 목표보다 작으면 전진
7. Bounding Box 면적이 목표보다 크면 후진
8. 목표 거리 근처에서는 정지
9. 키보드를 놓치면 제자리 회전으로 재탐색
```

<br>

### OCR 명령어 제어 로직

```text
1. TurtleBot3 카메라 영상 수신
2. 10프레임마다 OCR 수행
3. OCR 결과 중 신뢰도 0.40 이상만 사용
4. 인식된 문자열에서 공백 제거
5. 전진/후진/좌회전/우회전/정지 명령어 판단
6. 명령어에 따라 /cmd_vel publish
7. 명령어가 없거나 timeout 발생 시 자동 정지
```

<br>

## 🛠️ 9. Troubleshooting (문제 해결 과정)

### 1. TurtleBot3가 `/cmd_vel`을 받아도 움직이지 않는 문제

* **Issue:** Python 코드에서 `/cmd_vel`을 publish해도 TurtleBot3가 움직이지 않음
* **Cause:** ROS2 Jazzy TurtleBot3 bringup에서는 `/cmd_vel`이 `TwistStamped` 타입을 사용함
* **Solution:** 기존 `Twist`가 아니라 `geometry_msgs/msg/TwistStamped`를 사용하여 속도 명령을 publish하도록 수정

확인 명령어:

```bash
ros2 topic info /cmd_vel
```

<br>

### 2. OCR에서 숫자나 이상한 문자가 인식되는 문제

* **Issue:** `9`, `1` 또는 의미 없는 문자가 OCR 결과로 출력됨
* **Cause:** 글자 크기, 조명, 초점, 배경 대비 문제로 OCR 신뢰도가 낮아짐
* **Solution:**
  * 글자 크기를 크게 출력
  * 흰 배경 + 검은 글자처럼 대비를 크게 설정
  * 카메라 초점 조정
  * 조명 환경 개선
  * OCR 신뢰도 기준값 조정

관련 설정:

```python
self.min_score = 0.40
```

<br>

### 3. OCR 실행 시 영상이 느려지는 문제

* **Issue:** OCR 처리 중 프레임이 끊기거나 반응이 느려짐
* **Cause:** EasyOCR은 연산량이 커서 매 프레임 수행하면 속도가 느려질 수 있음
* **Solution:** OCR을 매 프레임이 아니라 일정 프레임 간격으로 수행

관련 설정:

```python
self.ocr_interval_frames = 10
```
<br>

### 4. PID 제어 미적용으로 인한 미세 움직임 문제

* **Issue:** YOLO가 키보드 객체를 정상적으로 인식했지만, TurtleBot3가 목표 위치에 도달한 뒤에도 미세하게 계속 움직이는 문제가 발생했습니다.
* **Cause:** 초기 제어 방식에서는 객체가 화면 중심에 있는지, Bounding Box 면적이 목표 거리와 가까운지만 단순 조건문으로 판단했습니다. 이 방식은 카메라 영상의 작은 흔들림, YOLO Bounding Box 좌표 변화, 조명 변화에 따른 인식 오차에도 바로 속도 명령이 바뀌기 때문에 TurtleBot3가 정지하지 못하고 계속 조금씩 움직이는 현상이 발생했습니다.
* **Solution:** 단순 조건 기반 제어 대신 PID 제어를 추가하여 화면 중심 오차와 Bounding Box 면적 오차를 연속적으로 계산하도록 개선했습니다.
  * 화면 중심과 키보드 중심의 차이인 `error_x`를 기준으로 회전 PID 제어 적용
  * 목표 Bounding Box 면적과 현재 객체 면적의 차이인 `area_error`를 기준으로 거리 PID 제어 적용
  * 중심 허용 오차(`center_tolerance`)와 거리 허용 오차(`area_tolerance`) 안에 들어오면 PID 값을 reset하고 정지
  * 최대 선속도와 각속도를 제한하여 급격한 움직임 방지

관련 설정:

```python
self.center_tolerance = 50
self.area_tolerance = 5000

self.max_linear_speed = 0.06
self.max_reverse_speed = -0.04
self.max_angular_speed = 0.25

self.angular_pid = PID(
    kp=0.0014,
    ki=0.0,
    kd=0.00025,
    output_limit=self.max_angular_speed,
    integral_limit=3000.0
)

self.linear_pid = PID(
    kp=0.0000020,
    ki=0.0,
    kd=0.0000004,
    output_limit=self.max_linear_speed,
    integral_limit=200000.0
)
```
<br>

## ✅ 10. Result (결과)

* TurtleBot3 Raspberry Pi 5에 연결된 USB 카메라 영상을 Flask 서버로 실시간 스트리밍했습니다.
* Remote PC에서 TurtleBot3 카메라 영상을 받아 YOLOv11 객체 인식을 수행했습니다.
* YOLOv11을 이용해 키보드 객체를 인식하고 TurtleBot3가 객체를 따라가도록 구현했습니다.
* PID 제어를 적용하여 단순 On/Off 제어보다 부드러운 방향 및 거리 제어를 구현했습니다.
* EasyOCR을 이용해 한글 명령어를 인식하고 TurtleBot3를 전진, 후진, 좌회전, 우회전, 정지시킬 수 있었습니다.
* ROS2 Jazzy TurtleBot3 환경에 맞게 `/cmd_vel` 메시지 타입을 `TwistStamped`로 적용했습니다.
* 객체 미탐지, 명령어 미검출, OCR timeout 상황에서 TurtleBot3가 자동 정지하도록 안전 로직을 추가했습니다.
* PID 제어를 적용한 뒤 객체가 화면 중앙과 목표 거리 근처에 위치했을 때 TurtleBot3가 불필요하게 떨리거나 계속 움직이는 문제가 줄어들었고, 키보드 객체를 더 부드럽고 안정적으로 추적할 수 있었습니다. 

<br>

## 🚀 11. Future Improvements (향후 개선점)

* OCR 인식률 향상을 위한 ROI 설정
* 이미지 이진화, Thresholding 등 OCR 전처리 강화
* YOLO 추적 대상을 키보드 외 다른 객체로 확장
* 객체 선택 UI 추가
* 음성 명령 인식 기능 추가
* SLAM 및 Navigation2와 연동하여 특정 객체 위치까지 자율 이동
* 장애물 회피 기능 추가
* 웹 대시보드에서 실시간 영상, 객체 인식 결과, OCR 결과, 로봇 상태를 함께 표시
* TurtleBot3 bringup, 카메라 서버, YOLO 제어, OCR 제어를 launch file로 통합 실행

<br>

## 📚 References

* ROBOTIS TurtleBot3 Official Repository  
  https://github.com/ROBOTIS-GIT/turtlebot3

* ROBOTIS TurtleBot3 e-Manual - Bringup  
  https://emanual.robotis.com/docs/en/platform/turtlebot3/bringup/

* ROS Index - turtlebot3_bringup  
  https://index.ros.org/p/turtlebot3_bringup/

* Ultralytics YOLO  
  https://github.com/ultralytics/ultralytics

* EasyOCR  
  https://github.com/JaidedAI/EasyOCR
