# inspired by onerandomusername/monty-python#713

import asyncio
import datetime as dt
import http
import os
import pathlib
import sys
import traceback
import typing
from collections import abc
from tkinter import filedialog
from typing import NewType

import anyio
import anyio.to_thread
import attrs
import msgspec
import rich
import rtoml

import disnake
import disnake.http
from discord import CustomEmoji
from disnake.utils import (
    _bytes_to_base64_data as bytes_to_base64_data,  # pyright: ignore[reportPrivateUsage]
)

from app import paths

# FIXME: importing from assets creates EMOJIS etc
from app.assets import Emojis
from defer import Defer

FieldName = NewType("FieldName", str)
FileName = NewType("FileName", str)
EmojiName = NewType("EmojiName", str)

ENV_KEY = "BOT_TOKEN"

FIELD_NAME_TO_EMOJI_NAME: abc.Mapping[FieldName, EmojiName] = typing.cast("abc.Mapping[FieldName, EmojiName]", {
    # item slots
    "item_slot_torso": "torso",
    "item_slot_legs": "legs",
    "item_slot_drone": "drone",
    "item_slot_side_weapon": "side_weapon_r",
    "item_slot_top_weapon": "top_weapon_r",
    "item_slot_charge": "charge",
    "item_slot_teleport": "teleport",
    "item_slot_hook": "hook",
    "item_slot_shield": "shield",
    "item_slot_module": "module",
    "item_slot_perk": "perk",
    "item_slot_kit": "kit",
    # mech slots
    "mech_slot_right_side_weapon": "side_weapon_r",
    "mech_slot_left_side_weapon": "side_weapon_l",
    "mech_slot_right_top_weapon": "top_weapon_r",
    "mech_slot_left_top_weapon": "top_weapon_l",
    # elements
    "element_other": "other",
    "element_physical": "phys_dmg",
    "element_explosive": "exp_dmg",
    "element_electric": "ele_dmg",
    "element_combined": "combined",
    # tiers
    "tier_common": "tier_common",
    "tier_rare": "tier_rare",
    "tier_epic": "tier_epic",
    "tier_legendary": "tier_legendary",
    "tier_mythical": "tier_mythical",
    "tier_divine": "tier_divine",
    "tier_perk": "tier_perk",
    "tier_common_hollow": "tier_common_o",
    "tier_rare_hollow": "tier_rare_o",
    "tier_epic_hollow": "tier_epic_o",
    "tier_legendary_hollow": "tier_legendary_o",
    "tier_mythical_hollow": "tier_mythical_o",
    "tier_divine_hollow": "tier_divine_o",
    "tier_perk_hollow": "tier_perk_o",
    # cards
    "card_common": "common_card",
    "card_rare": "rare_card",
    "card_epic": "epic_card",
    "card_legendary": "legendary_card",
    "card_mythical": "mythical_card",
    # pks
    "power_kit_common": "powerkit_10k",
    "power_kit_rare": "powerkit_50k",
    "stat_power": "power",
    # stats
    "stat_weight": "weight",
    "stat_hit_points": "hit_points",
    "stat_energy_capacity": "ene_cap",
    "stat_energy_regeneration": "regen",
    "stat_heat_capacity": "heat_cap",
    "stat_heat_cooling": "cooling",
    "stat_physical_resistance": "phys_res",
    "stat_explosive_resistance": "exp_res",
    "stat_electric_resistance": "ele_res",
    "stat_bullets_capacity": "bullets",
    "stat_rockets_capacity": "rockets",
    "stat_walk": "walk",
    "stat_jump": "jump",
    "stat_physical_damage": "phys_dmg",
    "stat_physical_resistance_damage": "phys_res_dmg",
    "stat_electric_damage": "ele_dmg",
    "stat_energy_damage": "ene_dmg",
    "stat_energy_capacity_damage": "ene_cap_dmg",
    "stat_regeneration_damage": "ene_reg_dmg",
    "stat_electric_resistance_damage": "ele_res_dmg",
    "stat_explosive_damage": "exp_dmg",
    "stat_heat_damage": "heat_dmg",
    "stat_heat_capacity_damage": "heat_cap_dmg",
    "stat_cooling_damage": "cooling_dmg",
    "stat_explosive_resistance_damage": "exp_res_dmg",
    "stat_range": "range",
    "stat_push": "push",
    "stat_pull": "pull",
    "stat_recoil": "recoil",
    "stat_advance": "advance",
    "stat_retreat": "retreat",
    "stat_uses": "uses",
    "stat_backfire": "backfire",
    "stat_repair": "repair",
    "stat_heat_generation": "heat_cost",
    "stat_energy_cost": "ene_cost",
    "stat_bullets_cost": "bullets",
    "stat_rockets_cost": "rockets",
    "stat_block_percentage": "absorption",
    # arena buffs
    # "buff_energy_capacity":
    # "buff_energy_regeneration":
    # "buff_energy_damage":
    # "buff_heat_capacity":
    # "buff_heat_cooling":
    # "buff_heat_damage":
    # "buff_physical_damage":
    # "buff_explosive_damage":
    # "buff_electric_damage":
    # "buff_physical_resistance":
    # "buff_explosive_resistance":
    # "buff_electric_resistance":
    # "buff_total_hp":
    # "buff_backfire_reduction":
    # "buff_damage_vs_titans":
    # ranks - note that these are saved into an array
    "rank_1": "rank1",
    "rank_2": "rank2",
    "rank_3": "rank3",
    "rank_4": "rank4",
    "rank_5": "rank5",
    "rank_6": "rank6",
    "rank_7": "rank7",
    "rank_8": "rank8",
    "rank_9": "rank9",
    "rank_10": "rank10",
    "rank_11": "rank11",
    "rank_12": "rank12",
    "rank_13": "rank13",
    "rank_14": "rank14",
    "rank_15": "rank15",
    "rank_16": "rank16",
    # currencies
    "currency_gold": "gold",
    "currency_tokens": "tokens",
})  # fmt: skip
EMOJI_NAME_TO_FIELD_NAMES: abc.Mapping[EmojiName, list[FieldName]] = {}

for _k, _v in FIELD_NAME_TO_EMOJI_NAME.items():
    EMOJI_NAME_TO_FIELD_NAMES.setdefault(_v, []).append(_k)

VALID_FIELD_NAMES: abc.Set[FieldName] = FIELD_NAME_TO_EMOJI_NAME.keys()
VALID_EMOJI_NAMES: abc.Set[EmojiName] = EMOJI_NAME_TO_FIELD_NAMES.keys()

ORDERED_FIELD_NAMES: tuple[FieldName, ...] = tuple(attrs.fields_dict(Emojis))  # pyright: ignore[reportAssignmentType]


class Config(msgspec.Struct):
    token: str
    overwrite: bool = False
    purge: bool = False
    manual: bool = False
    cache: bool = False


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
    _cli_parser.add_argument(
        "--manual",
        action="store_true",
        help=f"Whether to show a file picker. If not provided, selects all images under the {paths.ICONS_PNG_DIR} directory.",
    )
    _cli_parser.add_argument(
        "--cache", action="store_true", help=f"Whether to rebuild the {paths.EMOJIS_TOML} file."
    )
    ns = _cli_parser.parse_args()

    assert isinstance(ns.token, str)
    assert isinstance(ns.overwrite, bool)
    assert isinstance(ns.purge, bool)
    assert isinstance(ns.manual, bool)
    assert isinstance(ns.cache, bool)

    if ns.token:
        token = ns.token

    else:
        import dotenv  # noqa: PLC0415

        dotenv.load_dotenv(paths.DEV_ENV)
        try:
            token = os.environ[ENV_KEY]

        except KeyError:
            sys.exit(f"{ENV_KEY} not in env and --token not specified")

    return Config(
        token=token.strip(),
        overwrite=ns.overwrite,
        purge=ns.purge,
        manual=ns.manual,
        cache=ns.cache,
    )


CONFIG = get_config()

type Snowflake = str | int


class FileUpload(msgspec.Struct):
    path: pathlib.Path
    name: EmojiName


async def get_all_app_emojis(
    client: disnake.http.HTTPClient, app_id: Snowflake
) -> list[CustomEmoji]:
    response = await client.request(
        disnake.http.Route(http.HTTPMethod.GET, "/applications/{app_id}/emojis", app_id=app_id)
    )
    return msgspec.convert(response["items"], list[CustomEmoji], strict=False)


async def create_app_emoji(
    client: disnake.http.HTTPClient, app_id: Snowflake, *, name: EmojiName, path: pathlib.Path
) -> CustomEmoji:
    image_data = await anyio.to_thread.run_sync(path.read_bytes)
    response = await client.request(
        disnake.http.Route(http.HTTPMethod.POST, "/applications/{app_id}/emojis", app_id=app_id),
        json={
            "name": name,
            "image": bytes_to_base64_data(image_data),
        },
    )
    return msgspec.convert(response, CustomEmoji, strict=False)


async def delete_app_emoji(
    client: disnake.http.HTTPClient, app_id: Snowflake, *, emoji_id: Snowflake
) -> None:
    await client.request(
        disnake.http.Route(
            http.HTTPMethod.DELETE,
            "/applications/{app_id}/emojis/{emoji_id}",
            app_id=app_id,
            emoji_id=emoji_id,
        )
    )


def file_modified_at(file: pathlib.Path, /) -> dt.datetime:
    return dt.datetime.fromtimestamp(file.stat().st_mtime, tz=dt.UTC)


def main() -> None:
    if CONFIG.manual:
        file_paths = filedialog.askopenfilenames(
            title="Select emojis to upload",
            filetypes=[("png", "*.png")],
            initialdir=paths.ICONS_PNG_DIR,
        )
        if not file_paths:
            print("No files selected, aborting")
            return

        file_paths = [pathlib.Path(p) for p in file_paths]
        print("Selected files:", *(f.name for f in file_paths), sep="\n")

    else:
        file_paths = list(paths.ICONS_PNG_DIR.iterdir())

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

    name_to_file: abc.Mapping[FileName, pathlib.Path] = {FileName(f.stem): f for f in files}
    name_to_emoji: abc.Mapping[EmojiName, CustomEmoji] = {
        EmojiName(e.name): e for e in existing_emojis
    }

    local_file_names = name_to_file.keys()
    remote_emoji_names = name_to_emoji.keys()

    unused_local_files = local_file_names - VALID_FIELD_NAMES
    unused_remote_emojis = remote_emoji_names - VALID_EMOJI_NAMES

    valid_local_file_names = VALID_FIELD_NAMES & local_file_names
    valid_remote_emoji_names = VALID_EMOJI_NAMES & remote_emoji_names

    if CONFIG.overwrite:
        file_names_to_upload = valid_local_file_names
    else:
        existing_internal_emoji_names = {
            internal_n
            for external_n in valid_remote_emoji_names
            for internal_n in EMOJI_NAME_TO_FIELD_NAMES[external_n]
        }
        file_names_to_upload = valid_local_file_names - existing_internal_emoji_names

    files_to_upload = sorted(
        (
            FileUpload(name_to_file[FileName(name)], FIELD_NAME_TO_EMOJI_NAME[name])
            for name in file_names_to_upload
        ),
        key=lambda f: f.name,
    )

    if unused_local_files:
        rich.print("Unused local files:", sorted(unused_local_files))

    if files_to_upload:
        rich.print("New emojis to upload:", files_to_upload)
        if ask_proceed():
            new_emojis = await upload(client, app_id, files_to_upload)
            rich.print("Newly uploaded emojis:", [f"<:{e.name}:{e.id}>" for e in new_emojis])
            existing_emojis += new_emojis
    else:
        print("No files to upload.")

    if CONFIG.cache:
        cache(existing_emojis)

    if unused_remote_emojis:
        if CONFIG.purge:
            emojis_to_delete = [name_to_emoji[n] for n in unused_remote_emojis]
            rich.print("Emojis to purge:", emojis_to_delete)
            if ask_proceed():
                await purge(client, app_id, emojis_to_delete)
        else:
            rich.print("Unused remote emojis:", sorted(unused_remote_emojis))


def ask_proceed() -> bool:
    return input("Proceed? [y/n]: ").lower() in ("y", "yes")


async def upload(
    client: disnake.http.HTTPClient, app_id: Snowflake, to_upload: abc.Sequence[FileUpload]
) -> list[CustomEmoji]:
    new_emojis: list[CustomEmoji] = []

    async def worker(upload: FileUpload, /) -> None:
        new_emojis.append(
            await create_app_emoji(client, app_id, name=upload.name, path=upload.path)
        )

    async with anyio.create_task_group() as tg:
        for upload in to_upload:
            tg.start_soon(worker, upload)

    return new_emojis


async def purge(
    client: disnake.http.HTTPClient, app_id: Snowflake, to_purge: abc.Sequence[CustomEmoji]
) -> None:
    async def worker(emoji: CustomEmoji, /) -> None:
        await delete_app_emoji(client, app_id, emoji_id=emoji.id)

    async with anyio.create_task_group() as tg:
        for emoji in to_purge:
            tg.start_soon(worker, emoji)


def cache(emojis: abc.Sequence[CustomEmoji], /) -> None:
    name_to_emoji = {EmojiName(e.name): e for e in emojis}

    rank_emojis = [EmojiName(e.name) for e in emojis if e.name.startswith("rank")]
    rank_emojis.sort(key=lambda n: int(n[4:]))

    output_toml_dict: dict[FieldName, str | list[str]] = {}

    for field_name in ORDERED_FIELD_NAMES:
        if field_name == "ranks":
            output_toml_dict[field_name] = [
                str(name_to_emoji[emoji_name] for emoji_name in rank_emojis)
            ]
            continue

        if (emoji_name := FIELD_NAME_TO_EMOJI_NAME.get(field_name)) is None:
            continue

        if (emoji := name_to_emoji.get(emoji_name)) is None:
            continue

        output_toml_dict[field_name] = str(emoji)

    toml_string = rtoml.dumps(output_toml_dict)
    try:
        paths.EMOJIS_TOML.write_text(toml_string)
    except OSError as exc:
        print(f"Failed to write to {paths.EMOJIS_TOML}:")
        traceback.print_exception(exc)


if __name__ == "__main__":
    main()
