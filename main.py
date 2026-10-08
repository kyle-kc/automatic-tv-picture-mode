import asyncio
import datetime
import sys
import time
import traceback
from enum import Enum
from pathlib import Path
from uuid import uuid4

from aiowebostv import WebOsClient
from filelock import FileLock

class PictureMode(str, Enum):
    FILMMAKER_MODE = "filmMaker"
    GAME_OPTIMIZER = "game"

SHOULD_LOG = False
LOCK_FILE_NAME = "lock"
KEY_FILE_NAME = "tv_client_key.txt"
LOG_FILE_NAME_TEMPLATE = "{start_time}.{process_id}.log"
STATE_FILE_TEMPLATE = "last_set_{picture_mode}.state"

async def set_picture_mode(picture_mode: PictureMode):
    """Set the picture mode on the LG WebOS TV using the notification workaround."""
    key_file = Path(KEY_FILE_NAME)
    
    # Read the key if the file exists, otherwise default to None for a new pairing
    client_key = key_file.read_text().strip() if key_file.exists() else None

    web_os_client = WebOsClient("192.168.0.2", client_key)
    await web_os_client.connect()

    if web_os_client.client_key and web_os_client.client_key != client_key:
        key_file.write_text(web_os_client.client_key)

    # 1. Spawn a system notification with an embedded internal Luna command using the onclose trick.
    response = await web_os_client.request(
        "system.notifications/createAlert",
        payload={
            "message": " ",
            "modal": False,
            "type": "confirm",
            "isSysReq": True,
            "buttons": [{"label": ""}],
            "onclose": {
                "uri": "luna://com.webos.settingsservice/setSystemSettings",
                "params": {
                    "category": "picture",
                    "settings": {
                        "pictureMode": picture_mode
                    }
                }
            }
        }
    )
    
    # Extract the alertId from the response.
    alert_id = ""
    if isinstance(response, dict):
        alert_id = response.get("alertId") or response.get("payload", {}).get("alertId")
        if not alert_id and "settings" in response:
            alert_id = response.get("settings", {}).get("alertId")

    # 2. Immediately close the alert using the captured ID.
    if alert_id:
        await web_os_client.request("system.notifications/closeAlert", payload={"alertId": alert_id})
    else:
        # Fallback: if ID cannot be parsed, try a generic request or just proceed.
        await web_os_client.request("system.notifications/closeAlert", payload={"alertId": "0"})
    
    # Clean up and disconnect
    await web_os_client.disconnect()

def log_message(process_id: str, start_time: float, message: str):
    """Log a message to a file specific to the current process."""
    if SHOULD_LOG:
        log_file_name = LOG_FILE_NAME_TEMPLATE.format(start_time=start_time, process_id=process_id)
        with open(log_file_name, "a") as log_file:
            log_file.write(f"{datetime.datetime.fromtimestamp(time.time())}: {message}\n")

def get_state_file_path(picture_mode: PictureMode) -> Path:
    """Get the path to the state file for a given picture mode."""
    return Path(STATE_FILE_TEMPLATE.format(picture_mode=picture_mode))

def read_last_set_time(picture_mode: PictureMode) -> float:
    """Read the last set timestamp for a specific picture mode."""
    state_file = get_state_file_path(picture_mode)
    try:
        with open(state_file, "r") as file:
            return float(file.read().strip())
    except (FileNotFoundError, ValueError):
        return 0  # Return 0 if the file doesn't exist or the content is invalid

def write_last_set_time(picture_mode: PictureMode, timestamp: float):
    """Write the current timestamp to the state file for the given picture mode."""
    state_file = get_state_file_path(picture_mode)
    with open(state_file, "w") as file:
        file.write(str(timestamp))

if __name__ == "__main__":
    start_time = time.time()
    process_id = str(uuid4())

    try:
        # Log process start
        log_message(process_id, start_time, f"Process ID: {process_id}")

        # Get the picture mode from the command-line arguments
        picture_mode = PictureMode(sys.argv[1])
        log_message(process_id, start_time, f"Picture Mode: {picture_mode}")

        # Acquire the file lock
        lock = FileLock(str(Path(LOCK_FILE_NAME)))

        with lock:
            log_message(process_id, start_time, "Lock acquired.")

            # Check the last set time for this picture mode
            last_set_time = read_last_set_time(picture_mode)
            if start_time - last_set_time <= 5:
                log_message(process_id, start_time, "Picture mode already set recently. Exiting quietly.")
                sys.exit(0)

            # Set the picture mode
            asyncio.run(set_picture_mode(picture_mode))

            # Update the state file for this picture mode
            write_last_set_time(picture_mode, time.time())

    except Exception as e:
        log_message(process_id, start_time, f"Error: {traceback.format_exc()}")
        sys.exit(1)

    finally:
        # The file lock is automatically released when exiting the `with` block
        log_message(process_id, start_time, "Lock released.")
