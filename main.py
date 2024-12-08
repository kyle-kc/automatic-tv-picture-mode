import asyncio
import msvcrt
import sys
from enum import Enum

from bscpylgtv import WebOsClient


class PictureMode(str, Enum):
    FILMMAKER_MODE = "filmMaker"
    GAME_OPTIMIZER = "game"


LOCK_FILE_NAME = "lock"
LOG_FILE_NAME = "error.log"


async def set_picture_mode(picture_mode: PictureMode):
    web_os_client = await WebOsClient.create("192.168.0.2", ping_interval=None, states=[])
    await web_os_client.connect()
    result = await web_os_client.set_current_picture_mode(picture_mode)
    if not result["returnValue"]:
        raise RuntimeError("Could not set picture mode.")


def acquire_lock():
    lock_file = open(LOCK_FILE_NAME, "w")
    try:
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        raise RuntimeError("Another instance of this script is already running.")
    return lock_file


def release_lock(lock_file):
    lock_file.close()


def log_error(message):
    with open(LOG_FILE_NAME, "a") as log_file:
        log_file.write(message + "\n")


if __name__ == "__main__":
    lock_file = None
    try:
        lock_file = acquire_lock()
        picture_mode = PictureMode(sys.argv[1])
        asyncio.run(set_picture_mode(picture_mode))
    except Exception as e:
        error_message = f"Error: {e}"
        log_error(error_message)  # Log the error to a file
        sys.exit(1)
    finally:
        if lock_file is not None:
            release_lock(lock_file)
