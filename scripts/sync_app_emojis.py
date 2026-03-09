# inspired by onerandomusername/monty-python#713

import asyncio
import datetime as dt
import http
import os
import pathlib
import sys
from tkinter import filedialog

import anyio
import anyio.to_thread
import msgspec
import rich

import disnake
import disnake.http
from disnake.utils import (
    _bytes_to_base64_data as bytes_to_base64_data,  # pyright: ignore[reportPrivateUsage]
    snowflake_time,
)

from app import paths
from defer import Defer

ENV_KEY = "BOT_TOKEN"


class Config(msgspec.Struct):
    token: str
    overwrite: bool = False
    purge: bool = False


def get_config() -> Config:
    import argparse  # noqa: PLC0415

    _cli_parser = argparse.ArgumentParser()
    _cli_parser.add_argument(
        "--token", action="store", default="", help=f"Bot token to use. env: {ENV_KEY}"
    )
    _cli_parser.add_argument(
        "--overwrite", action="store_true", help="Whether to overwrite existing emojis."
    )
    _cli_parser.add_argument(
        "--purge", action="store_true", help="Whether to delete emojis that are no longer present."
    )
    ns = _cli_parser.parse_args()

    assert isinstance(ns.token, str)
    assert isinstance(ns.overwrite, bool)
    assert isinstance(ns.purge, bool)

    if ns.token:
        token = ns.token

    else:
        import dotenv  # noqa: PLC0415

        dotenv.load_dotenv(paths.DEV_ENV)
        try:
            token = os.environ[ENV_KEY]

        except KeyError:
            sys.exit(f"{ENV_KEY} not in env and --token not specified")

    config = Config(token.strip(), overwrite=ns.overwrite, purge=ns.purge)

    if config.overwrite or config.purge:  # TODO: remove once implemented
        msg = "--overwrite and --purge not implemented yet"
        raise NotImplementedError(msg)

    return config


CONFIG = get_config()

type Snowflake = str | int


class AppEmoji(msgspec.Struct):
    id: int
    name: str


async def get_all_app_emojis(client: disnake.http.HTTPClient, app_id: Snowflake) -> list[AppEmoji]:
    response = await client.request(
        disnake.http.Route(http.HTTPMethod.GET, "/applications/{app_id}/emojis", app_id=app_id)
    )
    return msgspec.convert(response["items"], list[AppEmoji], strict=False)


async def create_app_emoji(
    client: disnake.http.HTTPClient, app_id: Snowflake, *, name: str, path: pathlib.Path
) -> AppEmoji:
    image_data = await anyio.to_thread.run_sync(path.read_bytes)
    response = await client.request(
        disnake.http.Route(http.HTTPMethod.POST, "/applications/{app_id}/emojis", app_id=app_id),
        json={
            "name": name,
            "image": bytes_to_base64_data(image_data),
        },
    )
    return msgspec.convert(response, AppEmoji, strict=False)


def file_modified_at(file: pathlib.Path, /) -> dt.datetime:
    return dt.datetime.fromtimestamp(file.stat().st_mtime, tz=dt.UTC)


def main() -> None:
    file_paths = filedialog.askopenfilenames(
        title="Select emojis to upload",
        filetypes=[("png", "*.png")],
        initialdir=paths.ICONS_PNG_DIR,
    )
    if not file_paths:
        print("No files selected, aborting")
        return

    print("Selected files:", *file_paths, sep="\n")
    file_paths = [pathlib.Path(p) for p in file_paths]

    async def amain_wrapper(files: list[pathlib.Path]) -> None:
        async with Defer() as defer:
            await amain(defer, files)

    anyio.run(amain_wrapper, file_paths)


async def amain(defer: Defer.AsyncDefer, files: list[pathlib.Path]) -> None:
    client = disnake.http.HTTPClient(loop=asyncio.get_running_loop())

    # populates __session and token
    await client.static_login(CONFIG.token)
    defer(client.close)

    app_info = await client.application_info()
    app_id: Snowflake = app_info["id"]

    existing_emojis = await get_all_app_emojis(client, app_id)

    name_to_file: dict[str, pathlib.Path] = {f.stem: f for f in files}

    file_creation_dates: dict[str, dt.datetime] = {f.stem: file_modified_at(f) for f in files}
    emoji_creation_dates: dict[str, dt.datetime] = {
        e.name: snowflake_time(e.id) for e in existing_emojis
    }

    files_to_upload = sorted(file_creation_dates.keys() - emoji_creation_dates.keys())

    if not files_to_upload:
        print("All selected emojis already exist.")
        return

    rich.print("New emojis to upload:", files_to_upload)

    if input("Proceed? [y/n]: ").lower() not in ("y", "yes"):
        return

    new_emojis: list[AppEmoji] = []

    for file_name in files_to_upload:
        file_path = name_to_file[file_name]

        new_emojis.append(await create_app_emoji(client, app_id, name=file_name, path=file_path))

    rich.print("Newly uploaded emojis:", [f"<:{e.name}:{e.id}>" for e in new_emojis])


if __name__ == "__main__":
    main()
