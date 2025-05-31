# pyright: reportUninitializedInstanceVariable=false
from collections import abc
from functools import partial

from app.disnake_types import CommandInteraction
from discord.commands import register_cancellable

from app import ui
from app.assets import EMOJIS
from app.core import CONFIG
from app.gamerules import ARENA_BONUSES, MAXED_ARENA_SHOP
from app.models import Player
from app.plugins_factory import create_plugin
from app.text_utils import Char
from defer import Defer

import dupermechs.all as sm
from dupermechs.enums import ArenaShopCategory
from dupermechs.stats import AnyBonus, FlatBonus, MultiplierBonus

plugin = create_plugin(__name__)


def format_bonus(bonus: AnyBonus, /) -> str:
    match bonus:
        case FlatBonus(value):
            return f"{value:+}"

        case MultiplierBonus():
            multi = bonus.as_percent()
            if multi.is_integer():
                return f"{multi:+.0f}%"
            return f"{multi:+f}%"


def iter_category(category: ArenaShopCategory, /) -> abc.Iterator[str]:
    for bonus in ARENA_BONUSES[category]:
        yield format_bonus(bonus)


def make_label(shop: sm.IArenaShopLevels, category: ArenaShopCategory, /) -> str:
    return format_bonus(ARENA_BONUSES[category][shop[category]]).rjust(4, Char.BLANK)


def is_shop_maxed(shop: sm.IArenaShopLevels, /) -> bool:
    return shop == MAXED_ARENA_SHOP


class ArenaShopView:
    LAYOUT: abc.Sequence[abc.Sequence[abc.Sequence[ArenaShopCategory]]] = (
        (
            (ArenaShopCategory.energy_capacity,     ArenaShopCategory.heat_capacity, ArenaShopCategory.physical_damage),
            (ArenaShopCategory.energy_regeneration, ArenaShopCategory.heat_cooling,  ArenaShopCategory.explosive_damage),
            (ArenaShopCategory.energy_damage,       ArenaShopCategory.heat_damage,   ArenaShopCategory.electric_damage),
        ),
        (
            (ArenaShopCategory.physical_resistance,  ArenaShopCategory.total_hp),
            (ArenaShopCategory.explosive_resistance, ArenaShopCategory.backfire_reduction),
            (ArenaShopCategory.electric_resistance,  ArenaShopCategory.damage_vs_titans),
        ),
    )  # fmt: skip

    def __init__(self, store: ui.CallbackStore, shop: sm.ArenaShopLevels) -> None:
        self.store = store
        self.shop = shop
        self.active: ui.ToggleButton | None = None
        self.all_slot_buttons: list[ui.ToggleButton] = []
        self.init_pages(store)

    def init_pages(self, store: ui.CallbackStore) -> None:
        def update_state() -> None:
            prev_button.disabled = self.paginator.at_first_page
            next_button.disabled = self.paginator.at_last_page

        @store.bind(
            ui.ActionButton(
                label="🡸", style=ui.ButtonStyle.blurple, disabled=True, custom_id=store.make_id()
            )
        )
        async def prev_button(inter: ui.MessageInteraction) -> None:
            self.paginator.prev_page()
            update_state()
            await inter.response.edit_message(components=self.paginator.page)

        @store.bind(
            ui.ActionButton(label="🡺", style=ui.ButtonStyle.blurple, custom_id=store.make_id())
        )
        async def next_button(inter: ui.MessageInteraction) -> None:
            self.paginator.next_page()
            update_state()
            await inter.response.edit_message(components=self.paginator.page)

        @store.bind(
            ui.ActionButton(label="Max", style=ui.ButtonStyle.green, custom_id=store.make_id())
        )
        async def max_button(inter: ui.MessageInteraction) -> None:
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
        async def select(inter: ui.MessageInteraction) -> None:
            assert inter.values
            assert self.active is not None

            level = int(inter.values[0])
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
                    [prev_button, next_button, max_button],
                    [select],
                ],
                [
                    [*map(self.make_button, self.LAYOUT[1][0])],
                    [*map(self.make_button, self.LAYOUT[1][1])],
                    [*map(self.make_button, self.LAYOUT[1][2])],
                    [prev_button, next_button, max_button],
                    [select],
                ],
            ]
        )
        max_button.disabled = is_shop_maxed(self.shop)

    def make_button(self, category: ArenaShopCategory, /) -> ui.ToggleButton:
        btn = ui.ToggleButton(
            style_off=(
                ui.ButtonStyle.green
                if self.shop[category] == MAXED_ARENA_SHOP[category]
                else ui.ButtonStyle.gray
            ),
            style_on=ui.ButtonStyle.blurple,
            label=make_label(self.shop, category),
            emoji=EMOJIS.categories[category],
            custom_id=self.store.make_id(category.name),
        )
        self.store.bind(btn)(partial(self.buff_button, btn))
        self.all_slot_buttons.append(btn)
        return btn

    async def buff_button(self, button: ui.ToggleButton, inter: ui.MessageInteraction) -> None:
        if self.active is button:
            self.set_state_idle()
            await inter.response.edit_message(components=self.paginator.page)
            return

        button.on = True

        if self.active is None:
            self.select.disabled = False

        else:
            self.active.on = False

        self.active = button
        self.select.placeholder = button.label
        category = ArenaShopCategory[self.store.strip_id(button)]
        self.select.options = [
            ui.SelectOption(label=f"{level}: {buff}", value=str(level))
            for level, buff in enumerate(iter_category(category))
        ]
        await inter.response.edit_message(components=self.paginator.page)

    def modify_buff(self, button: ui.ToggleButton, level: int = -1) -> None:
        category = ArenaShopCategory[self.store.strip_id(button)]

        max_level = MAXED_ARENA_SHOP[category]

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

    def get_state_stopped(self) -> ui.MessageComponents:
        page = self.paginator.page
        del page[3:]
        for row in page:
            for component in row:
                component.disabled = True

        return page


@register_cancellable
@plugin.slash_command()
async def buffs(inter: CommandInteraction, player: Player) -> None:
    """Interactive UI for modifying your arena buffs. {{ ARENA_BUFFS }}"""  # noqa: D400
    store = ui.callback_store(inter)
    view = ArenaShopView(store, player.arena_shop)

    await inter.response.send_message(
        "**Arena Shop**", components=view.paginator.page, ephemeral=True
    )

    async with Defer(shield=True) as defer:
        defer(lambda: inter.edit_original_response(components=view.get_state_stopped()))
        await store.listen(timeout=CONFIG.user_input_timeout)


setup, teardown = plugin.create_extension_handlers()
