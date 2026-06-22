import os

# --- Distributed Network Config ---
PI_IP = "192.168.1.15"         # Local IP of the Raspberry Pi
PI_PORT = 5000                 # Port of the Pi Flask server

# --- Database Config ---
DATABASE_URL = "sqlite:///./database.db"

# --- Security & JWT Configurations ---
# Change this secret key in production!
SECRET_KEY = "b2c93847e30d4a5c891f1a5b6c7d8e9f"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 Hours

# --- SMTP Email Configurations ---
# Configure these variables to receive intruder email alerts.
# Example for Gmail: SMTP_SERVER = "smtp.gmail.com", SMTP_PORT = 587
# Use a Gmail "App Password" rather than your real password.
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "your_email@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your_app_password")
ALERT_RECEIVER_EMAIL = os.getenv("ALERT_RECEIVER_EMAIL", "receiver_email@gmail.com")

# --- Access Control & Timings ---
EMAIL_COOLDOWN = 30.0          # Seconds to wait between sending intruder alert emails
LOCK_COOLDOWN = 5.0            # Seconds to wait before sending repeat unlock commands to the Pi

# --- Recognition Model Thresholds ---
# Cosine Similarity thresholds (0.0 to 1.0)
CENTROID_THRESHOLD = 0.65      # Stricter: Match against average representation
INDIVIDUAL_THRESHOLD = 0.60    # Fallback: Match against individual dataset frames

# --- Caching & Performance ---
CACHE_LIFETIME = 1.0           # Seconds to cache tracked face classifications (reduces CPU load)

# --- File System Paths ---
DB_PATH = "../embeddings/authorized_faces.pt"
LOGS_DIR = "static/snapshots"
MODELS_DIR = "models"
