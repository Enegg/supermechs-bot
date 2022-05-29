from __future__ import annotations

import asyncio
import logging
import typing as t

from lib_helpers import CommandInteraction, MessageInteraction
from config import TEST_GUILDS
from disnake import ButtonStyle, SelectOption
from disnake.ext import commands
from SuperMechs.player import Player
from SuperMechs.core import STATS, ArenaBuffs, MAX_BUFFS
from ui import EMPTY_OPTION, Button, Select, TrinaryButton
from utils import unique_id

if t.TYPE_CHECKING:
    from bot import SMBot

logger = logging.getLogger("channel_logs")


@commands.slash_command()
@commands.max_concurrency(1, commands.BucketType.user)
async def buffs(inter: CommandInteraction, player: Player) -> None:
    """Interactive UI for modifying your arena buffs. {{ ARENA_BUFFS }}"""
    buffs = player.arena_buffs
    session_key = unique_id()
    columns_per_page = 3
    page = 0
    active: TrinaryButton[bool] | None = None

    buttons = [
        [
            TrinaryButton(
                item=buffs[id] == MAX_BUFFS[id] or None,
                label=f"{buffs.buff_as_str_aware(id):⠀>4}",
                custom_id=f"{session_key}:sb:{id}",
                emoji=STATS[id].emoji,
            )
            for id in row
        ]
        for row in (
            ("eneCap", "heaCap", "phyDmg", "phyRes", "health"),
            ("eneReg", "heaCol", "expDmg", "expRes", "backfire"),
            ("eneDmg", "heaDmg", "eleDmg", "eleRes"),
        )
    ]

    prev = Button(
        label="🡸", custom_id=f"{session_key}:prev", style=ButtonStyle.blurple, disabled=True
    )
    next_ = Button(label="🡺", custom_id=f"{session_key}:next", style=ButtonStyle.blurple)
    quit_ = Button(label="Quit", custom_id=f"{session_key}:quit", style=ButtonStyle.red)
    menu = Select(custom_id=f"{session_key}:menu", options=[EMPTY_OPTION], disabled=True)

    def toggle_style(button: TrinaryButton[bool]) -> None:
        button.toggle()
        nonlocal active

        if active is button:
            menu.placeholder = None
            menu.disabled = True
            active = None
            return

        if active is None:
            menu.disabled = False

        else:
            active.toggle()

        menu.placeholder = button.label

        menu.options = [
            SelectOption(label=f"{level}: {buff}", value=str(level))
            for level, buff in enumerate(buffs.iter_as_str(button.custom_id.rsplit(":", 1)[-1]))
        ]

        active = button

    def get_components():
        offset = columns_per_page * page

        return (
            *(row[offset : columns_per_page + offset] for row in buttons),
            (quit_, prev, next_),
            menu,
        )

    def lock_buttons():
        offset = columns_per_page * page
        final_buttons = [row[offset : columns_per_page + offset] for row in buttons]

        for row in final_buttons:
            for button in row:
                button.disabled = True

        return final_buttons

    def check(interaction: MessageInteraction) -> bool:
        return interaction.data.custom_id.startswith(session_key)

    await inter.response.send_message("**Arena Shop**", components=get_components(), ephemeral=True)

    while True:
        try:
            item_inter: MessageInteraction = await inter.bot.wait_for(
                "message_interaction", timeout=120, check=check
            )

        except asyncio.TimeoutError:
            await inter.edit_original_message(components=lock_buttons())
            return

        if item_inter.author != inter.author:
            await item_inter.send("This message is for someone else.", ephemeral=True)
            continue

        match item_inter.data.custom_id.split(":"):
            case [_, "sb", _]:
                for button in (button for row in buttons for button in row):
                    if button.custom_id == item_inter.data.custom_id:
                        toggle_style(button)
                        break

            case [_, "next"]:
                page += 1
                prev.disabled = False

                if (page + 1) * columns_per_page >= 5:
                    next_.disabled = True

            case [_, "prev"]:
                page -= 1
                next_.disabled = False

                if page == 0:
                    prev.disabled = True

            case [_, "menu"]:
                assert item_inter.data.values is not None
                level = int(item_inter.data.values[0])

                assert active is not None
                id = active.custom_id.rsplit(":", 1)[-1]
                buffs.levels[id] = level

                if level == MAX_BUFFS.levels[id]:
                    active.item = True

                else:
                    active.item = None

                active.label = buffs.buff_as_str_aware(id).rjust(4, "⠀")
                toggle_style(active)

            case [_, "quit"]:
                await item_inter.response.edit_message(components=lock_buttons())
                return

        await item_inter.response.edit_message(components=get_components())


@commands.slash_command(guild_ids=TEST_GUILDS)
@commands.is_owner()
async def maxed(inter: CommandInteraction) -> None:
    """Maxes out your arena buffs. {{ BUFFS_MAXED }}"""
    me = inter.bot.get_player(inter)
    me.arena_buffs.levels.update(ArenaBuffs.maxed().levels)
    await inter.send("Success", ephemeral=True)


def setup(bot: SMBot) -> None:
    bot.add_slash_command(buffs)
    bot.add_slash_command(maxed)


def teardown(bot: SMBot) -> None:
    bot.remove_slash_command("buffs")
    bot.remove_slash_command("maxed")
