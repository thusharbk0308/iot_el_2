import os
import torch
import numpy as np
import cv2
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1
from sqlalchemy.orm import Session
import config
import crud

class FaceEngine:
    def __init__(self):
        # Determine device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[FACE ENGINE] Using device: {self.device}")
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
        os.makedirs(config.LOGS_DIR, exist_ok=True)
        os.makedirs(config.MODELS_DIR, exist_ok=True)
        
        # Initialize MTCNN for detection (keep_all=True to handle multiple faces)
        self.mtcnn = MTCNN(
            keep_all=True, 
            device=self.device,
            pretrained=True
        )
        
        # Initialize InceptionResnetV1 for embedding generation (FaceNet)
        self.resnet = InceptionResnetV1(pretrained='vggface2', device=self.device).eval()
        
        # Load authorized embeddings from disk
        self.embeddings_db = {}
        self.load_embeddings()
        
    def load_embeddings(self):
        """
        Loads embeddings from the authorized_faces.pt file.
        """
        if os.path.exists(config.DB_PATH):
            try:
                # Load with map_location matching the current device
                self.embeddings_db = torch.load(config.DB_PATH, map_location=self.device)
                print(f"[FACE ENGINE] Loaded authorized embeddings for users: {list(self.embeddings_db.keys())}")
            except Exception as e:
                print(f"[FACE ENGINE] [ERROR] Failed to load embeddings file: {e}")
                self.embeddings_db = {}
        else:
            print(f"[FACE ENGINE] Embeddings database file not found at {config.DB_PATH}. Initializing empty database.")
            self.embeddings_db = {}

    def save_embeddings(self):
        """
        Saves the current embeddings to the authorized_faces.pt file.
        """
        try:
            torch.save(self.embeddings_db, config.DB_PATH)
            print(f"[FACE ENGINE] Saved embeddings to {config.DB_PATH}")
        except Exception as e:
            print(f"[FACE ENGINE] [ERROR] Failed to save embeddings to file: {e}")

    def get_embedding(self, face_img: np.ndarray) -> torch.Tensor:
        """
        Takes a pre-aligned cropped face image (numpy RGB format) and returns its embedding vector.
        """
        # Normalization standard for FaceNet
        face_tensor = torch.tensor(face_img, dtype=torch.float32, device=self.device)
        face_tensor = face_tensor.permute(2, 0, 1) # HWC to CHW
        face_tensor = (face_tensor - 127.5) / 128.0 
        face_tensor = face_tensor.unsqueeze(0)
        
        with torch.no_grad():
            embedding = self.resnet(face_tensor)
        return embedding[0]

    def recognize_face(self, face_embedding: torch.Tensor):
        """
        Compares an input face embedding against all enrolled users.
        Returns (name, confidence_score) where confidence_score is a cosine similarity.
        """
        if not self.embeddings_db:
            return "Unknown", 0.0
            
        best_name = "Unknown"
        best_score = 0.0
        
        # Normalize input embedding
        face_norm = face_embedding / torch.norm(face_embedding)
        
        # Iterate over each user's enrolled embeddings
        for name, user_embeddings in self.embeddings_db.items():
            if user_embeddings is None or len(user_embeddings) == 0:
                continue
                
            # Convert user embeddings list to tensor if needed
            if isinstance(user_embeddings, list):
                user_embeddings = torch.stack(user_embeddings)
            
            # user_embeddings shape: [N, 512]
            user_norms = user_embeddings / torch.norm(user_embeddings, dim=1, keepdim=True)
            
            # Compute cosine similarities
            similarities = torch.mm(face_norm.unsqueeze(0), user_norms.t()).squeeze(0)
            
            # Calculate individual max similarity
            max_sim = torch.max(similarities).item()
            
            # Calculate centroid similarity
            centroid = torch.mean(user_norms, dim=0)
            centroid_norm = centroid / torch.norm(centroid)
            centroid_sim = torch.dot(face_norm, centroid_norm).item()
            
            # Decide match based on configurations
            if centroid_sim >= config.CENTROID_THRESHOLD:
                if centroid_sim > best_score:
                    best_score = centroid_sim
                    best_name = name
            elif max_sim >= config.INDIVIDUAL_THRESHOLD:
                if max_sim > best_score:
                    best_score = max_sim
                    best_name = name
                    
        return best_name, best_score

    def detect_and_recognize(self, frame: np.ndarray):
        """
        Processes a raw frame: detects faces, draws bounding boxes, and performs recognition.
        Returns: (annotated_frame, list_of_detected_faces_info)
        face_info: {"name": str, "confidence": float, "box": [x1, y1, x2, y2]}
        """
        h, w, _ = frame.shape
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        boxes, probs = self.mtcnn.detect(rgb_frame)
        
        detected_faces = []
        annotated_frame = frame.copy()
        
        if boxes is not None:
            for box, prob in zip(boxes, probs):
                if prob is None or prob < 0.8: # Skip low confidence face detections
                    continue
                    
                x1, y1, x2, y2 = [int(coord) for coord in box]
                
                # Constrain coordinates to image bounds
                x1 = max(0, min(x1, w - 1))
                y1 = max(0, min(y1, h - 1))
                x2 = max(0, min(x2, w - 1))
                y2 = max(0, min(y2, h - 1))
                
                # Crop and resize face
                face_crop = rgb_frame[y1:y2, x1:x2]
                if face_crop.size == 0 or face_crop.shape[0] < 10 or face_crop.shape[1] < 10:
                    continue
                    
                face_crop_resized = cv2.resize(face_crop, (160, 160))
                
                # Get embedding and recognize
                embedding = self.get_embedding(face_crop_resized)
                name, confidence = self.recognize_face(embedding)
                
                detected_faces.append({
                    "name": name,
                    "confidence": confidence,
                    "box": [x1, y1, x2, y2]
                })
                
                # Draw bounding box and label on annotated frame
                color = (46, 204, 113) if name != "Unknown" else (231, 76, 60) # Green for authorized, Red for Unknown (BGR format)
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                
                label = f"{name} ({confidence:.2f})" if name != "Unknown" else "Unknown Face"
                cv2.putText(annotated_frame, label, (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                            
        return annotated_frame, detected_faces

    def rebuild_embeddings(self, dataset_dir: str, db: Session):
        """
        Walks through the dataset directory, extracts embeddings for all users,
        saves the .pt binary database, and syncs status to SQLite db.
        """
        print("[FACE ENGINE] Starting rebuild of embeddings database...")
        new_embeddings = {}
        
        if not os.path.exists(dataset_dir):
            print(f"[FACE ENGINE] Dataset directory {dataset_dir} does not exist. Nothing to compile.")
            return False
            
        # Walk directories
        for user_name in os.listdir(dataset_dir):
            user_path = os.path.join(dataset_dir, user_name)
            if not os.path.isdir(user_path):
                continue
                
            print(f"[FACE ENGINE] Processing user: {user_name}")
            user_embeddings = []
            
            for img_name in os.listdir(user_path):
                # Only load image formats
                if not img_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                img_path = os.path.join(user_path, img_name)
                # Read image
                frame = cv2.imread(img_path)
                if frame is None:
                    continue
                    
                h, w, _ = frame.shape
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Detect the main face in enrollment image
                boxes, probs = self.mtcnn.detect(rgb_frame)
                
                if boxes is not None and len(boxes) > 0:
                    # Take the highest probability detection
                    best_idx = np.argmax(probs)
                    if probs[best_idx] < 0.8:
                        continue
                        
                    box = boxes[best_idx]
                    x1, y1, x2, y2 = [int(coord) for coord in box]
                    
                    x1 = max(0, min(x1, w - 1))
                    y1 = max(0, min(y1, h - 1))
                    x2 = max(0, min(x2, w - 1))
                    y2 = max(0, min(y2, h - 1))
                    
                    face_crop = rgb_frame[y1:y2, x1:x2]
                    if face_crop.size == 0 or face_crop.shape[0] < 10 or face_crop.shape[1] < 10:
                        continue
                        
                    face_crop_resized = cv2.resize(face_crop, (160, 160))
                    embedding = self.get_embedding(face_crop_resized)
                    user_embeddings.append(embedding)
            
            if len(user_embeddings) > 0:
                # Stack list of embeddings into a single 2D tensor
                new_embeddings[user_name] = torch.stack(user_embeddings)
                print(f"[FACE ENGINE] Successfully enrolled {len(user_embeddings)} images for {user_name}")
                # Sync into database using CRUD helper
                crud.create_authorized_user(db, name=user_name, image_count=len(user_embeddings))
            else:
                print(f"[FACE ENGINE] [WARNING] No valid faces found for user {user_name}. Skipping.")
                
        # Save new embeddings
        self.embeddings_db = new_embeddings
        self.save_embeddings()
        print("[FACE ENGINE] Embeddings database rebuild complete.")
        return True

# Initialize single global instance
engine = FaceEngine()
