import requests
import logging
import config

logger = logging.getLogger(__name__)

def send_pi_unlock() -> bool:
    """
    Sends a request to the Raspberry Pi Node to unlock the door.
    Returns True if successful, False otherwise.
    """
    try:
        url = f"http://{config.PI_IP}:{config.PI_PORT}/unlock"
        response = requests.get(url, timeout=3)
        if response.status_code == 200 and response.text.strip() == "UNLOCKED":
            logger.info("Successfully sent unlock command to Pi Node.")
            return True
        else:
            logger.error(f"Failed to unlock: Pi Node returned {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to communicate with Pi Node at {config.PI_IP}:{config.PI_PORT}: {e}")
        return False

def send_pi_lock() -> bool:
    """
    Sends a request to the Raspberry Pi Node to force lock the door.
    Returns True if successful, False otherwise.
    """
    try:
        url = f"http://{config.PI_IP}:{config.PI_PORT}/lock"
        response = requests.get(url, timeout=3)
        if response.status_code == 200 and response.text.strip() == "LOCKED":
            logger.info("Successfully sent force lock command to Pi Node.")
            return True
        else:
            logger.error(f"Failed to lock: Pi Node returned {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to communicate with Pi Node: {e}")
        return False

def check_pi_health() -> bool:
    """
    Checks if the Pi node is online and responding.
    """
    try:
        url = f"http://{config.PI_IP}:{config.PI_PORT}/handshake"
        response = requests.get(url, timeout=2)
        return response.status_code == 200 and response.text.strip() == "ACK"
    except Exception:
        return False
