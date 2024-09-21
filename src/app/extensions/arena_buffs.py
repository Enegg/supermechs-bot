from collections import abc
from functools import partial
from typing import Final

from disnake import CommandInteraction, MessageInteraction
from disnake.ext import commands, plugins

from app.assets import ASSETS, INVISIBLE_CHAR
from app.bridges import ui
from app.models import Player

from supermechs.api import ArenaShop, Category

plugin: Final = plugins.Plugin[commands.InteractionBot](name="ArenaBuffs", logger=__name__)


def format_value(category: Category, level: int, /) -> str:
    suffix = "" if category.data.is_absolute else "%"
    value = category.data.progression[level]
    return f"{value:+}{suffix}"


def iter_category(category: Category, /) -> abc.Iterator[str]:
    for level in range(len(category.data.progression)):
        yield format_value(category, level)


def make_label(shop: ArenaShop, category: Category, /) -> str:
    return format_value(category, shop[category]).rjust(4, INVISIBLE_CHAR)


class ArenaShopView:
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

    def __init__(self, store: ui.CallbackStore, shop: ArenaShop) -> None:
        self.store = store
        self.shop = shop
        self.active: ui.ToggleButton | None = None
        self.all_slot_buttons: list[ui.ToggleButton] = []
        self.init_pages(store)

    def init_pages(self, store: ui.CallbackStore) -> None:
        @store.bind(
            ui.ActionButton(label="Quit", style=ui.ButtonStyle.red, custom_id=store.make_id())
        )
        async def quit_button(inter: MessageInteraction) -> None:
            store.stop()
            await inter.response.edit_message(components=self.get_state_stopped())

        def update_state() -> None:
            prev_button.disabled = self.paginator.at_first_page
            next_button.disabled = self.paginator.at_last_page

        @store.bind(
            ui.ActionButton(
                label="🡸", style=ui.ButtonStyle.blurple, disabled=True, custom_id=store.make_id()
            )
        )
        async def prev_button(inter: MessageInteraction) -> None:
            self.paginator.prev_page()
            update_state()
            await inter.response.edit_message(components=self.paginator.page)

        @store.bind(
            ui.ActionButton(label="🡺", style=ui.ButtonStyle.blurple, custom_id=store.make_id())
        )
        async def next_button(inter: MessageInteraction) -> None:
            self.paginator.next_page()
            update_state()
            await inter.response.edit_message(components=self.paginator.page)

        @store.bind(
            ui.ActionButton(label="Max", style=ui.ButtonStyle.green, custom_id=store.make_id())
        )
        async def max_button(inter: MessageInteraction) -> None:
            for btn in self.all_slot_buttons:
                self.modify_buff(btn)
                btn.on = False

            max_button.disabled = True
            self.set_state_idle()
            await inter.response.edit_message(components=self.paginator.page)

        @store.bind(
            ui.StringSelect(
                options=[ui.SelectOption(label="$")], disabled=True, custom_id=store.make_id()
            )
        )
        async def select(inter: MessageInteraction) -> None:
            assert inter.values is not None
            level = int(inter.values[0])

            assert self.active is not None
            self.modify_buff(self.active, level)
            self.set_state_idle()

            await inter.response.edit_message(components=self.paginator.page)

        self.max_button = max_button
        self.select = select
        self.paginator = ui.Paginator(
            [
                [
                    [*map(self.make_button, self.LAYOUT[0][0])],
                    [*map(self.make_button, self.LAYOUT[0][1])],
                    [*map(self.make_button, self.LAYOUT[0][2])],
                    [quit_button, prev_button, next_button, max_button],
                    [select],
                ],
                [
                    [*map(self.make_button, self.LAYOUT[1][0])],
                    [*map(self.make_button, self.LAYOUT[1][1])],
                    [*map(self.make_button, self.LAYOUT[1][2])],
                    [quit_button, prev_button, next_button, max_button],
                    [select],
                ],
            ]
        )
        max_button.disabled = all(
            btn.style_off is ui.ButtonStyle.green for btn in self.all_slot_buttons
        )

    def make_button(self, category: Category, /) -> ui.ToggleButton:
        btn = ui.ToggleButton(
            style_off=(
                ui.ButtonStyle.green
                if self.shop[category] == category.data.max_level
                else ui.ButtonStyle.gray
            ),
            style_on=ui.ButtonStyle.blurple,
            label=make_label(self.shop, category),
            emoji=ASSETS.categories[category.name].emoji,
            custom_id=self.store.make_id(category.name),
        )
        self.store.bind(btn)(partial(self.buff_button, btn))
        self.all_slot_buttons.append(btn)
        return btn

    async def buff_button(self, button: ui.ToggleButton, inter: MessageInteraction) -> None:
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
        category = Category.of_name(self.store.strip_id(button))
        self.select.options = [
            ui.SelectOption(label=f"{level}: {buff}", value=str(level))
            for level, buff in enumerate(iter_category(category))
        ]
        await inter.response.edit_message(components=self.paginator.page)

    def modify_buff(self, button: ui.ToggleButton, level: int = -1) -> None:
        category = Category.of_name(self.store.strip_id(button))
        max_level = category.data.max_level

        if level == -1:
            level = max_level

        self.shop[category] = level

        if level == max_level:
            button.style_off = ui.ButtonStyle.green

        else:
            self.max_button.disabled = False
            button.style_off = ui.ButtonStyle.gray

        button.label = make_label(self.shop, category)

    def set_state_idle(self) -> None:
        if self.active is not None:
            self.active.on = False
            self.active = None

        self.select.placeholder = None
        self.select.disabled = True

    def get_state_stopped(self) -> ui.Components[ui.MessageUIComponent]:
        page = self.paginator.page
        del page[3:]
        for row in page:
            for component in row:
                component.disabled = True

        return page


@plugin.slash_command()
@commands.max_concurrency(1, commands.BucketType.user)
async def buffs(inter: CommandInteraction, player: Player) -> None:
    """Interactive UI for modifying your arena buffs. {{ ARENA_BUFFS }}"""  # noqa: D400
    store = ui.CallbackStore()
    view = ArenaShopView(store, player.arena_shop)

    await inter.response.send_message(
        "**Arena Shop**", components=view.paginator.page, ephemeral=True
    )

    if await store.listen(plugin.bot.wait_for, check=ui.get_check(inter.author), timeout=180):
        await inter.edit_original_response(components=view.get_state_stopped())


setup, teardown = plugin.create_extension_handlers()
