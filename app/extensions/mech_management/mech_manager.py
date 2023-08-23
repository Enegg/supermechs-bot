import typing as t

from disnake import ButtonStyle, Embed, MessageInteraction, SelectOption
from disnake.utils import MISSING

from assets import ELEMENT_ASSETS, SIDED_TYPE_ASSETS, TYPE_ASSETS, get_weight_emoji
from library_extensions import INVISIBLE_CHARACTER, OPTION_LIMIT, embed_image, embed_to_footer
from library_extensions.ui import (
    EMPTY_OPTION,
    ActionRow,
    Button,
    MessageUIComponent,
    PaginatedSelect,
    PaginatorView,
    SaneView,
    ToggleButton,
    TrinaryButton,
    add_callback,
    button,
    invoker_bound,
    positioned,
    select,
)

from supermechs.api import STATS, ArenaBuffs, Element, InvItem, Item, ItemPack, Mech, Player, Type
from supermechs.converters import slot_to_type
from supermechs.rendering import PackRenderer


def embed_mech(mech: Mech, included_buffs: ArenaBuffs | None = None) -> Embed:
    embed = Embed(
        title=f'Mech build "{mech.name}"',
        color=ELEMENT_ASSETS[mech.dominant_element or Element.UNKNOWN].color,
    ).add_field("Stats:", format_stats(mech, included_buffs))
    return embed


def get_mech_config(mech: Mech) -> str:
    """Returns a str of item IDs that are visible on image."""
    return "_".join(
        "0" if inv_item is None else str(inv_item.item.data.id)
        for inv_item in mech.iter_items(body=True, weapons=True)
    )


def get_weight_usage(mech: Mech, weight: int) -> str:
    return " " + get_weight_emoji(weight)


def format_stats(
    mech: Mech,
    included_buffs: ArenaBuffs | None = None,
    /,
    *,
    extra: t.Mapping[str, t.Callable[[Mech, int], t.Any]] = {"weight": get_weight_usage},
) -> str:
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

    def default_extra(mech: Mech, value: int) -> t.Any:
        return ""

    return "\n".join(
        "{stat.emoji} **{value}** {stat.name}{extra}".format(
            value=value,
            stat=STATS[stat_name],
            extra=extra.get(stat_name, default_extra)(mech, value),
        )
        for stat_name, value in bank.items()
    )


def slot_to_emoji(slot: str, /) -> str:
    type = slot_to_type(slot)

    if type is Type.SIDE_WEAPON or type is Type.TOP_WEAPON:
        asset = SIDED_TYPE_ASSETS[type]
        return (asset.left if int(slot[-1]) % 2 else asset.right).emoji

    return TYPE_ASSETS[type].emoji


def get_sorted_options(
    options: list[SelectOption], primary_element: Element | None, /
) -> list[SelectOption]:
    """Returns a list of `SelectOption`s sorted by element.

    Note: this deliberately does not respect the option limit.
    """
    new_options = [EMPTY_OPTION]

    if len(options) + 1 <= OPTION_LIMIT:
        return new_options + options

    element_emojis = [element.emoji for element in ELEMENT_ASSETS.values()]

    if primary_element is not None and primary_element is not Element.PHYSICAL:
        # physical is the first one anyway
        primary_emoji = ELEMENT_ASSETS[primary_element].emoji
        element_emojis.remove(primary_emoji)
        element_emojis.insert(0, primary_emoji)

    new_options += sorted(options, key=lambda o: (element_emojis.index(str(o.emoji)), o.label))

    return new_options


@invoker_bound
class MechView(PaginatorView):
    """View for button-based mech building."""

    buffs_command: t.ClassVar[str]
    user_id: int

    def __init__(
        self,
        mech: Mech,
        pack: ItemPack,
        renderer: PackRenderer,
        player: Player,
        *,
        timeout: float = 180.0,
    ) -> None:
        super().__init__(timeout=timeout, columns=5)
        self.pack = pack
        self.mech = mech
        self.player = player
        self.renderer = renderer
        self.user_id = player.id
        self.mech_config = get_mech_config(mech)

        self.active: TrinaryButton[str] | None = None
        self.embed = embed_mech(mech)

        for pos, row in enumerate(
            (
                ("top1", "drone", "top2", "charge", "mod1", "mod2", "mod3", "mod4"),
                ("side3", "torso", "side4", "tele", "mod5", "mod6", "mod7", "mod8"),
                ("side1", "legs", "side2", "hook"),
            )
        ):
            self.rows[pos].extend_page_items(
                add_callback(
                    TrinaryButton(
                        custom_id=f"{self.id}:{slot}",
                        item=None if (item := mech[slot]) is None else item.name,  # TODO
                        emoji=slot_to_emoji(slot),
                    ),
                    self.slot_button_cb,
                )
                for slot in row
            )

        self.rows[2].extend_page_items(
            Button(label=INVISIBLE_CHARACTER, custom_id=f"{self.id}:no_op{i}", disabled=True, row=2)
            for i in range(4)
        )

        # property updates the rows
        self.page = 0

        self.item_groups: dict[Type, list[SelectOption]] = {type: [] for type in Type}

        for item in pack.items.values():
            self.item_groups[item.type].append(
                SelectOption(label=item.name, emoji=ELEMENT_ASSETS[item.element].emoji)
            )

        ref = {ELEMENT_ASSETS[element].emoji: index for index, element in enumerate(Element)}

        for item_list in self.item_groups.values():
            item_list.sort(key=lambda option: (ref[str(option.emoji)], option.label))

    async def slot_button_cb(self, button: TrinaryButton[str], inter: MessageInteraction) -> None:
        """Callback shared by all of the item slot buttons."""
        if button.on:
            self.set_state_idle()

        elif self.active is not None:
            self.switch_active_button(button)

        else:
            self.set_state_pressed(button)

        await inter.response.edit_message(view=self)

    @positioned(0, 4)
    @button(emoji=TYPE_ASSETS[Type.MODULE].emoji, custom_id="button:modules")
    async def modules_button(self, button: Button[None], inter: MessageInteraction) -> None:
        """Button swapping mech editor with modules and vice versa."""
        self.page ^= 1  # toggle between 0 and 1
        TYPE_ASSETS[Type.TORSO].emoji
        button.emoji = TYPE_ASSETS[Type.TORSO if self.page == 1 else Type.MODULE].emoji

        await inter.response.edit_message(view=self)

    @positioned(1, 4)
    @button(cls=ToggleButton, label="Buffs", custom_id="button:buffs")
    async def buffs_button(self, button: ToggleButton, inter: MessageInteraction) -> None:
        """Button toggling arena buffs being applied to mech's stats."""
        if self.player.arena_buffs.is_at_zero():
            return await inter.response.send_message(
                "This won't show any effect because all your buffs are at level zero.\n"
                f"You can change that using {self.buffs_command} command.",
                ephemeral=True,
            )

        button.toggle()
        assert self.embed._fields is not None
        self.embed.set_field_at(
            0,
            name=self.embed.fields[0].name,
            value=format_stats(self.mech, self.player.arena_buffs if button.on else None),
        )

        await inter.response.edit_message(embed=self.embed, view=self)

    @positioned(2, 4)
    @button(label="Quit", style=ButtonStyle.red)
    async def quit_button(self, button: Button[None], inter: MessageInteraction) -> None:
        del button
        await inter.response.defer(ephemeral=True)
        self.stop()

    @positioned(3, 0)
    @select(
        cls=PaginatedSelect,
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
        custom_id="select:item",
        all_options=[EMPTY_OPTION],
        disabled=True,
    )
    async def item_select(self, select: PaginatedSelect, inter: MessageInteraction) -> None:
        """Dropdown menu with all the items."""
        assert self.active is not None
        (value,) = select.values

        if select.update_page_if_own_option(value):
            return await inter.response.edit_message(view=self)

        item_name = None if value == EMPTY_OPTION.value else value

        item_data = None if item_name is None else self.pack.get_item_by_name(item_name)
        slot = self.active.custom_id.split(":")[-1]

        # sanity check if the item is actually valid
        if item_data is not None and item_data.type is not slot_to_type(slot):
            raise RuntimeWarning(f"{item_data.type} is not valid for slot {slot}")

        self.active.item = select.placeholder = item_name

        if item_data is not None:
            item = InvItem.from_item(Item.from_data(item_data, maxed=True))

        else:
            item = None

        self.mech[slot] = item

        self.update_embed_color()
        self.set_state_idle()

        self.embed.set_field_at(
            0,
            name="Stats:",
            value=format_stats(self.mech, self.player.arena_buffs if self.buffs_button.on else None)
        )
        new_config = get_mech_config(self.mech)

        if new_config == self.mech_config:
            return await inter.response.edit_message(embed=self.embed, view=self)

        self.mech_config = new_config
        file = MISSING
        url = None

        if self.mech.torso is not None:
            image = self.renderer.create_mech_image(self.mech)
            url, file = embed_image(image, new_config + ".png")

        self.embed.set_image(url)

        if __debug__:
            embed_to_footer(self.embed)

        await inter.response.edit_message(embed=self.embed, file=file, view=self, attachments=[])

    def set_state_idle(self) -> None:
        if self.active is not None:
            self.active.on = False
            self.active = None
        self.item_select.disabled = True

    def set_state_pressed(self, button: TrinaryButton[str], /) -> None:
        button.on = True
        self.active = button
        self.item_select.disabled = False
        self.update_dropdown(button)

    def switch_active_button(self, button: TrinaryButton[str], /) -> None:
        assert self.active is not None
        self.active.on = False
        button.on = True
        self.active = button
        self.update_dropdown(button)

    def update_dropdown(self, button: TrinaryButton[str], /) -> None:
        options = self.item_groups[slot_to_type(button.custom_id.split(":")[-1])]
        self.item_select.all_options = get_sorted_options(options, self.mech.dominant_element)
        self.item_select.placeholder = "empty" if button.item is None else button.item

    def update_embed_color(self) -> None:
        if (dominant := self.mech.dominant_element) is not None:
            self.embed.color = ELEMENT_ASSETS[dominant].color

        elif self.mech.torso is not None:
            self.embed.color = ELEMENT_ASSETS[self.mech.torso.item.data.element].color

        else:
            self.embed.color = ELEMENT_ASSETS[Element.UNKNOWN].color


@invoker_bound
class DetailedBrowseView(SaneView[ActionRow[MessageUIComponent]]):
    def __init__(self, player: Player, *, timeout: float = 180.0) -> None:
        super().__init__(timeout=timeout)
        self.player = player
        self.user_id = player.id
        self.page = 0
        self.embed = embed_mech(next(iter(player.builds.values())), player.arena_buffs)

    @positioned(0, 0)
    @button(label="🡸", custom_id="button:prev", disabled=True)
    async def prev_button(self, button: Button[None], inter: MessageInteraction) -> None:
        self.page -= 1
        self.next_button.disabled = False

        if self.page == 0:
            button.disabled = True

        await inter.response.edit_message(view=self)

    @positioned(0, 1)
    @button(label="🡺", custom_id="button:next")
    async def next_button(self, button: Button[None], inter: MessageInteraction) -> None:
        self.page += 1
        self.prev_button.disabled = False

        # condition for max page
        if False:
            button.disabled = True

        await inter.response.edit_message(view=self)
