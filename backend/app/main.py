import os
import cv2
import time
import logging
import numpy as np
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

import config
import crud
import database
import schemas
import auth
import lock_controller
import inference_worker
from websocket_manager import manager as ws_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Security System API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure snapshot directory exists
os.makedirs(config.LOGS_DIR, exist_ok=True)
app.mount("/static/snapshots", StaticFiles(directory=config.LOGS_DIR), name="snapshots")

# --- LIFECYCLE EVENTS ---

@app.on_event("startup")
def on_startup():
    # Initialize SQLite database and tables
    database.Base.metadata.create_all(bind=database.engine)
    
    db = database.SessionLocal()
    try:
        # Create default admin user if database is empty
        admin_user = db.query(database.User).first()
        if not admin_user:
            logger.info("No users found in database. Creating default admin account...")
            default_admin = schemas.UserCreate(
                username="admin",
                email="admin@smartlock.local",
                password="admin",
                role="admin"
            )
            crud.create_user(db, default_admin)
            logger.info("SUCCESS: Default admin created! (User: admin, Password: admin)")

        # Sync existing embeddings database with the SQLite authorized_users table
        from face_engine import engine as face_engine
        if face_engine.embeddings_db:
            for name, user_embeddings in face_engine.embeddings_db.items():
                count = len(user_embeddings) if isinstance(user_embeddings, list) else user_embeddings.shape[0]
                crud.create_authorized_user(db, name=name, image_count=count)
            logger.info("Synced SQLite database with existing face embeddings binary.")
    except Exception as e:
        logger.error(f"Error during startup DB initialization: {e}")
    finally:
        db.close()
        
    # Start the background inference and health threads
    inference_worker.start_worker()

@app.on_event("shutdown")
def on_shutdown():
    # Stop background threads
    inference_worker.stop_worker()

# --- CAMERA STREAM ENDPOINT ---

def gen_annotated_frames():
    """
    Generator yielding the latest processed frames from the inference thread.
    """
    while True:
        frame = inference_worker.get_latest_frame()
        if frame is None:
            # Render a standby screen if Pi Node stream is offline
            standby = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(standby, "Awaiting Camera Feed...", (160, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2)
            ret, buffer = cv2.imencode('.jpg', standby)
            frame_bytes = buffer.tobytes()
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.04) # ~25 frames per second limit

@app.get("/api/camera/stream")
def get_camera_stream():
    """
    Returns a live, multipart MJPEG video stream with overlayed face boundaries.
    """
    return StreamingResponse(
        gen_annotated_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# --- WEBSOCKET EVENT HUB ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time system events gateway.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive heartbeat loop
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket client connection error: {e}")
        ws_manager.disconnect(websocket)

# --- AUTH API ROUTES ---

@app.post("/api/auth/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    db_email = crud.get_user_by_email(db, email=user.email)
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    return crud.create_user(db, user)

@app.post("/api/auth/login", response_model=schemas.Token)
def login_user(credentials: schemas.UserLogin, db: Session = Depends(database.get_db)):
    user = crud.get_user_by_username(db, username=credentials.username)
    if not user or not auth.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = auth.create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role
    }

# --- SYSTEM HEALTH ENDPOINT ---

@app.get("/api/status", response_model=schemas.SystemStatusResponse)
def get_system_status(db: Session = Depends(database.get_db)):
    pi_health = inference_worker.get_pi_status()
    db_health = "Online"
    try:
        db.execute("SELECT 1")
    except Exception:
        db_health = "Offline"
        
    return {
        "pi": pi_health,
        "camera": pi_health,
        "ai_server": "Online",
        "lock": "Online" if pi_health == "Online" else "Offline",
        "database": db_health
    }

# --- LOCK ACTION ROUTE ---

@app.post("/api/lock/control")
def control_door_lock(
    request: schemas.LockControlRequest, 
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_active_admin)
):
    action = request.action.lower()
    if action == "unlock":
        success = lock_controller.send_pi_unlock()
        if success:
            crud.create_notification(db, message=f"Door remotely UNLOCKED by Admin '{current_user.username}'.", type="Lock")
            ws_manager.active_connections # Trigger update
            # Broadcast Lock status change
            import asyncio
            asyncio.run(ws_manager.broadcast({"type": "LOCK", "status": "UNLOCKED"}))
            return {"status": "success", "message": "Unlock command delivered to Pi."}
        else:
            raise HTTPException(status_code=502, detail="Failed to communicate unlock request to Pi Node.")
            
    elif action == "lock":
        success = lock_controller.send_pi_lock()
        if success:
            crud.create_notification(db, message=f"Door remotely LOCKED by Admin '{current_user.username}'.", type="Lock")
            import asyncio
            asyncio.run(ws_manager.broadcast({"type": "LOCK", "status": "LOCKED"}))
            return {"status": "success", "message": "Lock command delivered to Pi."}
        else:
            raise HTTPException(status_code=520, detail="Failed to communicate lock request to Pi Node.")
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'unlock' or 'lock'.")

# --- ACCESS LOGS ROUTE ---

@app.get("/api/logs", response_model=List[schemas.AccessLogResponse])
def get_access_logs(
    status: Optional[str] = Query(None, description="Filter logs by 'Granted' or 'Denied'"),
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user)
):
    return crud.get_access_logs(db, limit=limit, status=status)

# --- INTRUDER ALERTS ROUTE ---

@app.get("/api/alerts", response_model=List[schemas.IntruderAlertResponse])
def get_intruder_alerts(
    limit: int = 100,
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user)
):
    return crud.get_intruder_alerts(db, limit=limit)

@app.delete("/api/alerts/{alert_id}")
def delete_intruder_alert(
    alert_id: int, 
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_active_admin)
):
    # Retrieve path to delete physical snapshot file
    alert = db.query(database.IntruderAlert).filter(database.IntruderAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert record not found")
        
    # Delete file
    snapshot_rel_path = alert.snapshot_path.lstrip("/") # Remove leading slash
    # Map back to local config LOGS_DIR path
    # e.g., static/snapshots/unknown_xxxx.jpg
    filename = os.path.basename(snapshot_rel_path)
    snapshot_abs_path = os.path.join(config.LOGS_DIR, filename)
    
    if os.path.exists(snapshot_abs_path):
        try:
            os.remove(snapshot_abs_path)
            logger.info(f"Deleted physical snapshot file: {snapshot_abs_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {snapshot_abs_path}: {e}")
            
    # Delete DB record
    crud.delete_intruder_alert(db, alert_id)
    return {"status": "success", "message": "Alert snapshot and record deleted."}

# --- SYSTEM NOTIFICATIONS ROUTE ---

@app.get("/api/notifications", response_model=List[schemas.NotificationResponse])
def get_system_notifications(
    limit: int = 50,
    unread_only: bool = False,
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user)
):
    return crud.get_notifications(db, limit=limit, unread_only=unread_only)

@app.post("/api/notifications/read")
def read_system_notifications(
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user)
):
    count = crud.mark_notifications_as_read(db)
    return {"status": "success", "marked_read_count": count}

# --- ENROLLED USERS MANAGEMENT ---

@app.get("/api/users", response_model=List[schemas.AuthorizedUserResponse])
def get_authorized_users(
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user)
):
    return crud.get_authorized_users(db)

@app.post("/api/users/enroll")
def enroll_new_face(
    name: str = Query(..., description="Name of the person being enrolled"),
    current_user: database.User = Depends(auth.get_current_active_admin)
):
    # Validate name format
    clean_name = "".join(x for x in name if x.isalnum() or x in "._-").strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Invalid name format. Only alphanumeric characters allowed.")
        
    success = inference_worker.trigger_enrollment(clean_name)
    if not success:
        raise HTTPException(status_code=409, detail="An enrollment session is currently in progress. Please wait.")
        
    return {"status": "success", "message": f"Face enrollment initialized for '{clean_name}'. Stand in front of the camera."}

@app.delete("/api/users/{name}")
def delete_authorized_user(
    name: str, 
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_active_admin)
):
    # Remove from dataset folder
    dataset_path = os.path.join("../dataset", name)
    if os.path.exists(dataset_path):
        try:
            shutil.rmtree(dataset_path)
            logger.info(f"Deleted dataset folder for user: {name}")
        except Exception as e:
            logger.error(f"Failed to delete folder {dataset_path}: {e}")
            
    # Delete database registration
    success = crud.remove_authorized_user(db, name)
    if not success:
        raise HTTPException(status_code=404, detail="Authorized user not found in database")
        
    # Rebuild embeddings list asynchronously to reflect changes
    from face_engine import engine as face_engine
    import threading
    threading.Thread(target=inference_worker.rebuild_and_notify, args=(name,), daemon=True).start()
    
    return {"status": "success", "message": f"User '{name}' removed. Triggered embeddings database rebuild."}

# --- STATIC CLIENT APPLICATION ROUTE ---

# Fallback catchall to serve the React application
# This is set up at the very bottom so it doesn't mask API routes
frontend_dist_path = "../frontend/dist"
if os.path.exists(frontend_dist_path):
    # Mount assets folder (Vite outputs index.css and index.js here)
    assets_path = os.path.join(frontend_dist_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
        logger.info(f"Mounted frontend assets directory: {assets_path}")
        
    @app.get("/{catchall:path}")
    async def serve_react_app(catchall: str):
        # Exclude API endpoints from routing
        if catchall.startswith("api/") or catchall.startswith("ws"):
            raise HTTPException(status_code=404, detail="API resource not found")
        # Return React app index.html
        index_file = os.path.join(frontend_dist_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Static index file not found")

