import os
import cv2
import time
import datetime
import logging
import threading
import shutil
import numpy as np
import requests
from sqlalchemy.orm import Session

import config
import crud
import database
from face_engine import engine as face_engine
import email_service
import lock_controller
from websocket_manager import manager as ws_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global states
latest_annotated_frame = None
frame_lock = threading.Lock()
pi_status = "Offline"
status_lock = threading.Lock()
is_running = False
worker_thread = None
health_thread = None

# Track cooldowns
last_email_sent_time = 0.0
last_unlock_time = 0.0

# Enrollment states
enrollment_target = None
enrollment_pics_captured = 0
enrollment_lock = threading.Lock()

def get_latest_frame():
    """
    Retrieves the latest annotated video frame for streaming.
    """
    global latest_annotated_frame
    with frame_lock:
        if latest_annotated_frame is None:
            return None
        return latest_annotated_frame.copy()

def get_pi_status():
    """
    Retrieves the current Pi Node connection health.
    """
    global pi_status
    with status_lock:
        return pi_status

def set_pi_status(new_status: str):
    """
    Safely updates and broadcasts the Pi status if it changes.
    """
    global pi_status
    old_status = None
    with status_lock:
        old_status = pi_status
        pi_status = new_status
        
    if old_status != new_status:
        logger.info(f"Raspberry Pi health status changed: {old_status} -> {new_status}")
        # Broadcast status change to clients
        async_broadcast({
            "type": "HEALTH",
            "pi": new_status,
            "camera": new_status,
            "ai_server": "Online",
            "database": "Online",
            "lock": "Online" if new_status == "Online" else "Offline"
        })
        
        # Save system notification
        db = database.SessionLocal()
        try:
            crud.create_notification(
                db, 
                message=f"Raspberry Pi security node is now {new_status.lower()}.", 
                type="System"
            )
        finally:
            db.close()

def async_broadcast(message: dict):
    """
    Helper to run websocket broadcasts in the event loop asynchronously.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(message), loop)
        else:
            loop.run_until_complete(ws_manager.broadcast(message))
    except Exception as e:
        logger.debug(f"Async broadcast bypass failed: {e}")

def process_face_events(faces, frame):
    """
    Processes recognized faces: triggers locks or email alerts based on database config.
    """
    global last_email_sent_time, last_unlock_time
    db = database.SessionLocal()
    
    try:
        now = time.time()
        for face in faces:
            name = face["name"]
            confidence = face["confidence"]
            
            if name != "Unknown":
                # Known Authorized User: Grant access & unlock lock
                if now - last_unlock_time > config.LOCK_COOLDOWN:
                    last_unlock_time = now
                    logger.info(f"Authorized user '{name}' recognized. Triggering unlock.")
                    
                    # Unlock Pi
                    success = lock_controller.send_pi_unlock()
                    signal_status = "Yes" if success else "Failed"
                    
                    # Save DB log
                    crud.create_access_log(
                        db, 
                        name=name, 
                        status="Granted", 
                        confidence=confidence, 
                        signal_sent=signal_status
                    )
                    
                    # Create notification
                    crud.create_notification(
                        db,
                        message=f"Access granted to {name} ({confidence:.2f} confidence).",
                        type="Lock"
                    )
                    
                    # Broadcast to WebSockets
                    async_broadcast({
                        "type": "ACCESS",
                        "name": name,
                        "status": "Granted",
                        "confidence": confidence,
                        "signal_sent": signal_status,
                        "timestamp": datetime.datetime.now().isoformat()
                    })
                    
                    # Broadcast Lock change
                    async_broadcast({
                        "type": "LOCK",
                        "status": "UNLOCKED"
                    })
            else:
                # Unknown Person: Deny access & trigger intruder email
                logger.warning("Unknown face detected! Access denied.")
                
                # Save DB log
                crud.create_access_log(
                    db, 
                    name="Unknown", 
                    status="Denied", 
                    confidence=0.0, 
                    signal_sent="No"
                )
                
                # Check email alert cooldown
                email_sent = False
                snapshot_file = None
                
                if now - last_email_sent_time > config.EMAIL_COOLDOWN:
                    last_email_sent_time = now
                    
                    # Save snapshot image
                    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    snapshot_filename = f"unknown_{timestamp_str}.jpg"
                    
                    # Verify snapshot directory exists
                    os.makedirs(config.LOGS_DIR, exist_ok=True)
                    snapshot_file = os.path.join(config.LOGS_DIR, snapshot_filename)
                    
                    cv2.imwrite(snapshot_file, frame)
                    logger.info(f"Saved intruder snapshot: {snapshot_file}")
                    
                    # Send Email Asynchronously
                    pretty_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    email_service.send_intruder_email(pretty_time, snapshot_file)
                    email_sent = True
                    
                    # Save Intruder Alert to DB
                    # Database path is stored relative to static folder for UI display
                    ui_snapshot_path = f"/static/snapshots/{snapshot_filename}"
                    crud.create_intruder_alert(db, snapshot_path=ui_snapshot_path, email_sent=True)
                    
                    # Create notifications
                    crud.create_notification(
                        db,
                        message="Intruder detected! Snapshot captured and security email alert dispatched.",
                        type="Alert"
                    )
                    
                    # Broadcast Alert to WebSockets
                    async_broadcast({
                        "type": "INTRUDER",
                        "snapshot_path": ui_snapshot_path,
                        "timestamp": pretty_time
                    })
                
                # Broadcast Access Denied
                async_broadcast({
                    "type": "ACCESS",
                    "name": "Unknown",
                    "status": "Denied",
                    "confidence": 0.0,
                    "signal_sent": "No",
                    "timestamp": datetime.datetime.now().isoformat()
                })
                
    except Exception as e:
        logger.error(f"Error in face events handler: {e}")
    finally:
        db.close()

def rebuild_and_notify(target: str):
    """
    Background worker thread to rebuild FaceNet embeddings and notify clients.
    """
    logger.info(f"Triggering background embedding rebuild for target: {target}")
    db = database.SessionLocal()
    try:
        # Rebuild embeddings from the dataset folder
        success = face_engine.rebuild_embeddings("../dataset", db)
        if success:
            async_broadcast({
                "type": "ENROLLMENT",
                "status": "Success",
                "name": target
            })
            crud.create_notification(
                db,
                message=f"Successfully enrolled new user '{target}' into database.",
                type="System"
            )
        else:
            async_broadcast({
                "type": "ENROLLMENT",
                "status": "Failed",
                "name": target
            })
    except Exception as e:
        logger.error(f"Failed to rebuild embeddings for user {target}: {e}")
        async_broadcast({
            "type": "ENROLLMENT",
            "status": "Failed",
            "name": target
        })
    finally:
        db.close()

def trigger_enrollment(name: str) -> bool:
    """
    Initializes face enrollment mode for a specific name.
    Clears any old enrollment folder if exists to start fresh.
    """
    global enrollment_target, enrollment_pics_captured
    with enrollment_lock:
        if enrollment_target is not None:
            return False  # Already enrolling someone
            
        enrollment_target = name
        enrollment_pics_captured = 0
        
        # Clear existing directory if any
        target_dir = os.path.join("../dataset", name)
        if os.path.exists(target_dir):
            try:
                shutil.rmtree(target_dir)
            except Exception as e:
                logger.error(f"Failed to clear old dataset folder for {name}: {e}")
                
        os.makedirs(target_dir, exist_ok=True)
        logger.info(f"Initiated face enrollment mode for target: {name}")
        return True

def main_inference_loop():
    """
    Main loop parsing the Pi's MJPEG stream byte-by-byte and feeding it to the Face Engine.
    """
    global latest_annotated_frame, is_running, enrollment_target, enrollment_pics_captured
    stream_url = f"http://{config.PI_IP}:{config.PI_PORT}/video_feed"
    
    logger.info(f"Connecting to Pi stream at: {stream_url}")
    
    while is_running:
        try:
            # Use requests to parse the raw MJPEG stream bytes directly
            response = requests.get(stream_url, stream=True, timeout=5)
            if response.status_code != 200:
                logger.error(f"Pi stream responded with status {response.status_code}. Retrying...")
                set_pi_status("Offline")
                time.sleep(2)
                continue
                
            set_pi_status("Online")
            bytes_data = bytes()
            
            # Start byte reading stream loop
            for chunk in response.iter_content(chunk_size=4096):
                if not is_running:
                    break
                    
                bytes_data += chunk
                
                # JPEG boundary tags
                a = bytes_data.find(b'\xff\xd8') # JPEG Start
                b = bytes_data.find(b'\xff\xd9') # JPEG End
                
                if a != -1 and b != -1 and a < b:
                    jpg_bytes = bytes_data[a:b+2]
                    bytes_data = bytes_data[b+2:]
                    
                    # Decode frame
                    frame = cv2.imdecode(np.frombuffer(jpg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        continue
                    
                    # Check if enrollment mode is active
                    target = None
                    captured = 0
                    with enrollment_lock:
                        target = enrollment_target
                        captured = enrollment_pics_captured
                        
                    if target is not None:
                        # MTCNN requires RGB
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        boxes, probs = face_engine.mtcnn.detect(rgb)
                        annotated = frame.copy()
                        
                        if boxes is not None and len(boxes) > 0 and probs[0] is not None and probs[0] > 0.8:
                            # Draw box
                            box = boxes[0]
                            x1, y1, x2, y2 = [int(coord) for coord in box]
                            # Draw bounding box and count labels (yellow)
                            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 215, 255), 2)
                            cv2.putText(annotated, f"Enrolling {target}: {captured + 1}/15", (x1, y1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 215, 255), 2)
                            
                            # Save raw frame
                            target_dir = os.path.join("../dataset", target)
                            img_path = os.path.join(target_dir, f"face_{captured}.jpg")
                            cv2.imwrite(img_path, frame)
                            logger.info(f"Captured enrollment face {captured} for {target}")
                            
                            with enrollment_lock:
                                enrollment_pics_captured += 1
                                if enrollment_pics_captured >= 15:
                                    # Complete capture
                                    enrollment_target = None
                                    enrollment_pics_captured = 0
                                    threading.Thread(target=rebuild_and_notify, args=(target,), daemon=True).start()
                                    
                            async_broadcast({
                                "type": "ENROLLMENT",
                                "status": "Progress",
                                "name": target,
                                "progress": int((captured + 1) / 15 * 100)
                            })
                            # Sleep to allow user to vary face angle
                            time.sleep(0.3)
                        else:
                            # Prompt user to face camera
                            cv2.putText(annotated, "Align face with camera to capture...", (20, 40),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                                        
                        with frame_lock:
                            latest_annotated_frame = annotated
                        continue
                    
                    # AI face detection & recognition (Standard loop)
                    annotated, faces = face_engine.detect_and_recognize(frame)
                    
                    # Update local state
                    with frame_lock:
                        latest_annotated_frame = annotated
                        
                    # Process hits (known/unknown)
                    if faces:
                        process_face_events(faces, frame)
                        
        except Exception as e:
            logger.error(f"Inference stream worker encountered error: {e}")
            set_pi_status("Offline")
            time.sleep(2)

def main_health_loop():
    """
    Periodic background check to verify Pi node communication health.
    """
    global is_running
    while is_running:
        try:
            is_alive = lock_controller.check_pi_health()
            set_pi_status("Online" if is_alive else "Offline")
        except Exception as e:
            logger.debug(f"Health check exception: {e}")
            set_pi_status("Offline")
        time.sleep(5)

def start_worker():
    """
    Launches the background AI and health check threads.
    """
    global is_running, worker_thread, health_thread
    if is_running:
        return
        
    is_running = True
    
    # Start inference loop thread
    worker_thread = threading.Thread(target=main_inference_loop, name="InferenceWorker", daemon=True)
    worker_thread.start()
    
    # Start health loop thread
    health_thread = threading.Thread(target=main_health_loop, name="HealthWorker", daemon=True)
    health_thread.start()
    
    logger.info("Background inference and health worker threads successfully started.")

def stop_worker():
    """
    Gracefully stops the worker threads.
    """
    global is_running
    is_running = False
    logger.info("Signaled background workers to stop.")
