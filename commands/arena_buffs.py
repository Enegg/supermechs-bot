from __future__ import annotations

import logging
import typing as t

from lib_helpers import CommandInteraction, MessageInteraction
from config import TEST_GUILDS
from disnake import ButtonStyle, SelectOption
from disnake.ext import commands
from SuperMechs.core import STAT_NAMES, ArenaBuffs
from typing_extensions import Self
from ui import EMPTY_OPTION, Button, PaginatorView, Select, TrinaryButton, button, select

if t.TYPE_CHECKING:
    from bot import SMBot

logger = logging.getLogger("channel_logs")


class ArenaBuffsView(PaginatorView):
    MAXED_BUFFS = ArenaBuffs.maxed()
    active: TrinaryButton[Self, bool | None] | None

    def __init__(
        self,
        buffs_ref: ArenaBuffs,
        user_id: int,
        *,
        columns_per_page: int = 3,
        timeout: float | None = 180,
    ) -> None:
        self.buttons = [
            [
                TrinaryButton(
                    item=buffs_ref[id] == self.MAXED_BUFFS[id] or None,
                    callback=self.button_callback,
                    label=f"{buffs_ref.buff_as_str_aware(id):⠀>4}",
                    custom_id=id,
                    emoji=STAT_NAMES[id].emoji,
                    row=pos,
                )
                for id in row
            ]
            for pos, row in enumerate(
                (
                    ("eneCap", "heaCap", "phyDmg", "phyRes", "health"),
                    ("eneReg", "heaCol", "expDmg", "expRes", "backfire"),
                    ("eneDmg", "heaDmg", "eleDmg", "eleRes"),
                )
            )
        ]
        super().__init__(user_id=user_id, timeout=timeout, columns_per_page=columns_per_page)
        self.buffs = buffs_ref
        self.update_page()

    async def button_callback(
        self, button: TrinaryButton[Self, bool | None], inter: MessageInteraction
    ) -> None:
        self.toggle_style(button)
        await inter.response.edit_message(view=self)

    @button(label="Quit", style=ButtonStyle.red, row=3)
    async def quit_button(self, _: Button[Self], inter: MessageInteraction) -> None:
        self.before_stop()
        self.stop()
        await inter.response.edit_message(view=self)

    @button(label="🡸", style=ButtonStyle.blurple, row=3, disabled=True)
    async def left_button(self, button: Button[Self], interaction: MessageInteraction) -> None:
        """Callback for left button"""
        self.page -= 1
        self.update_page()
        self.right_button.disabled = False

        if self.page == 0:
            button.disabled = True

        await interaction.response.edit_message(view=self)

    @button(label="🡺", style=ButtonStyle.blurple, row=3)
    async def right_button(self, button: Button[Self], interaction: MessageInteraction) -> None:
        """Callback for right button"""
        self.page += 1
        self.update_page()
        self.left_button.disabled = False

        if (self.page + 1) * self.columns_per_page >= self.columns:
            button.disabled = True

        await interaction.response.edit_message(view=self)

    @select(options=[EMPTY_OPTION], disabled=True, row=4)
    async def dropdown(self, select: Select[Self], interaction: MessageInteraction) -> None:
        level = int(select.values[0])

        active = self.active
        assert active is not None
        id = active.custom_id
        self.buffs.levels[id] = level

        if level == self.MAXED_BUFFS.levels[id]:
            active.item = True

        else:
            active.item = None

        active.label = self.buffs.buff_as_str_aware(id).rjust(4, "⠀")
        self.toggle_style(active)

        await interaction.response.edit_message(view=self)

    def toggle_style(self, button: TrinaryButton[Self, bool | None]) -> None:
        button.toggle()

        if self.active is button:
            self.dropdown.placeholder = None
            self.dropdown.disabled = True
            self.active = None
            return

        if self.active is None:
            self.dropdown.disabled = False

        else:
            self.active.toggle()

        self.dropdown.placeholder = button.label

        self.dropdown.options = [
            SelectOption(label=f"{level}: {buff}", value=str(level))
            for level, buff in enumerate(self.buffs.iter_as_str(button.custom_id))
        ]

        self.active = button

    def before_stop(self) -> None:
        self.remove_item(self.right_button)
        self.remove_item(self.left_button)
        self.remove_item(self.quit_button)
        self.remove_item(self.dropdown)

        for item in self.visible:
            item.disabled = True


@commands.slash_command()
@commands.max_concurrency(1, commands.BucketType.user)
async def buffs(inter: ApplicationCommandInteraction) -> None:
    """Interactive UI for modifying your arena buffs"""
    player = inter.bot.get_player(inter)
    view = ArenaBuffsView(player.arena_buffs, inter.author.id)

    async def on_timeout() -> None:
        view.before_stop()
        await inter.edit_original_message(view=view)

    view.on_timeout = on_timeout

    await inter.send("**Arena Shop**", view=view)


@commands.slash_command(guild_ids=TEST_GUILDS)
@commands.is_owner()
async def maxed(inter: CommandInteraction) -> None:
    """Maxes out your buffs"""
    me = inter.bot.get_player(inter)
    me.arena_buffs.levels.update(ArenaBuffs.maxed().levels)
    await inter.send("Success", ephemeral=True)


def setup(bot: SMBot) -> None:
    bot.add_slash_command(buffs)
    bot.add_slash_command(maxed)


def teardown(bot: SMBot) -> None:
    bot.remove_slash_command("buffs")
    bot.remove_slash_command("maxed")
