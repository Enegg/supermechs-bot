import typing as t

from disnake import ButtonStyle, CommandInteraction, MessageInteraction, SelectOption
from disnake.ext import commands, plugins
from disnake.ui import Button, StringSelect, button, string_select

from assets import STAT
from library_extensions import SPACE
from library_extensions.ui import (
    EMPTY_OPTION,
    PaginatorView,
    ToggleButton,
    add_callback,
    invoker_bound,
    metadata_of,
    positioned,
)

from supermechs.api import Player
from supermechs.arena_buffs import ArenaBuffs, iter_modifiers_of, max_level_of
from supermechs.item_stats import Stat

plugin: t.Final = plugins.Plugin["commands.InteractionBot"](name="ArenaBuffs", logger=__name__)


def make_label(buffs: ArenaBuffs, stat_key: Stat, /) -> str:
    return str(buffs.modifier_of(stat_key)).rjust(4, SPACE)


@invoker_bound
class ArenaBuffsView(PaginatorView):
    def __init__(self, buffs: ArenaBuffs, *, user_id: int, timeout: float = 180) -> None:
        super().__init__(timeout=timeout, columns=3)
        self.user_id = user_id
        self.buffs = buffs
        self.active: ToggleButton | None = None
        self.all_slot_buttons: list[ToggleButton] = []

        for i, row in enumerate(
            (
                (
                    Stat.energy_capacity,
                    Stat.heat_capacity,
                    Stat.physical_damage,
                    Stat.physical_resistance,
                    Stat.hit_points,
                ),
                (
                    Stat.regeneration,
                    Stat.cooling,
                    Stat.explosive_damage,
                    Stat.explosive_resistance,
                    Stat.backfire,
                ),
                (
                    Stat.energy_damage,
                    Stat.heat_damage,
                    Stat.electric_damage,
                    Stat.electric_resistance,
                ),
            )
        ):
            for stat_key in row:
                btn = ToggleButton(
                    style_off=ButtonStyle.green
                    if buffs[stat_key] == max_level_of(stat_key)
                    else ButtonStyle.gray,
                    style_on=ButtonStyle.blurple,
                    label=make_label(buffs, stat_key),
                    custom_id=f"{self.id}:{stat_key.name}",
                    emoji=STAT[stat_key],
                )
                add_callback(btn, self.buff_button)
                self.all_slot_buttons.append(btn)
                self.rows[i].extend_page_items(btn)

        self.page = 0
        self.max_button.disabled = all(
            btn.style_off is ButtonStyle.green for btn in self.all_slot_buttons
        )

    async def buff_button(self, button: ToggleButton, inter: MessageInteraction) -> None:
        if self.active is button:
            self.set_state_idle()
            return

        button.on = True

        if self.active is None:
            self.select.disabled = False

        else:
            self.active.on = False

        self.active = button
        self.select.placeholder = button.label
        stat_key = Stat.of_name(metadata_of(button)[0])
        self.select.options = [
            SelectOption(label=f"{level}: {buff}", value=str(level))
            for level, buff in enumerate(iter_modifiers_of(stat_key))
        ]
        await inter.response.edit_message(view=self)

    @positioned(3, 0)
    @button(label="Quit", style=ButtonStyle.red)
    async def quit_button(self, button: Button[None], inter: MessageInteraction) -> None:
        del button
        self.set_state_stopped()
        await inter.response.edit_message(view=self)

    @positioned(3, 1)
    @button(label="🡸", style=ButtonStyle.blurple, disabled=True)
    async def prev_button(self, button: Button[None], inter: MessageInteraction) -> None:
        self.page -= 1
        self.next_button.disabled = False

        if self.page == 0:
            button.disabled = True

        await inter.response.edit_message(view=self)

    @positioned(3, 2)
    @button(label="🡺", style=ButtonStyle.blurple)
    async def next_button(self, button: Button[None], inter: MessageInteraction) -> None:
        self.page += 1
        self.prev_button.disabled = False

        if self.page == 1:
            button.disabled = True

        await inter.response.edit_message(view=self)

    @positioned(3, 3)
    @button(label="Max", style=ButtonStyle.green)
    async def max_button(self, button: Button[None], inter: MessageInteraction) -> None:
        for btn in self.all_slot_buttons:
            self.modify_buff(btn)
            btn.on = False

        button.disabled = True
        self.set_state_idle()
        await inter.response.edit_message(view=self)

    @positioned(4, 0)
    @string_select(options=[EMPTY_OPTION], disabled=True)
    async def select(self, select: StringSelect[None], inter: MessageInteraction) -> None:
        level = int(select.values[0])

        assert self.active is not None
        self.modify_buff(self.active, level)
        self.set_state_idle()

        await inter.response.edit_message(view=self)

    def modify_buff(self, button: ToggleButton, level: int = -1) -> None:
        stat_key = Stat.of_name(metadata_of(button)[0])
        max_level = max_level_of(stat_key)

        if level == -1:
            level = max_level

        self.buffs.levels[stat_key] = level

        if level == max_level:
            button.style_off = ButtonStyle.green

        else:
            self.max_button.disabled = False
            button.style_off = ButtonStyle.gray

        button.label = make_label(self.buffs, stat_key)

    def set_state_idle(self) -> None:
        if self.active is not None:
            self.active.on = False
            self.active = None

        self.select.placeholder = None
        self.select.disabled = True

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
