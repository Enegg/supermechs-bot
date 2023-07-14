from __future__ import annotations

import typing as t

from disnake import ButtonStyle, CommandInteraction, MessageInteraction, SelectOption
from disnake.ext import commands, plugins

from library_extensions import INVISIBLE_CHARACTER
from library_extensions.ui import (
    EMPTY_OPTION,
    Button,
    InteractionCheck,
    PaginatorView,
    Select,
    TrinaryButton,
    add_callback,
    button,
    positioned,
    select,
)

from supermechs.api import MAX_BUFFS, STATS, ArenaBuffs, Player

plugin = plugins.Plugin["commands.InteractionBot"](name="ArenaBuffs", logger=__name__)


def custom_id_to_slot(custom_id: str) -> str:
    return custom_id.rsplit(":", 1)[-1]


class ArenaBuffsView(InteractionCheck, PaginatorView):
    def __init__(self, buffs: ArenaBuffs, *, user_id: int, timeout: float = 180) -> None:
        super().__init__(timeout=timeout, columns=3)
        self.user_id = user_id
        self.buffs = buffs
        self.active: TrinaryButton[bool] | None = None

        for i, row in enumerate(
            (
                ("eneCap", "heaCap", "phyDmg", "phyRes", "health"),
                ("eneReg", "heaCol", "expDmg", "expRes", "backfire"),
                ("eneDmg", "heaDmg", "eleDmg", "eleRes"),
            )
        ):
            self.rows[i].extend_page_items(
                add_callback(
                    TrinaryButton(
                        item=buffs[id] == MAX_BUFFS[id] or None,
                        label=str(buffs.modifier_of(id)).rjust(4, INVISIBLE_CHARACTER),
                        custom_id=f"slotbutton:{id}",
                        emoji=STATS[id].emoji,
                    ),
                    self.buff_buttons,
                )
                for id in row
            )

        self.page = 0
        self.max_button.disabled = self.buffs.levels == MAX_BUFFS.levels

    async def buff_buttons(self, button: TrinaryButton[bool], inter: MessageInteraction) -> None:
        button.toggle()
        self.change_style(button)
        await inter.response.edit_message(view=self)

    @positioned(3, 0)
    @button(label="Quit", custom_id="button:quit", style=ButtonStyle.red)
    async def quit_button(self, _: Button[None], inter: MessageInteraction) -> None:
        self.set_state_stopped()
        await inter.response.edit_message(view=self)

    @positioned(3, 1)
    @button(label="🡸", custom_id="button:prev", style=ButtonStyle.blurple, disabled=True)
    async def prev_button(self, button: Button[None], inter: MessageInteraction) -> None:
        self.page -= 1
        self.next_button.disabled = False

        if self.page == 0:
            button.disabled = True

        await inter.response.edit_message(view=self)

    @positioned(3, 2)
    @button(label="🡺", custom_id="button:next", style=ButtonStyle.blurple)
    async def next_button(self, button: Button[None], inter: MessageInteraction) -> None:
        self.page += 1
        self.prev_button.disabled = False

        if (self.page + 1) * self.columns >= 5:
            button.disabled = True

        await inter.response.edit_message(view=self)

    @positioned(3, 3)
    @button(label="Max", custom_id="button:max", style=ButtonStyle.green)
    async def max_button(self, button: Button[None], inter: MessageInteraction) -> None:
        for row in self.rows:
            for item in t.cast(list[TrinaryButton[bool]], row.page_items):
                if item.custom_id.startswith("slotbutton"):
                    slot = custom_id_to_slot(item.custom_id)
                    self.modify_buff(item, MAX_BUFFS.levels[slot])
                    item.on = False

        button.disabled = True
        self.set_state_idle()
        await inter.response.edit_message(view=self)

    @positioned(4, 0)
    @select(custom_id="select:menu", options=[EMPTY_OPTION], disabled=True)
    async def select_menu(self, select: Select[None], inter: MessageInteraction) -> None:
        level = int(select.values[0])

        assert self.active is not None
        self.modify_buff(self.active, level)
        self.active.toggle()
        self.change_style(self.active)

        await inter.response.edit_message(view=self)

    def modify_buff(self, button: TrinaryButton[bool], level: int) -> None:
        slot = custom_id_to_slot(button.custom_id)
        self.buffs.levels[slot] = level

        if level == MAX_BUFFS.levels[slot]:
            button.item = True

        else:
            self.max_button.disabled = False
            button.item = None

        button.label = str(self.buffs.modifier_of(slot)).rjust(4, INVISIBLE_CHARACTER)

    def set_state_idle(self) -> None:
        if self.active is not None:
            self.active.on = False

        select = self.select_menu
        select.placeholder = None
        select.disabled = True
        self.active = None

    def change_style(self, button: TrinaryButton[bool]) -> None:
        select = self.select_menu
        if self.active is button:
            self.set_state_idle()
            return

        if self.active is None:
            select.disabled = False

        else:
            self.active.toggle()

        self.active = button

        select.placeholder = button.label
        stat_name = button.custom_id.rsplit(":", 1)[-1]
        select.options = [
            SelectOption(label=f"{level}: {buff}", value=str(level))
            for level, buff in enumerate(self.buffs.iter_modifiers_of(stat_name))
        ]

    def set_state_stopped(self) -> None:
        self.stop()

        for row in self.rows[:3]:
            for btn in row:
                btn.disabled = True

        for row in self.rows[3:]:
            row.clear_items()


@plugin.slash_command()
@commands.max_concurrency(1, commands.BucketType.user)
async def buffs(inter: CommandInteraction, player: Player) -> None:
    """Interactive UI for modifying your arena buffs. {{ ARENA_BUFFS }}"""
    view = ArenaBuffsView(player.arena_buffs, user_id=inter.author.id)
    await inter.response.send_message("**Arena Shop**", view=view, ephemeral=True)

    if await view.wait():
        view.set_state_stopped()
        await inter.edit_original_response(view=view)


setup, teardown = plugin.create_extension_handlers()
