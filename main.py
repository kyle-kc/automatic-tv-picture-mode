import asyncio
import msvcrt
import os
import sys
import time
import traceback
from enum import Enum
from pathlib import Path
from uuid import uuid4

from bscpylgtv import WebOsClient


class PictureMode(str, Enum):
    FILMMAKER_MODE = "filmMaker"
    GAME_OPTIMIZER = "game"


LOCK_FILE_NAME = "lock.queue"
LOG_FILE_NAME = "error.log"


async def set_picture_mode(picture_mode: PictureMode):
    web_os_client = await WebOsClient.create("192.168.0.2", ping_interval=None, states=[])
    await web_os_client.connect()
    result = await web_os_client.set_current_picture_mode(picture_mode)
    if not result["returnValue"]:
        raise RuntimeError("Could not set picture mode.")


def acquire_fifo_lock(process_id: str):
    lock_file_path = Path(LOCK_FILE_NAME)
    start_time = time.time()

    lock_file_path.touch(exist_ok=True)

    with open(LOCK_FILE_NAME, "r+") as lock_fd:
        while True:
            try:
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, os.path.getsize(LOCK_FILE_NAME) + 1)

                lock_fd.seek(0)
                queue = lock_fd.read().strip().splitlines()

                if not queue or queue[0] == process_id:
                    if process_id not in queue:
                        queue.append(process_id)
                        lock_fd.seek(0)
                        lock_fd.write("\n".join(queue) + "\n")
                        lock_fd.truncate()
                    break
            except OSError:
                pass
            finally:
                try:
                    msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, os.path.getsize(LOCK_FILE_NAME) + 1)
                except OSError:
                    pass

            if time.time() - start_time > 60:
                raise RuntimeError("Timeout while waiting for the lock.")

            time.sleep(0.1)


def release_fifo_lock(lock_file, process_id: str):
    lock_path = Path(lock_file)
    if not lock_path.exists():
        return

    with open(lock_file, "r+") as lock_fd:
        try:
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, os.path.getsize(lock_file) + 1)

            lock_fd.seek(0)
            queue = lock_fd.read().strip().splitlines()

            if process_id in queue:
                queue.remove(process_id)

            lock_fd.seek(0)
            lock_fd.write("\n".join(queue) + "\n")
            lock_fd.truncate()
        finally:
            try:
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, os.path.getsize(lock_file) + 1)
            except OSError:
                pass


def log_error(message):
    with open(LOG_FILE_NAME, "a") as log_file:
        log_file.write(message + "\n")


if __name__ == "__main__":
    process_id = str(uuid4())
    try:
        acquire_fifo_lock(process_id)
        picture_mode = PictureMode(sys.argv[1])
        asyncio.run(set_picture_mode(picture_mode))
    except Exception as e:
        log_error(traceback.format_exc())
        sys.exit(1)
    finally:
        release_fifo_lock(LOCK_FILE_NAME, process_id)
