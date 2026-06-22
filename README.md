# Smart Sentinel: Distributed Face Recognition Smart Lock System

Smart Sentinel is a distributed IoT home security system. It shifts heavy AI face inference (MTCNN + FaceNet) to a local Laptop/PC, while utilizing a lightweight Raspberry Pi node as a video capture source and servo lock controller. It provides a professional, real-time web-monitoring dashboard with secure JWT authentication, instant intruder alerts, and automated email notifications with attachments.

---

## 🏗️ System Architecture

```
                      +----------------------------+
                      |     Raspberry Pi Node      |
                      |  (USB/CSI Camera + Servo)  |
                      +-------------+--------------+
                                    |
                            Streams Video (MJPEG)
                            Sends Commands (HTTP)
                                    |
                                    v
                      +-------------+--------------+
                      |         Laptop/PC          |
                      |   - FastAPI Backend API    |
                      |   - MTCNN & FaceNet AI     |
                      |   - SQLite Database        |
                      +-------------+--------------+
                                    |
                            WebSockets / REST
                                    |
                                    v
                      +-------------+--------------+
                      |    Web Dashboard Client    |
                      |   - React + Vite + Tailwind|
                      +----------------------------+
```

1. **Raspberry Pi**: Captures frames, exposes a video streaming endpoint at `/video_feed`, checks handshakes at `/handshake`, and controls the SG90 Servo motor via GPIO Pin 18 on HTTP signals `/unlock` or `/lock`.
2. **Laptop/PC (Server)**: Connects to the Pi's MJPEG feed, performs real-time face detection (MTCNN) and recognition (FaceNet), runs a FastAPI REST server, sends email alerts (SMTP), writes SQLite logs, and broadcasts updates over WebSockets.
3. **Web Dashboard**: Responsive dark-themed UI displaying the live camera feed, system health, lock switches, and event log list.

---

## 🔌 Hardware Wiring Diagram (Raspberry Pi & SG90 Servo)

> [!IMPORTANT]
> **Power Safety**: Do NOT power the SG90 servo motor directly from the Raspberry Pi's 5V pin. Actuators draw significant surge currents that cause Pi voltage brownouts and reboots. Use an external 5V power supply and join the grounds.

```
       Raspberry Pi BCM Pinout                 External 5V Power Supply
      +-----------------------+               +------------------------+
      |                       |               |                        |
      |  Pin 12 (GPIO 18)     |---------------+  [ Positive 5V Output ]  |
      |  [PWM Lock Control]   |               |                        |
      |                       |               |  [ Ground (GND) ]      |
      |  Pin 6 (GND)          |---+           +-----------+------------+
      +-----------------------+   |                       |
                                  |                       |
                                  +-----------+-----------+
                                              |
                                              v (Common Ground Line)
                                     +--------+--------+
                                     |  SG90 Servo     |
                                     |  - Brown (GND)  |
                                     |  - Red (5V)     |  <-- Connects to +5V external
                                     |  - Orange (PWM) |  <-- Connects to GPIO 18 (Pin 12)
                                     +-----------------+
```

* **PWM Signal (Orange)**: Connect to **GPIO 18** (Physical Pin 12) on the Raspberry Pi.
* **Positive Power (Red)**: Connect to the **positive terminal (+5V)** of the external power supply.
* **GND (Brown/Black)**: Connect to the **negative terminal (GND)** of the external power supply **AND** to a **GND pin (e.g., Pin 6)** on the Raspberry Pi (Common Ground).

---

## 🚀 Installation & Running Guide

### 1. Raspberry Pi Node Setup

1. Copy the `pi_node` directory to your Raspberry Pi.
2. Install system dependencies:
   ```bash
   sudo apt-get update
   sudo apt-get install python3-opencv python3-pip -y
   ```
3. Install Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
4. Verify config settings in `pi_node/config.py` (pins, port, camera type).
5. Start the Pi server:
   ```bash
   python3 pi_node.py
   ```

---

### 2. Laptop/PC (Server & Dashboard) Setup

1. Install Python (3.8 - 3.11 recommended) and Git.
2. Clone the repository and enter the directory:
   ```bash
   git clone https://github.com/thusharbk0308/iot_el_2.git
   cd iot_el_2
   ```
3. Initialize a virtual environment and install packages:
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows: venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```
4. Configure environment settings in `backend/app/config.py`:
   - Set `PI_IP` to the IP address of your Raspberry Pi.
   - Configure the `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASSWORD` variables to receive intruder email alerts.
5. Launch the FastAPI server:
   ```bash
   cd backend/app
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
6. Access the dashboard in your web browser at:
   `http://localhost:8000`

> [!NOTE]
> **Default Admin Account**: On first launch, the database automatically populates a default administrator account.
> - **Username**: `admin`
> - **Password**: `admin`
> - Please register a custom account and update credentials for safety.

---

## 💻 Web Dashboard Features

* **Live Video Feeds**: Displays annotated bounding boxes, matched names, and similarity percentages.
* **System Health Monitor**: Instant connection states for Pi Nodes, Web Cameras, AI Models, and Databases.
* **Face Enrollment Wizard**: Submit a username in the "Authorized Users" page, look at the camera, and the system automatically captures 15 snapshots at varied angles, rebuilds the embeddings file, and registers the person.
* **Intruder Snapshot Grid**: View deny instances and inspect high-resolution frames of unknown visitors.
* **Filterable Audit Tables**: Search and sort logs by date, time, status, or confidence scores.
