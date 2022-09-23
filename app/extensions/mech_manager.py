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
from disnake.ext import commands
from disnake.utils import MISSING

from app.lib_helpers import DesyncError, image_to_file
from app.ui.buttons import Button, ToggleButton, TrinaryButton, button
from app.ui.item import add_callback
from app.ui.selects import EMPTY_OPTION, PaginatedSelect, Select, select
from app.ui.views import InteractionCheck, PaginatorView, positioned
from SuperMechs.enums import Element, Type
from SuperMechs.ext.wu_compat import dump_mechs, load_mechs, mech_to_id_str
from SuperMechs.inv_item import InvItem
from SuperMechs.item import AnyItem
from SuperMechs.mech import Mech, slot_to_icon_data, slot_to_type
from SuperMechs.pack_interface import PackInterface
from SuperMechs.player import Player
from SuperMechs.utils import truncate_name

if t.TYPE_CHECKING:
    from app.bot import SMBot

MixedInteraction = CommandInteraction | MessageInteraction
logger = logging.getLogger(f"main.{__name__}")


class MechView(InteractionCheck, PaginatorView):
    """Class implementing View for a button-based mech building"""

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

        self.active: TrinaryButton[AnyItem] | None = None
        self.dominant = mech.get_dominant_element()
        self.image_update_task = asyncio.Task(asyncio.sleep(0))

        # fmt: off
        self.embed = Embed(
            title=f'Mech build "{mech.name}"', color=Element.OMNI.color
        ).add_field("Stats:", mech.print_stats())
        # fmt: on

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
                        item=mech[id],
                        emoji=slot_to_icon_data(id).emoji,
                        row=pos,
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

        ref = [element.emoji for element in Element]

        for item_list in self.item_groups.values():
            item_list.sort(key=lambda option: (ref.index(str(option.emoji)), option.label))

    async def slot_button_cb(
        self,
        button: TrinaryButton[t.Any],
        inter: MessageInteraction,
    ) -> None:
        """Callback shared by all of the item slot buttons."""
        self.update_style(button)
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
            await inter.send(
                "This won't show any effect because all your buffs are at level zero.\n"
                "You can change that using `/buffs` command.",
                ephemeral=True,
            )
            return

        button.toggle()

        self.embed.set_field_at(
            0,
            name="Stats:",
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
        (item_name,) = select.values

        if select.check_option(item_name):
            await inter.response.edit_message(view=self)
            return

        item = None if item_name == EMPTY_OPTION.label else self.pack.get_item_by_name(item_name)

        # sanity check if the item is actually valid
        if item is not None and item.type is not slot_to_type(self.active.custom_id):
            raise DesyncError()

        self.active.item = item
        select.placeholder = item_name

        if item is not None:
            item = InvItem.from_item(item, maxed=True)

        self.mech[self.active.custom_id] = item

        self.dominant = self.mech.get_dominant_element()

        if self.dominant is not None:
            self.embed.color = self.dominant.color

        elif self.mech.torso is not None:
            self.embed.color = self.mech.torso.element.color

        elif self.active.custom_id == "torso" and item is None:
            self.embed.color = Element.OMNI.color

        self.update_style(self.active)

        self.embed.set_field_at(
            0,
            name="Stats:",
            value=self.mech.print_stats(self.player.arena_buffs if self.buffs_button.on else None),
        )

        await inter.response.edit_message(embed=self.embed, view=self)

    async def update_image(self) -> None:
        """Background task to update embed's image."""
        if self.mech.has_image_cached:
            return

        await asyncio.sleep(2.0)

        file = image_to_file(self.mech.image, mech_to_id_str(self.mech))
        self.embed.set_image(url=f"attachment://{file.filename}")
        await self.response_message.edit(embed=self.embed, file=file, attachments=[])

    def sort_options(self, item_type: Type) -> list[SelectOption]:
        """Returns a list of `SelectOption`s filtered by type"""
        all_options = self.item_groups[item_type]
        new_options = [EMPTY_OPTION]

        if len(all_options) <= 24:
            return new_options + all_options

        ref = [element.emoji for element in Element]

        if self.dominant is not None:
            ref.remove(self.dominant.emoji)
            ref.insert(0, self.dominant.emoji)

        new_options += sorted(all_options, key=lambda o: (ref.index(str(o.emoji)), o.label))

        return new_options

    def update_style(self, button: TrinaryButton[AnyItem], /) -> None:
        """Changes active button, alters its and passed button's style,
        updates dropdown description"""
        button.toggle()

        if self.active is button:
            self.item_select.disabled = True
            self.active = None

            self.image_update_task = asyncio.create_task(self.update_image())
            return

        self.image_update_task.cancel()

        if self.active is None:
            self.item_select.disabled = False

        else:
            self.active.toggle()

        self.item_select.all_options = self.sort_options(slot_to_type(button.custom_id))
        self.item_select.placeholder = button.item.name if button.item else "empty"
        self.active = button


class MechManager(commands.Cog):
    def __init__(self, bot: SMBot) -> None:
        self.bot = bot

    @commands.slash_command()
    async def mech(self, _: CommandInteraction) -> None:
        pass

    @mech.sub_command(name="list")
    async def browse(self, inter: CommandInteraction, player: Player) -> None:
        """Displays a list of your builds. {{ MECH_BROWSE }}"""
        if not player.builds:
            await inter.send("You do not have any builds.", ephemeral=True)
            return

        string = f"Currently active: **{player.active_build_name}**\n"

        string += "\n\n".join(
            f"**{name}**:\n"
            f'{build.torso or "No torso"}'
            f', {build.legs or "no legs"}'
            f", {len(tuple(filter(None, build.iter_items(weapons=True))))} weapon(s)"
            f", {len(tuple(filter(None, build.iter_items(modules=True))))} module(s)"
            f"; {build.weight} weight"
            for name, build in player.builds.items()
        )

        await inter.send(string, ephemeral=True)

    @mech.sub_command()
    @commands.max_concurrency(1, commands.BucketType.user)
    async def build(self, inter: MixedInteraction, player: Player, name: str | None = None) -> None:
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

        view = MechView(mech, self.bot.default_pack, player, timeout=100)
        file = MISSING

        if mech.torso is not None:
            view.embed.color = mech.torso.element.color

            file = image_to_file(mech.image, mech_to_id_str(mech))
            url = f"attachment://{file.filename}"
            view.embed.set_image(url)

        if isinstance(inter, MessageInteraction):
            await inter.response.edit_message(embed=view.embed, file=file, view=view)

        else:
            await inter.response.send_message(
                embed=view.embed, file=file, view=view, ephemeral=True
            )
        view.response_message = await inter.original_response()

        await view.wait()
        await inter.edit_original_response(view=None)

    @mech.sub_command(name="import")
    async def import_(self, inter: CommandInteraction, player: Player, file: Attachment) -> None:
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
            mechs, failed = load_mechs(data, self.bot.default_pack)

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
    async def export(self, inter: CommandInteraction, player: Player) -> None:
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

        new_inter: MessageInteraction = await inter.bot.wait_for("dropdown", check=check)
        values = new_inter.values
        assert values is not None
        selected = frozenset(values)

        mechs = (mech for name, mech in player.builds.items() if name in selected)
        fp = dump_mechs(mechs, self.bot.default_pack.key)
        file = File(fp, "mechs.json")  # type: ignore
        await new_inter.response.edit_message(file=file, components=None)

    @build.autocomplete("name")
    async def mech_name_autocomplete(
        self, inter: CommandInteraction, input: str
    ) -> list[str] | dict[str, str]:
        """Autocomplete for player builds."""
        player = self.bot.get_player(inter)
        input = truncate_name(input)
        case_insensitive = input.lower()
        return [name for name in player.builds if name.lower().startswith(case_insensitive)] or {
            f'Enter to create mech "{input}"...': input
        }


def setup(bot: SMBot) -> None:
    bot.add_cog(MechManager(bot))
    logger.info('Cog "MechManager" loaded')
