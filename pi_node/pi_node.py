import os
import cv2
import time
import socket
import threading
from flask import Flask, Response
import config

# Initialize Flask app
app = Flask(__name__)

# Global variables for camera and servo
camera = None
servo = None
servo_lock = threading.Lock() # Thread lock for servo operations

def get_local_ip():
    """
    Retrieves the local IP address of the Raspberry Pi.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # We use a public DNS server address to find the outgoing interface IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def init_hardware():
    """
    Initializes camera and servo interfaces.
    """
    global camera, servo
    from camera_stream import CameraStream
    
    print("[PI NODE] Initializing camera...")
    camera = CameraStream(0)
    
    print(f"[PI NODE] Initializing GPIO lock servo on BCM Pin {config.PI_SERVO_PIN}...")
    try:
        from gpiozero import Servo
        servo = Servo(config.PI_SERVO_PIN)
        servo.min() # Set to locked position
        print("[PI NODE] [SUCCESS] Servo initialized successfully.")
    except ImportError:
        print("[PI NODE] [WARNING] 'gpiozero' module not found. Servo commands will run in mock mode.")
    except Exception as e:
        print(f"[PI NODE] [ERROR] Failed to initialize servo: {e}")

def gen_frames():
    """
    Generator function that captures frames and formats them for MJPEG streaming.
    """
    global camera
    while True:
        if camera is None or not camera.isOpened():
            time.sleep(0.1)
            continue
            
        success, frame = camera.read()
        if not success:
            time.sleep(0.03)
            continue
            
        # Encode the frame as a JPEG image
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        # Yield the image as part of a multipart boundary payload
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """
    Route that streams the live video feed.
    """
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/handshake')
def handshake():
    """
    Route used for laptop-to-Pi handshake connectivity test.
    """
    return Response("ACK", mimetype="text/plain")

@app.route('/unlock')
def unlock():
    """
    Route that unlocks the door (servo moves to max, waits config.UNLOCK_DURATION, returns to min).
    """
    global servo
    
    def _async_servo_cycle():
        with servo_lock:
            if servo:
                try:
                    servo.max() # Open lock
                    print("[PI NODE] Servo set to OPEN (max).")
                    time.sleep(config.UNLOCK_DURATION)
                    servo.min() # Re-lock
                    print("[PI NODE] Servo set to LOCKED (min).")
                except Exception as e:
                    print(f"[PI NODE] [ERROR] Servo movement failure: {e}")
            else:
                # Mock output
                print("[PI NODE] [MOCK] Servo set to OPEN (max).")
                time.sleep(config.UNLOCK_DURATION)
                print("[PI NODE] [MOCK] Servo set to LOCKED (min).")

    # Dispatch servo movement in a background thread to prevent blocking HTTP response
    threading.Thread(target=_async_servo_cycle, daemon=True).start()
    return Response("UNLOCKED", mimetype="text/plain")

@app.route('/lock')
def lock():
    """
    Route that explicitly locks the door.
    """
    global servo
    with servo_lock:
        if servo:
            try:
                servo.min()
                print("[PI NODE] Servo forced to LOCKED (min).")
            except Exception as e:
                print(f"[PI NODE] [ERROR] Servo force lock failure: {e}")
        else:
            print("[PI NODE] [MOCK] Servo forced to LOCKED (min).")
            
    return Response("LOCKED", mimetype="text/plain")

if __name__ == '__main__':
    # Initialize camera and servo
    init_hardware()
    
    local_ip = get_local_ip()
    print("\n" + "="*50)
    print(f"  Raspberry Pi Smart Lock Node is starting!")
    print(f"  Local IP Address: {local_ip}")
    print(f"  Live Video Feed:  http://{local_ip}:{config.PORT}/video_feed")
    print(f"  Unlock Command:   http://{local_ip}:{config.PORT}/unlock")
    print("="*50 + "\n")
    
    # Run server on all network interfaces
    app.run(host='0.0.0.0', port=config.PORT, threaded=True)
