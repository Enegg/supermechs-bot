import typing
from collections import abc

from disnake import ButtonStyle, CommandInteraction, MessageInteraction, SelectOption, ui
from disnake.ext import commands, plugins

from assets import CATEGORY
from discord_extensions import SPACE
from discord_extensions.ui import (
    EMPTY_OPTION,
    Paginator,
    SaneView,
    ToggleButton,
    invoker_bound,
    metadata_of,
    random_str,
    with_callback,
)
from models import Player

from supermechs.api import ArenaShop, Category

plugin: typing.Final = plugins.Plugin[commands.InteractionBot](name="ArenaBuffs", logger=__name__)


@plugin.load_hook(post=True)
async def on_load() -> None:
    from events import BUFFS_LOADED

    BUFFS_LOADED.set()


def format_value(category: Category, level: int, /) -> str:
    string = f"{category.data.progression[level]:+}"
    if not category.data.is_absolute:
        string += "%"
    return string


def iter_category(category: Category, /) -> abc.Iterator[str]:
    for level in range(len(category.data.progression)):
        yield format_value(category, level)


def make_label(shop: ArenaShop, category: Category, /) -> str:
    return format_value(category, shop[category]).rjust(4, SPACE)


@invoker_bound
class ArenaShopView(SaneView):
    LAYOUT: abc.Sequence[abc.Sequence[abc.Sequence[Category]]] = (
        (
            (Category.energy_capacity,     Category.heat_capacity, Category.physical_damage),
            (Category.energy_regeneration, Category.heat_cooling,  Category.explosive_damage),
            (Category.energy_damage,       Category.heat_damage,   Category.electric_damage),
        ),
        (
            (Category.physical_resistance,  Category.total_hp),
            (Category.explosive_resistance, Category.backfire_reduction),
            (Category.electric_resistance,  ),
        ),
    )  # fmt: skip

    def __init__(self, shop: ArenaShop, *, user_id: int, timeout: float = 180) -> None:
        self.user_id = user_id
        self.shop = shop
        self.active: ToggleButton | None = None
        self.all_slot_buttons: list[ToggleButton] = []
        self.id = random_str()

        pages: list[list[ui.ActionRow[ui.MessageUIComponent]]] = []
        self.paginator = Paginator(pages)

        for page in self.LAYOUT:
            rows: list[ui.ActionRow[ui.MessageUIComponent]] = []
            pages.append(rows)

            for row in page:
                action_row = ui.ActionRow[ui.MessageUIComponent]()
                rows.append(action_row)

                for category in row:
                    btn = ToggleButton(
                        style_off=(
                            ButtonStyle.green
                            if shop[category] == category.data.max_level
                            else ButtonStyle.gray
                        ),
                        style_on=ButtonStyle.blurple,
                        label=make_label(shop, category),
                        custom_id=f"{self.id}:{category.name}",
                        emoji=CATEGORY[category],
                    )
                    with_callback(btn, self.buff_button)
                    self.all_slot_buttons.append(btn)
                    action_row.append_item(btn)

        super().__init__(*self.paginator.page, timeout=timeout)

        self.max_button.disabled = all(
            btn.style_off is ButtonStyle.green for btn in self.all_slot_buttons
        )

    def swap_rows(self) -> None:
        self.rows[:3] = self.paginator.page

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
        category = Category.of_name(metadata_of(button)[0])
        self.select.options = [
            SelectOption(label=f"{level}: {buff}", value=str(level))
            for level, buff in enumerate(iter_category(category))
        ]
        await inter.response.edit_message(view=self)

    @SaneView.button(3, 0, label="Quit", style=ButtonStyle.red)
    async def quit_button(self, inter: MessageInteraction) -> None:
        self.stop()
        self.set_state_stopped()
        await inter.response.edit_message(view=self)

    @SaneView.button(3, 1, label="🡸", style=ButtonStyle.blurple, disabled=True)
    async def prev_button(self, inter: MessageInteraction) -> None:
        self.paginator.prev_page()
        self.next_button.disabled = False

        if self.paginator.at_first_page:
            self.prev_button.disabled = True

        self.swap_rows()
        await inter.response.edit_message(view=self)

    @SaneView.button(3, 2, label="🡺", style=ButtonStyle.blurple)
    async def next_button(self, inter: MessageInteraction) -> None:
        self.paginator.next_page()
        self.prev_button.disabled = False

        if self.paginator.at_last_page:
            self.next_button.disabled = True

        self.swap_rows()
        await inter.response.edit_message(view=self)

    @SaneView.button(3, 3, label="Max", style=ButtonStyle.green)
    async def max_button(self, inter: MessageInteraction) -> None:
        for btn in self.all_slot_buttons:
            self.modify_buff(btn)
            btn.on = False

        self.max_button.disabled = True
        self.set_state_idle()
        await inter.response.edit_message(view=self)

    @SaneView.string_select(4, 0, options=[EMPTY_OPTION], disabled=True)
    async def select(self, inter: MessageInteraction) -> None:
        level = int(self.select.values[0])

        assert self.active is not None
        self.modify_buff(self.active, level)
        self.set_state_idle()

        await inter.response.edit_message(view=self)

    def modify_buff(self, button: ToggleButton, level: int = -1) -> None:
        category = Category.of_name(metadata_of(button)[0])
        max_level = category.data.max_level

        if level == -1:
            level = max_level

        self.shop[category] = level

        if level == max_level:
            button.style_off = ButtonStyle.green

        else:
            self.max_button.disabled = False
            button.style_off = ButtonStyle.gray

        button.label = make_label(self.shop, category)

    def set_state_idle(self) -> None:
        if self.active is not None:
            self.active.on = False
            self.active = None

        self.select.placeholder = None
        self.select.disabled = True

    def set_state_stopped(self) -> None:
        for row in self.rows[:3]:
            for btn in row:
                btn.disabled = True

        for row in self.rows[3:]:
            row.clear_items()


@plugin.slash_command()
@commands.max_concurrency(1, commands.BucketType.user)
async def buffs(inter: CommandInteraction, player: Player) -> None:
    """Interactive UI for modifying your arena buffs. {{ ARENA_BUFFS }}"""
    view = ArenaShopView(player.arena_shop, user_id=inter.author.id)
    await inter.response.send_message("**Arena Shop**", view=view, ephemeral=True)

    if await view.wait():
        view.set_state_stopped()
        await inter.edit_original_response(view=view)


setup, teardown = plugin.create_extension_handlers()
