from __future__ import annotations

from disnake import ButtonStyle, Embed, File, MessageInteraction, SelectOption
from disnake.app_commands import APIApplicationCommand
from disnake.utils import MISSING

from abstract.files import Bytes
from library_extensions.ui import (
    EMPTY_OPTION,
    ActionRow,
    Button,
    InteractionCheck,
    MessageUIComponent,
    PaginatedSelect,
    PaginatorView,
    SaneView,
    ToggleButton,
    TrinaryButton,
    add_callback,
    button,
    positioned,
    select,
)

from SuperMechs.api import ArenaBuffs, Element, InvItem, ItemPack, Mech, Player, Type
from SuperMechs.converters import slot_to_icon_data, slot_to_type
from SuperMechs.ext.wu_compat import mech_to_id_str
from SuperMechs.rendering import PackRenderer


def embed_mech(mech: Mech, included_buffs: ArenaBuffs | None = None) -> Embed:
    embed = Embed(
        title=f'Mech build "{mech.name}"', color=(mech.dominant_element or Element.UNKNOWN).color
    ).add_field("Stats:", mech.print_stats(included_buffs))
    return embed


class MechView(InteractionCheck, PaginatorView):
    """Class implementing View for a button-based mech building."""

    def __init__(
        self,
        mech: Mech,
        pack: ItemPack,
        renderer: PackRenderer,
        player: Player,
        buffs_command: APIApplicationCommand,
        *,
        timeout: float = 180.0,
    ) -> None:
        super().__init__(timeout=timeout, columns=5)
        self.pack = pack
        self.mech = mech
        self.player = player
        self.renderer = renderer
        self.buffs_command = buffs_command
        self.user_id = player.id

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
                        custom_id=id,
                        item=None if (item := mech[id]) is None else item.name,
                        emoji=slot_to_icon_data(id).emoji,
                    ),
                    self.slot_button_cb,
                )
                for id in row
            )

        self.rows[2].extend_page_items(
            Button(label="⠀", custom_id=f"button:no_op{i}", disabled=True, row=2) for i in range(4)
        )

        # property updates the rows
        self.page = 0

        self.item_groups: dict[Type, list[SelectOption]] = {type: [] for type in Type}

        for item in pack.items.values():
            self.item_groups[item.type].append(
                SelectOption(label=item.name, emoji=item.element.emoji)
            )

        ref = {element.emoji: index for index, element in enumerate(Element)}

        for item_list in self.item_groups.values():
            item_list.sort(key=lambda option: (ref[str(option.emoji)], option.label))

    async def slot_button_cb(self, button: TrinaryButton[str], inter: MessageInteraction) -> None:
        """Callback shared by all of the item slot buttons."""
        if button.on:
            self.set_state_idle()

        elif self.active is not None:
            self.set_state_switched(button)

        else:
            self.set_state_pressed(button)

        await inter.response.edit_message(view=self)

    @positioned(0, 4)
    @button(emoji=Type.MODULE.emoji, custom_id="button:modules")
    async def modules_button(self, button: Button[None], inter: MessageInteraction) -> None:
        """Button swapping mech editor with modules and vice versa."""
        self.page ^= 1  # toggle between 0 and 1
        button.emoji = Type.TORSO.emoji if self.page == 1 else Type.MODULE.emoji

        await inter.response.edit_message(view=self)

    @positioned(1, 4)
    @button(cls=ToggleButton, label="Buffs", custom_id="button:buffs")
    async def buffs_button(self, button: ToggleButton, inter: MessageInteraction) -> None:
        """Button toggling arena buffs being applied to mech's stats."""
        if self.player.arena_buffs.is_at_zero():
            command_mention = "</{0.name}:{0.id}>".format(self.buffs_command)
            return await inter.response.send_message(
                "This won't show any effect because all your buffs are at level zero.\n"
                f"You can change that using {command_mention} command.",
                ephemeral=True,
            )

        button.toggle()
        assert self.embed._fields is not None
        self.embed.set_field_at(
            0,
            name=self.embed.fields[0].name,
            value=self.mech.print_stats(self.player.arena_buffs if button.on else None),
        )

        await inter.response.edit_message(embed=self.embed, view=self)

    @positioned(2, 4)
    @button(label="Quit", custom_id="button:quit", style=ButtonStyle.red)
    async def quit_button(self, button: Button[None], inter: MessageInteraction) -> None:
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

        if select.check_option(value):
            return await inter.response.edit_message(view=self)

        item_name = None if value == EMPTY_OPTION.value else value

        item = None if item_name is None else self.pack.get_item_by_name(item_name)

        # sanity check if the item is actually valid
        if item is not None and item.type is not slot_to_type(self.active.custom_id):
            raise RuntimeWarning(f"{item.type} is not valid for slot {self.active.custom_id}")

        self.active.item = select.placeholder = item_name

        if item is not None:
            item = InvItem.from_item(item, maxed=True)

        self.mech[self.active.custom_id] = item

        self.update_color(item is None)
        self.set_state_idle()

        self.embed.set_field_at(
            0,
            name="Stats:",
            value=self.mech.print_stats(self.player.arena_buffs if self.buffs_button.on else None),
        )

        if "TODO: condition_for_cached_image":
            return await inter.response.edit_message(embed=self.embed, view=self)

        file = MISSING
        url = None

        if self.mech.torso is not None:
            image = self.renderer.get_mech_image(self.mech)
            resource = Bytes.from_image(image, mech_to_id_str(self.mech) + ".png")
            file = File(resource.fp, resource.filename)
            url = resource.url

        await inter.response.edit_message(
            embed=self.embed.set_image(url), file=file, view=self, attachments=[]
        )

    def sorted_options(self, options: list[SelectOption]) -> list[SelectOption]:
        """Returns a list of `SelectOption`s sorted by element."""
        new_options = [EMPTY_OPTION]

        if len(options) <= 24:
            return new_options + options

        if (dominant := self.mech.dominant_element) is not None:
            element_to_index = {element.emoji: index for index, element in enumerate(Element, 1)}
            element_to_index[dominant.emoji] = 0

        else:
            element_to_index = {element.emoji: index for index, element in enumerate(Element)}

        new_options += sorted(options, key=lambda o: (element_to_index[str(o.emoji)], o.label))

        return new_options

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

    def set_state_switched(self, button: TrinaryButton[str], /) -> None:
        assert self.active is not None
        self.active.toggle()
        button.on = True
        self.active = button
        self.update_dropdown(button)

    def update_dropdown(self, button: TrinaryButton[str], /) -> None:
        options = self.item_groups[slot_to_type(button.custom_id)]
        self.item_select.all_options = self.sorted_options(options)
        self.item_select.placeholder = "empty" if button.item is None else button.item

    def update_color(self, item_not_set: bool) -> None:
        assert self.active is not None
        if (dominant := self.mech.dominant_element) is not None:
            self.embed.color = dominant.color

        elif self.mech.torso is not None:
            self.embed.color = self.mech.torso.element.color

        elif self.active.custom_id == "torso" and item_not_set:
            self.embed.color = Element.UNKNOWN.color


class BrowseView(InteractionCheck, SaneView[ActionRow[MessageUIComponent]]):
    """View"""

    pass


class DetailedBrowseView(InteractionCheck, SaneView[ActionRow[MessageUIComponent]]):
    def __init__(self, player: Player, *, timeout: float = 180.0) -> None:
        super().__init__(timeout=timeout)
        self.player = player
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
