from __future__ import annotations

import asyncio
from io import BytesIO
import aiohttp

import discord
from PIL import Image


async def get_image(link: str, session: aiohttp.ClientSession) -> Image.Image:
    async with session.get(link) as response:
        response.raise_for_status()
        return Image.open(BytesIO(await response.content.read()))


def image_to_file(image: Image.Image, filename: str=None) -> discord.File:
    with BytesIO() as stream:
        image.save(stream, format='png')
        stream.seek(0)
        return discord.File(stream, filename)


def bbox_to_w_h(bbox: tuple[int, int, int, int] | None) -> tuple[int, int]:
    assert bbox is not None
    x, y, a, b = bbox
    return a - x, b - y


if __name__ == '__main__':
    img = asyncio.run(get_image('https://raw.githubusercontent.com/ctrl-raul/supermechs-item-images/master/reloaded/png/EnergyFreeArmor.png', aiohttp.ClientSession()))
    img.show()
    file = image_to_file(img)
    print(file, file.filename)
