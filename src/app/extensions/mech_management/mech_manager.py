import typing
from collections import abc
from functools import partial

from app import i18n
from app.assets import ASSETS, get_weight_emoji
from app.bridges.embeds import embed_image  # noqa: TCH001
from app.devtools import debug_footer
from app.models import ItemPack, MechBuild, Player
from app.shared.utils import SPACE
from discord_plus import ComponentLimits, EmbedColorType
from discord_plus.ui import ActionButton, ComponentStore, PaginatedSelect, Paginator, ToggleButton

from disnake import ButtonStyle, Embed, Locale, MessageInteraction, SelectOption, ui
from disnake.utils import MISSING

from supermechs.abc.item import ItemID
from supermechs.api import ArenaShop, Element, Item, ItemData, Mech, Stat, Type, is_shop_empty
from supermechs.mech import SlotType
from supermechs.tools.mech import dominant_element
from supermechs.tools.stats import buff_stats, mech_summary


def embed_mech(mech: Mech, locale: Locale, name: str) -> Embed:
    embed = Embed(
        title=i18n.get_message(locale, "mech-summary-title", name=name),
        color=color_from_mech(mech),
    ).add_field(i18n.get_message(locale, "mech-summary-field"), format_summary(mech, locale))
    return embed


def get_mech_config(mech: Mech, /) -> str:
    """Returns a string of item IDs that are visible on image."""
    return "_".join(
        "0" if item is None else str(item.data.id) for item in mech.iter_items("body", "weapons")
    )


def format_summary(mech: Mech, locale: Locale, buff_with: ArenaShop | None = None) -> str:
    """Returns a string of lines formatted with mech stats.

    Parameters
    ----------
    mech: `Mech` to format stats of.
    locale: `Locale` to use for i18n of stat names.
    buff_with: optional `ArenaShop` to apply buffs from.
    """
    summary = mech_summary(mech)

    if buff_with is not None:
        summary = buff_stats(summary, buff_with, skip_hp=False)

    return "\n".join(
        "{stat_emoji} **{value}** {stat_name}{extra}".format(
            stat_emoji=ASSETS.stats[stat].emoji,
            value=value,
            stat_name=i18n.get_stat_name(locale, stat),
            extra=" " + get_weight_emoji(value) if stat is Stat.weight else "",
        )
        for stat, value in summary.items()
        if value != 0 or stat is Stat.weight
    )


def slot_emoji(slot: SlotType, /) -> str:
    """Returns the emoji representing a slot, with respect to the right & left variants."""

    if isinstance(slot, tuple):
        slot, n = slot

        if slot is not Type.MODULE:
            asset = ASSETS.sided_types[slot]
            return (asset.right if n % 2 else asset.left).emoji

    return ASSETS.types[slot].emoji


def sorted_options(
    options: abc.Mapping[Element, list[SelectOption]], primary_element: Element | None, /
) -> list[SelectOption]:
    """Returns a list of `SelectOption`s sorted by element.

    Note: this ignores the option limit.
    """
    all_options: list[SelectOption] = []

    if sum(map(len, options.values())) + 1 <= ComponentLimits.select_options:
        it = options.values()

    else:
        element_order = list(ASSETS.elements)

        if primary_element is not None:
            element_order.remove(primary_element)
            element_order.insert(0, primary_element)

        it = (options[key] for key in element_order)

    for option_list in it:
        all_options += option_list

    return all_options


def color_from_mech(mech: Mech, /) -> EmbedColorType:
    if (dominant := dominant_element(mech)) is not None:
        key = dominant

    elif mech.torso is not None:
        key = mech.torso.element

    else:
        return None

    return ASSETS.elements[key].color


def slot_to_type(metadata: abc.Sequence[str], /) -> SlotType:
    type_ = Type.of_name(metadata[0])

    if type_ in (Type.SIDE_WEAPON, Type.TOP_WEAPON, Type.MODULE):
        return type_, int(metadata[1])

    return type_


def group_items(pack: ItemPack, /) -> dict[Type, dict[Element, list[SelectOption]]]:
    item_groups = {type_: {element: list[ItemData]() for element in Element} for type_ in Type}

    for item in pack.items.values():
        item_groups[item.type][item.element].append(item)

    for element_dict in item_groups.values():
        for item_list in element_dict.values():
            item_list.sort(key=lambda item: item.name)

    return {
        type_: {
            element: [
                SelectOption(
                    label=item.name, value=str(item.id), emoji=ASSETS.elements[item.element].emoji
                )
                for item in items
            ]
            for element, items in element_dict.items()
        }
        for type_, element_dict in item_groups.items()
    }


def make_empty_option(locale: Locale, /) -> SelectOption:
    return SelectOption(
        label=i18n.get_message(locale, "ui-empty-option-label"),
        description=i18n.get_message(locale, "ui-empty-option-desc"),
        value="$empty",
        emoji="⏏",
    )


class MechView:
    store: ComponentStore
    mech: Mech
    pack: ItemPack
    player: Player
    embed: Embed
    locale: Locale
    paginator: Paginator[abc.Sequence[abc.Sequence[ui.MessageUIComponent]]]
    active: ToggleButton | None
    empty_option: SelectOption
    mech_config: str

    command_mention: typing.ClassVar[str] = "`/buffs`"

    # pages of rows of components
    LAYOUT: abc.Sequence[abc.Sequence[abc.Sequence[str]]] = (
        (
            ( "TOP_WEAPON:0", "DRONE",  "TOP_WEAPON:1", "CHARGE"),
            ("SIDE_WEAPON:2", "TORSO", "SIDE_WEAPON:3", "TELEPORTER"),
            ("SIDE_WEAPON:0", "LEGS",  "SIDE_WEAPON:1", "HOOK"),
        ),
        (
            tuple(f"MODULE:{n}" for n in range(0, 4)),  # noqa: PIE808
            tuple(f"MODULE:{n}" for n in range(4, 8)),
        ),
    )  # fmt: skip
    DUMMY_BUTTONS = tuple(
        ActionButton(label=SPACE, disabled=True, custom_id=f"$dummy{n}") for n in range(4)
    )
    PAGE_EMOJI = (ASSETS.types[Type.MODULE].emoji, ASSETS.types[Type.TORSO].emoji)

    def __init__(
        self,
        store: ComponentStore,
        build: MechBuild,
        pack: ItemPack,
        # renderer: PackRenderer,
        player: Player,
        locale: Locale,
    ) -> None:
        self.store = store
        self.mech = build.mech
        self.pack = pack
        self.renderer: typing.Any = object()  # TODO
        self.player = player
        self.embed = embed_mech(build.mech, locale, build.name)
        self.locale = locale
        self.active = None
        self.empty_option = make_empty_option(locale)
        self.mech_config = get_mech_config(build.mech)
        self.init_pages(store)
        self.item_groups = group_items(pack)

    def init_pages(self, store: ComponentStore) -> None:  # noqa: PLR0915
        gettext = i18n.get_gettext(self.locale)

        @store.bind(ActionButton(emoji=self.PAGE_EMOJI[0], custom_id=store.make_id()))
        async def modules_button(inter: MessageInteraction) -> None:
            """Button swapping mech editor with modules and vice versa."""
            self.paginator.index ^= 1  # toggle between 0 and 1
            modules_button.emoji = self.PAGE_EMOJI[self.paginator.index]
            await inter.response.edit_message(components=self.paginator.page)

        @store.bind(ToggleButton(label="🡅", custom_id=store.make_id()))
        async def buffs_button(inter: MessageInteraction) -> None:
            """Button toggling arena buffs being applied to mech's stats."""
            if is_shop_empty(self.player.arena_shop):
                return await inter.response.send_message(
                    gettext("mech-build-no-buffs", command_mention=self.command_mention),
                    ephemeral=True,
                )

            buffs_button.toggle()
            assert self.embed._fields is not None  # pyright: ignore[reportPrivateUsage]
            self.embed._fields[0]["value"] = format_summary(  # pyright: ignore[reportPrivateUsage]
                self.mech, self.locale, self.player.arena_shop if buffs_button.on else None
            )
            await inter.response.edit_message(embed=self.embed, components=self.paginator.page)

        @store.bind(
            ActionButton(label=gettext("ui-quit"), style=ButtonStyle.red, custom_id=store.make_id())
        )
        async def quit_button(inter: MessageInteraction) -> None:
            store.stop()
            await inter.response.defer(ephemeral=True)

        @store.bind(
            PaginatedSelect(
                up=SelectOption(
                    label=gettext("mech-build-ui-select-up-label"),
                    value="$up",
                    emoji="🔺",
                    description=gettext("mech-build-ui-select-up-desc"),
                ),
                down=SelectOption(
                    label=gettext("mech-build-ui-select-down-label"),
                    value="$down",
                    emoji="🔻",
                    description=gettext("mech-build-ui-select-down-desc"),
                ),
                placeholder=gettext("mech-build-ui-select-placeholder"),
                all_options=[SelectOption(label="$")],  # 1 option required even when disabled
                disabled=True,
                custom_id=store.make_id(),
            )
        )
        async def select(inter: MessageInteraction) -> None:
            """Item select dropdown."""
            assert self.active is not None
            assert inter.values is not None
            value = inter.values[0]

            if select.update_on_own_option(value):
                return await inter.response.edit_message(components=self.paginator.page)

            slot = slot_to_type(store.strip_id(self.active).split(":"))

            if value == self.empty_option.value:
                item = None
                select.placeholder = None
                self.active.style_off = ButtonStyle.gray

            else:
                item_data = self.pack.get_item(ItemID(int(value)))
                target_type = slot[0] if isinstance(slot, tuple) else slot

                if item_data.type is not target_type:
                    # challenge complete: How Did We Get Here?
                    msg = f"{item_data.type} is not valid for slot {target_type}"
                    raise RuntimeWarning(msg)

                item = Item.maxed(item_data)
                select.placeholder = item_data.name
                self.active.style_off = ButtonStyle.green

            self.mech[slot] = item
            self.embed.color = color_from_mech(self.mech)
            self.set_state_idle()

            self.embed.set_field_at(
                0,
                name="Stats:",
                value=format_summary(
                    self.mech,
                    self.locale,
                    self.player.arena_shop if buffs_button.on else None,
                ),
            )
            new_config = get_mech_config(self.mech)

            if new_config == self.mech_config:
                return await inter.response.edit_message(
                    embed=self.embed, components=self.paginator.page
                )

            self.mech_config = new_config
            url, file = None, MISSING

            if False:
                if self.mech.torso is not None:
                    image = self.renderer.create_mech_image(self.mech)
                    url, file = embed_image(image, new_config)

            self.embed.set_image(url)

            if __debug__:
                debug_footer(self.embed, replace=True)

            await inter.response.edit_message(
                embed=self.embed, file=file, components=self.paginator.page, attachments=[]
            )

        self.select = select
        self.paginator = Paginator(
            (
                [
                    [*map(self.make_button, self.LAYOUT[0][0]), modules_button],
                    [*map(self.make_button, self.LAYOUT[0][1]), buffs_button],
                    [*map(self.make_button, self.LAYOUT[0][2]), quit_button],
                    [select],
                ],
                [
                    [*map(self.make_button, self.LAYOUT[1][0]), modules_button],
                    [*map(self.make_button, self.LAYOUT[1][1]), buffs_button],
                    [*self.DUMMY_BUTTONS, quit_button],
                    [select],
                ],
            )
        )

    def set_state_idle(self) -> None:
        if self.active is not None:
            self.active.on = False
            self.active = None
        self.select.disabled = True

    def set_state_active(self, button: ToggleButton, /) -> None:
        button.on = True
        self.active = button
        self.select.disabled = False
        self.update_dropdown(button)

    def switch_active_button(self, button: ToggleButton, /) -> None:
        assert self.active is not None
        self.active.on = False
        button.on = True
        self.active = button
        self.update_dropdown(button)

    def update_dropdown(self, button: ToggleButton, /) -> None:
        metadata = self.store.strip_id(button).split(":")
        options = self.item_groups[Type.of_name(metadata[0])]
        element = dominant_element(self.mech)
        self.select.all_options = [self.empty_option, *sorted_options(options, element)]
        slot = slot_to_type(metadata)
        item = self.mech[slot]
        self.select.placeholder = self.empty_option.label if item is None else item.name

    def make_button(self, slot: str, /) -> ToggleButton:
        sm_slot = slot_to_type(slot)
        btn = ToggleButton(
            style_off=(ButtonStyle.gray if self.mech[sm_slot] is None else ButtonStyle.green),
            style_on=ButtonStyle.blurple,
            emoji=slot_emoji(sm_slot),
            custom_id=self.store.make_id(slot),
        )
        self.store.bind(btn)(partial(self.slot_button_cb, btn))
        return btn

    async def slot_button_cb(self, button: ToggleButton, inter: MessageInteraction) -> None:
        """Callback shared by all of the item slot buttons."""
        if button.on:
            self.set_state_idle()

        elif self.active is not None:
            self.switch_active_button(button)

        else:
            self.set_state_active(button)

        await inter.response.edit_message(components=self.paginator.page)
