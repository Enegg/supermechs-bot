from __future__ import annotations

import asyncio
import json
import logging
import typing as t

from disnake import (
    Attachment,
    ButtonStyle,
    CommandInteraction,
    Embed,
    File,
    Message,
    MessageInteraction,
    SelectOption,
)
from disnake.ext import commands, plugins
from disnake.utils import MISSING

from library_extensions import DesyncError, image_to_file
from ui.action_row import ActionRow, MessageUIComponent
from ui.buttons import Button, ToggleButton, TrinaryButton, button
from ui.item import add_callback
from ui.selects import EMPTY_OPTION, PaginatedSelect, Select, select
from ui.views import InteractionCheck, PaginatorView, SaneView, positioned

from SuperMechs.core import STATS, ArenaBuffs
from SuperMechs.enums import Element, Type
from SuperMechs.ext.wu_compat import dump_mechs, load_mechs, mech_to_id_str
from SuperMechs.inv_item import InvItem
from SuperMechs.mech import Mech, slot_to_icon_data, slot_to_type
from SuperMechs.pack_interface import PackInterface
from SuperMechs.player import Player
from SuperMechs.utils import truncate_name

if t.TYPE_CHECKING:
    from bot import SMBot

MixedInteraction = CommandInteraction | MessageInteraction
T = t.TypeVar("T")
LOGGER = logging.getLogger(__name__)
plugin = plugins.Plugin["SMBot"](name="Mech-manager")

# we need to hardcode it as bot.get_global_command_named fails in testing
# due to the command being registered in test guilds only
BUFFS_COMMAND_ID = 919329829227229196


def embed_mech(mech: Mech, included_buffs: ArenaBuffs | None = None) -> Embed:
    embed = Embed(
        title=f'Mech build "{mech.name}"', color=(mech.dominant_element or Element.OMNI).color
    ).add_field("Stats:", mech.print_stats(included_buffs))
    return embed


class MechView(InteractionCheck, PaginatorView):
    """Class implementing View for a button-based mech building."""

    response_message: Message

    def __init__(
        self,
        mech: Mech,
        pack: PackInterface,
        player: Player,
        *,
        timeout: float = 180.0,
    ) -> None:
        super().__init__(timeout=timeout, columns=5)
        self.pack = pack
        self.mech = mech
        self.player = player
        self.user_id = player.id

        self.active: TrinaryButton[str] | None = None
        self.image_update_task = asyncio.Task(asyncio.sleep(0))
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
            return await inter.send(
                "This won't show any effect because all your buffs are at level zero.\n"
                f"You can change that using </buffs:{BUFFS_COMMAND_ID}> command.",
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
            raise DesyncError()

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

        if not self.mech.has_image_cached:
            file = MISSING
            url = None

            if self.mech.torso is not None:
                file = image_to_file(self.mech.image, mech_to_id_str(self.mech))
                url = f"attachment://{file.filename}"

            await inter.response.edit_message(
                embed=self.embed.set_image(url), file=file, view=self, attachments=[]
            )

        else:
            await inter.response.edit_message(embed=self.embed, view=self)

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
            self.embed.color = Element.OMNI.color


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


@plugin.slash_command()
async def mech(_: CommandInteraction) -> None:
    pass


@mech.sub_command(name="list")
async def browse(inter: CommandInteraction, player: Player) -> None:
    """Displays a list of your builds. {{ MECH_BROWSE }}"""
    if not player.builds:
        await inter.send("You do not have any builds.", ephemeral=True)
        return

    embed = Embed(title="Your builds", color=inter.author.color)

    if player.active_build_name:
        embed.description = f"Currently active: **{player.active_build_name}**"

    fields: list[tuple[str, str]] = []

    def count_not_none(it: t.Iterable[t.Any | None]) -> int:
        i = 0
        for item in it:
            if item is not None:
                i += 1
        return i

    fmt_string = (
        f"• {Type.TORSO.emoji} {{TORSO}}\n"
        f"• {Type.LEGS.emoji} {{LEGS}}\n"
        f"• {Type.SIDE_WEAPON.emoji} {{WEAPONS}} weapon(s)\n"
        f"• {Type.MODULE.emoji} {{MODULES}} module(s)\n"
        f"• {STATS['weight'].emoji} {{WEIGHT}} weight"
    )

    for name, build in player.builds.items():
        value = fmt_string.format(
            TORSO="no torso" if build.torso is None else build.torso.name,
            LEGS="no legs" if build.legs is None else build.legs.name,
            WEAPONS=count_not_none(build.iter_items(weapons=True)),
            MODULES=count_not_none(build.iter_items(modules=True)),
            WEIGHT=build.weight,
        )
        fields.append((name, value))

    for title, value in fields:
        embed.add_field(title, value)

    await inter.send(embed=embed, ephemeral=True)


@mech.sub_command()
@commands.max_concurrency(1, commands.BucketType.user)
async def build(inter: MixedInteraction, player: Player, name: str | None = None) -> None:
    """Interactive UI for modifying a mech build. {{ MECH_BUILD }}

    Parameters
    -----------
    name: The name of existing build or one to create. If not passed, defaults to "Unnamed Mech". {{ MECH_BUILD_NAME }}
    """

    if name is None:
        mech = player.get_or_create_active_build()
        name = player.active_build_name

    elif name not in player.builds:
        mech = player.create_build(name)

    else:
        mech = player.builds[name]
        player.active_build_name = mech.name

    view = MechView(mech, plugin.bot.default_pack, player, timeout=100)
    file = MISSING

    if mech.torso is not None:
        view.embed.color = mech.torso.element.color

        file = image_to_file(mech.image, mech_to_id_str(mech))
        url = f"attachment://{file.filename}"
        view.embed.set_image(url)

    if isinstance(inter, MessageInteraction):
        await inter.response.edit_message(embed=view.embed, file=file, view=view)

    else:
        await inter.response.send_message(embed=view.embed, file=file, view=view, ephemeral=True)
    view.response_message = await inter.original_response()

    await view.wait()
    await inter.edit_original_response(view=None)


@mech.sub_command(name="import")
async def import_(inter: CommandInteraction, player: Player, file: Attachment) -> None:
    """Import mech(s) from a .JSON file.

    Parameters
    ----------
    file: a .JSON file as exported from WU.
    """
    # file size of 16KiB sounds like a pretty beefy amount of mechs
    MAX_SIZE = 1 << 14

    if MAX_SIZE < file.size:
        raise commands.UserInputError(f"The maximum accepted file size is {MAX_SIZE >> 10}KiB.")

    data = json.loads(await file.read())

    try:
        mechs, failed = load_mechs(data, plugin.bot.default_pack)

    except ValueError as e:
        raise commands.UserInputError(str(e)) from None

    if not mechs:
        message = "No mechs loaded."

    else:
        # TODO: warn about overwriting
        player.builds.update((mech.name, mech) for mech in mechs)
        message = "Loaded mechs: " + ", ".join(f"`{mech.name}`" for mech in mechs)

    if failed:
        message += "\nFailed to load: " + ", ".join(
            f"{name}, reason: {reason}" for name, reason in failed.items()
        )

    await inter.response.send_message(message, ephemeral=True)


@mech.sub_command()
async def export(inter: CommandInteraction, player: Player) -> None:
    """Export selected mechs into a WU-compatible .JSON file."""

    if not player.builds:
        return await inter.response.send_message("You do not have any builds.", ephemeral=True)

    mech_select = Select(
        placeholder="Select mechs to export",
        custom_id="select:exported_mechs",
        max_values=min(25, len(player.builds)),
        options=list(player.builds)[:25],
    )
    await inter.response.send_message(components=mech_select, ephemeral=True)

    def check(inter: MessageInteraction) -> bool:
        return inter.data.custom_id == mech_select.custom_id

    new_inter: MessageInteraction = await plugin.bot.wait_for("dropdown", check=check)
    values = new_inter.values
    assert values is not None
    selected = frozenset(values)

    mechs = (mech for name, mech in player.builds.items() if name in selected)
    fp = dump_mechs(mechs, plugin.bot.default_pack.key)
    file = File(fp, "mechs.json")  # type: ignore
    await new_inter.response.edit_message(file=file, components=None)


@build.autocomplete("name")
async def mech_name_autocomplete(
    inter: CommandInteraction, input: str
) -> list[str] | dict[str, str]:
    """Autocomplete for player builds."""
    player = plugin.bot.get_player(inter)
    input = truncate_name(input)
    case_insensitive = input.lower()
    return (
        [name for name in player.builds if name.lower().startswith(case_insensitive)]
        or {f'Enter to create mech "{input}"...': input}
        if input
        else []
    )


setup, teardown = plugin.create_extension_handlers()
