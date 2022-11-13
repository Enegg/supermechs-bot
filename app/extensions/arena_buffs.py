from __future__ import annotations

from disnake import ButtonStyle, CommandInteraction, MessageInteraction, SelectOption
from disnake.ext import commands, plugins

from config import TEST_GUILDS
from ui.buttons import Button, TrinaryButton, button
from ui.item import add_callback
from ui.selects import EMPTY_OPTION, Select, select
from ui.views import InteractionCheck, PaginatorView, positioned

from SuperMechs.core import MAX_BUFFS, STATS, ArenaBuffs
from SuperMechs.player import Player

plugin = plugins.Plugin()


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
                        label=str(buffs.modifier_of(id)).rjust(4, "⠀"),
                        custom_id=f"slotbutton:{id}",
                        emoji=STATS[id].emoji,
                    ),
                    self.buff_buttons,
                )
                for id in row
            )

        self.page = 0

    async def buff_buttons(self, button: TrinaryButton[bool], inter: MessageInteraction) -> None:
        self.toggle_style(button)
        await inter.response.edit_message(view=self)

    @positioned(3, 2)
    @button(label="🡺", custom_id="button:next", style=ButtonStyle.blurple)
    async def next_button(self, button: Button[None], inter: MessageInteraction) -> None:
        self.page += 1
        self.prev_button.disabled = False

        if (self.page + 1) * self.columns >= 5:
            button.disabled = True

        await inter.response.edit_message(view=self)

    @positioned(3, 1)
    @button(label="🡸", custom_id="button:prev", style=ButtonStyle.blurple, disabled=True)
    async def prev_button(self, button: Button[None], inter: MessageInteraction) -> None:
        self.page -= 1
        self.next_button.disabled = False

        if self.page == 0:
            button.disabled = True

        await inter.response.edit_message(view=self)

    @positioned(3, 0)
    @button(label="Quit", custom_id="button:quit", style=ButtonStyle.red)
    async def quit_button(self, _: Button[None], inter: MessageInteraction) -> None:
        self.stop()

        for row in self.rows[:3]:
            for button in row:
                button.disabled = True

        for row in self.rows[3:]:
            row.clear_items()

        await inter.response.edit_message(view=self)

    @positioned(4, 0)
    @select(custom_id="select:menu", options=[EMPTY_OPTION], disabled=True)
    async def select_menu(self, select: Select[None], inter: MessageInteraction) -> None:
        level = int(select.values[0])

        assert self.active is not None
        id = self.active.custom_id.rsplit(":", 1)[-1]
        self.buffs.levels[id] = level

        if level == MAX_BUFFS.levels[id]:
            self.active.item = True

        else:
            self.active.item = None

        self.active.label = str(self.buffs.modifier_of(id)).rjust(4, "⠀")
        self.toggle_style(self.active)

        await inter.response.edit_message(view=self)

    def toggle_style(self, button: TrinaryButton[bool]) -> None:
        button.toggle()

        if self.active is button:
            self.select_menu.placeholder = None
            self.select_menu.disabled = True
            self.active = None
            return

        if self.active is None:
            self.select_menu.disabled = False

        else:
            self.active.toggle()

        self.select_menu.placeholder = button.label
        self.select_menu.options = [
            SelectOption(label=f"{level}: {buff}", value=str(level))
            for level, buff in enumerate(
                self.buffs.iter_modifiers_of(button.custom_id.rsplit(":", 1)[-1])
            )
        ]

        self.active = button


@plugin.slash_command()
@commands.max_concurrency(1, commands.BucketType.user)
async def buffs(inter: CommandInteraction, player: Player) -> None:
    """Interactive UI for modifying your arena buffs. {{ ARENA_BUFFS }}"""
    view = ArenaBuffsView(player.arena_buffs, user_id=inter.author.id)
    await inter.response.send_message("**Arena Shop**", view=view, ephemeral=True)
    await view.wait()


@plugin.slash_command(guild_ids=TEST_GUILDS)
@commands.is_owner()
async def maxed(inter: CommandInteraction, player: Player) -> None:
    """Maxes out your arena buffs. {{ BUFFS_MAXED }}"""
    player.arena_buffs.levels.update(ArenaBuffs.maxed().levels)
    await inter.send("Success", ephemeral=True)


setup, teardown = plugin.create_extension_handlers()
