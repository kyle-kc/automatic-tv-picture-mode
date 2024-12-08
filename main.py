from enum import Enum

from bscpylgtv import WebOsClient
import asyncio
import sys

class PictureMode(str, Enum):
    FILMMAKER_MODE = "filmMaker"
    GAME_OPTIMIZER = "game"


async def set_picture_mode(picture_mode: PictureMode):
    web_os_client = await WebOsClient.create("192.168.0.2", ping_interval=None, states=[])
    await web_os_client.connect()
    result = await web_os_client.set_current_picture_mode(picture_mode)
    if not result["returnValue"]:
        raise RuntimeError("Could not set picture mode.")

if __name__ == "__main__":
    picture_mode = PictureMode(sys.argv[1])
    asyncio.run(set_picture_mode(picture_mode))
