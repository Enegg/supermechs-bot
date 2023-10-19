import typing as t

from disnake import ButtonStyle, Embed, Locale, MessageInteraction, SelectOption
from disnake.ui import Button, button, string_select
from disnake.utils import MISSING

import i18n
from assets import ELEMENT, SIDED_TYPE, STAT, TYPE, get_weight_emoji
from library_extensions import OPTION_LIMIT, SPACE, ColorType, debug_footer, embed_image
from library_extensions.ui import (
    EMPTY_OPTION,
    PaginatedSelect,
    PaginatorView,
    ToggleButton,
    TrinaryButton,
    add_callback,
    invoker_bound,
    metadata_of,
    positioned,
)

from supermechs.api import ArenaBuffs, Item, ItemPack, Mech, Player, Stat
from supermechs.models.item import Element, Type
from supermechs.rendering import PackRenderer


def embed_mech(mech: Mech, locale: Locale, included_buffs: ArenaBuffs | None = None) -> Embed:
    embed = Embed(
        title=f'Mech build "{mech.name}"',
        color=ELEMENT[mech.dominant_element or Element.UNKNOWN].color,
    ).add_field("Summary:", format_stats(mech, locale, included_buffs))
    return embed


def get_mech_config(mech: Mech, /) -> str:
    """Returns a str of item IDs that are visible on image."""
    return "_".join(
        "0" if item is None else str(item.data.id) for item in mech.iter_items("body", "weapons")
    )


def get_weight_usage(weight: int, /) -> str:
    return " " + get_weight_emoji(weight)


def format_stats(mech: Mech, locale: Locale, included_buffs: ArenaBuffs | None = None, /) -> str:
    """Returns a string of lines formatted with mech stats.

    Parameters
    ----------
    mech: `Mech` object which stats to format.
    included_buffs: `ArenaBuffs` object to apply buffs from.
    """
    if included_buffs is None:
        bank = mech.stat_summary

    else:
        bank = included_buffs.buff_stats(mech.stat_summary, buff_health=True)

    return "\n".join(
        "{stat_emoji} **{value}** {stat_name}{extra}".format(  # TODO: stat names
            value=value,
            stat_name=i18n.get(locale, stat_key).default,
            stat_emoji=STAT[stat_key],
            extra=get_weight_usage(value) if stat_key is Stat.weight else "",
        )
        for stat_key, value in bank.items()
    )


def slot_to_emoji(slot: Mech.Slot, /) -> str:
    if slot.type is Type.SIDE_WEAPON or slot.type is Type.TOP_WEAPON:
        asset = SIDED_TYPE[slot.type]
        return (asset.left if int(slot.name[-1]) % 2 else asset.right).emoji

    return TYPE[slot.type].emoji


def get_sorted_options(
    options: list[SelectOption], primary_element: Element | None, /
) -> list[SelectOption]:
    """Returns a list of `SelectOption`s sorted by element.

    Note: this ignores the option limit.
    """
    new_options = [EMPTY_OPTION]

    if len(options) + 1 <= OPTION_LIMIT:
        return new_options + options

    element_emojis = [element.emoji for element in ELEMENT.values()]

    if primary_element is not None and primary_element is not Element.PHYSICAL:
        # physical is the first one anyway
        primary_emoji = ELEMENT[primary_element].emoji
        element_emojis.remove(primary_emoji)
        element_emojis.insert(0, primary_emoji)

    new_options += sorted(options, key=lambda o: (element_emojis.index(str(o.emoji)), o.label))

    return new_options


def color_from_mech(mech: Mech, /) -> ColorType:
    if (dominant := mech.dominant_element) is not None:
        return ELEMENT[dominant].color

    if mech.torso is not None:
        return ELEMENT[mech.torso.data.element].color

    return ELEMENT[Element.UNKNOWN].color


@invoker_bound
class MechView(PaginatorView):
    """View for button-based mech building."""

    # fmt: off
    LAYOUT = (
        (
            Mech.Slot.TOP_WEAPON_1, Mech.Slot.DRONE, Mech.Slot.TOP_WEAPON_2, Mech.Slot.CHARGE,
            Mech.Slot.MODULE_1, Mech.Slot.MODULE_2, Mech.Slot.MODULE_3, Mech.Slot.MODULE_4
        ),
        (
            Mech.Slot.SIDE_WEAPON_3, Mech.Slot.TORSO, Mech.Slot.SIDE_WEAPON_4, Mech.Slot.TELEPORTER,
            Mech.Slot.MODULE_5, Mech.Slot.MODULE_6, Mech.Slot.MODULE_7, Mech.Slot.MODULE_8
        ),
        (Mech.Slot.SIDE_WEAPON_1, Mech.Slot.LEGS, Mech.Slot.SIDE_WEAPON_2, Mech.Slot.HOOK),
    )
    # fmt: on

    buffs_command: t.ClassVar[str]
    user_id: int

    def __init__(
        self,
        mech: Mech,
        pack: ItemPack,
        renderer: PackRenderer,
        player: Player,
        locale: Locale,
        *,
        timeout: float = 180.0,
    ) -> None:
        super().__init__(timeout=timeout, columns=5)
        self.mech = mech
        self.locale = locale
        self.arena_buffs = player.arena_buffs
        self.renderer = renderer
        self.user_id = player.id
        self.get_item = pack.get_item_by_id
        self.mech_config = get_mech_config(mech)

        self.active: TrinaryButton[str] | None = None
        self.embed = embed_mech(mech, locale)

        for pos, row in enumerate(self.LAYOUT):
            self.rows[pos].extend_page_items(
                add_callback(
                    TrinaryButton(
                        custom_id=f"{self.id}:{slot.name}",
                        item=TrinaryButton.NOTSET
                        if (item := mech[slot]) is None
                        else item.data.name,
                        emoji=slot_to_emoji(slot),
                    ),
                    self.slot_button_cb,
                )
                for slot in row
            )

        self.rows[2].extend_page_items(
            Button(label=SPACE, custom_id=f"{self.id}:no_op{i}", disabled=True, row=2)
            for i in range(4)
        )

        # property updates the rows
        self.page = 0
        self.item_groups: dict[Type, list[SelectOption]] = {type: [] for type in Type}

        for item in pack.items.values():
            self.item_groups[item.type].append(
                SelectOption(label=item.name, value=str(item.id), emoji=ELEMENT[item.element].emoji)
            )

        ref = {ELEMENT[element].emoji: index for index, element in enumerate(Element)}

        for item_list in self.item_groups.values():
            item_list.sort(key=lambda option: (ref[str(option.emoji)], option.label))

    async def slot_button_cb(self, button: TrinaryButton[str], inter: MessageInteraction) -> None:
        """Callback shared by all of the item slot buttons."""
        if button.on:
            self.set_state_idle()

        elif self.active is not None:
            self.switch_active_button(button)

        else:
            self.set_state_active(button)

        await inter.response.edit_message(view=self)

    @positioned(0, 4)
    @button(emoji=TYPE[Type.MODULE].emoji)
    async def modules_button(self, button: Button[None], inter: MessageInteraction) -> None:
        """Button swapping mech editor with modules and vice versa."""
        self.page ^= 1  # toggle between 0 and 1
        button.emoji = TYPE[Type.TORSO if self.page == 1 else Type.MODULE].emoji

        await inter.response.edit_message(view=self)

    @positioned(1, 4)
    @button(ToggleButton, label="Buffs")
    async def buffs_button(self, button: ToggleButton, inter: MessageInteraction) -> None:
        """Button toggling arena buffs being applied to mech's stats."""
        if self.arena_buffs.is_at_zero():
            return await inter.response.send_message(
                "This won't show any effect because all your buffs are at level zero.\n"
                f"You can change that using {self.buffs_command} command.",
                ephemeral=True,
            )

        button.toggle()
        assert self.embed._fields is not None
        self.embed._fields[0]["value"] = format_stats(
            self.mech, self.locale, self.arena_buffs if button.on else None
        )
        await inter.response.edit_message(embed=self.embed, view=self)

    @positioned(2, 4)
    @button(label="Quit", style=ButtonStyle.red)
    async def quit_button(self, button: Button[None], inter: MessageInteraction) -> None:
        del button
        await inter.response.defer(ephemeral=True)
        self.stop()

    @positioned(3, 0)
    @string_select(
        PaginatedSelect,
        up=SelectOption(
            label="Previous items",
            value="option:up",
            emoji="🔼",
            description="Click to show previous items",
        ),
        down=SelectOption(
            label="More items",
            value="option:down",
            emoji="🔽",
            description="Click to show more items",
        ),
        placeholder="Choose slot",
        all_options=[EMPTY_OPTION],
        disabled=True,
    )
    async def select(self, select: PaginatedSelect, inter: MessageInteraction) -> None:
        """Dropdown menu with all the items."""
        assert self.active is not None
        assert inter.values is not None
        value = inter.values[0]

        if page := select.is_own_option(value):
            select.page += page
            return await inter.response.edit_message(view=self)

        item_data = None if value == EMPTY_OPTION.value else self.get_item(int(value))
        slot = Mech.Slot.of_name(metadata_of(self.active)[0])

        if item_data is not None:
            if item_data.type is not slot.type:
                # how did we get here?
                raise RuntimeWarning(f"{item_data.type} is not valid for slot {slot}")

            item = Item.from_data(item_data, maxed=True)
            await self.renderer.get_item_sprite(item).load()
            self.active.item = select.placeholder = item_data.name

        else:
            item = None
            select.placeholder = None
            self.active.item = TrinaryButton.NOTSET

        self.mech[slot] = item
        self.embed.color = color_from_mech(self.mech)
        self.set_state_idle()

        self.embed.set_field_at(
            0,
            name="Stats:",
            value=format_stats(
                self.mech,
                self.locale,
                self.arena_buffs if self.buffs_button.on else None,
            ),
        )
        new_config = get_mech_config(self.mech)

        if new_config == self.mech_config:
            return await inter.response.edit_message(embed=self.embed, view=self)

        self.mech_config = new_config
        url, file = None, MISSING

        if self.mech.torso is not None:
            image = self.renderer.create_mech_image(self.mech)
            url, file = embed_image(image, new_config)

        self.embed.set_image(url)

        if __debug__:
            debug_footer(self.embed)

        await inter.response.edit_message(embed=self.embed, file=file, view=self, attachments=[])

    def set_state_idle(self) -> None:
        if self.active is not None:
            self.active.on = False
            self.active = None
        self.select.disabled = True

    def set_state_active(self, button: TrinaryButton[str], /) -> None:
        button.on = True
        self.active = button
        self.select.disabled = False
        self.update_dropdown(button)

    def switch_active_button(self, button: TrinaryButton[str], /) -> None:
        assert self.active is not None
        self.active.on = False
        button.on = True
        self.active = button
        self.update_dropdown(button)

    def update_dropdown(self, button: TrinaryButton[str], /) -> None:
        options = self.item_groups[Mech.Slot.of_name(metadata_of(button)[0]).type]
        self.select.all_options = get_sorted_options(options, self.mech.dominant_element)
        self.select.placeholder = (
            EMPTY_OPTION.label if button.item is TrinaryButton.NOTSET else button.item
        )
