from __future__ import annotations

import asyncio
import logging
import typing as t

from disnake import (AllowedMentions, CommandInteraction, Embed, Message, MessageInteraction,
                     SelectOption)
from disnake.ext import commands
from typing_extensions import Self

from lib_helpers import DesyncError, image_to_file
from SuperMechs.enums import Element, Type
from SuperMechs.inv_item import AnyInvItem, InvItem
from SuperMechs.item import AnyItem
from SuperMechs.mech import Mech, icon_data_for_slot, type_for_slot
from SuperMechs.player import Player
from ui.buttons import Button, ToggleButton, TrinaryButton, button
from ui.item import add_callback
from ui.selects import EMPTY_OPTION, PaginatedSelect, select
from ui.views import InteractionCheck, PaginatorView, positioned

if t.TYPE_CHECKING:
    from bot import SMBot

logger = logging.getLogger(f"main.{__name__}")


class MechView(InteractionCheck, PaginatorView):
    """Class implementing View for a button-based mech building"""

    bot_msg: Message

    def __init__(
        self,
        mech: Mech,
        bot: SMBot,
        embed: Embed,
        player: Player,
        *,
        timeout: float | None = 180,
    ) -> None:
        super().__init__(timeout=timeout, columns=5)
        self.bot = bot
        self.mech = mech
        self.embed = embed
        self.player = player
        self.user_id = player.id

        self.active: TrinaryButton[AnyItem] | None = None
        self.dominant = mech.figure_dominant_element()
        self.image_update_task = asyncio.Future[None]()

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
                        emoji=icon_data_for_slot(id).emoji,
                        row=pos,
                    ),
                    self.slot_button_cb,
                )
                for id in row
            )

        self.rows[2].extend_page_items(
            Button(label="⠀", custom_id=f"button:no_op{i}", disabled=True, row=2)
            for i in range(6)
        )

        # property updates the rows
        self.page = 0

        self.item_groups: dict[Type, list[SelectOption]] = {type: [] for type in Type}

        for item in bot.items_cache.values():
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
    async def modules_button(self, button: Button[Self], inter: MessageInteraction) -> None:
        """Button swapping mech editor with modules and vice versa."""
        self.page ^= 1
        button.emoji = Type.TORSO.emoji if self.page else Type.MODULE.emoji

        await inter.response.edit_message(view=self)

    @positioned(1, 4)
    @button(cls=ToggleButton, label="Buffs", custom_id="button:buffs")
    async def buffs_button(self, button: ToggleButton, inter: MessageInteraction) -> None:
        """Button toggling arena buffs being applied to mech's stats."""
        if self.player.arena_buffs.is_at_zero:
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
        options=[EMPTY_OPTION],
        disabled=True,
    )
    async def item_select(self, select: PaginatedSelect, inter: MessageInteraction) -> None:
        """Dropdown menu with all the items."""
        assert self.active is not None
        (item_name,) = select.values

        if select.check_option(item_name):
            await inter.response.edit_message(view=self)
            return

        item = None if item_name == "empty" else self.bot.items_cache[item_name]

        # sanity check if the item is actually valid
        if item is not None and item.type is not type_for_slot(self.active.custom_id):
            raise DesyncError()

        self.active.item = item
        select.placeholder = item_name

        if item is not None:
            item = t.cast(AnyInvItem, InvItem.from_item(item))  # type: ignore

        self.mech[self.active.custom_id] = item

        self.dominant = self.mech.figure_dominant_element()

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

        # load images while waiting
        await asyncio.gather(asyncio.sleep(2.0), self.mech.load_images(self.bot.session))

        filename = f"{self.mech:id}.png"
        self.embed.set_image(url=f"attachment://{filename}")
        file = image_to_file(self.mech.image, filename)
        await self.bot_msg.edit(embed=self.embed, file=file, attachments=[])

    def resort_options(self, item_type: Type) -> list[SelectOption]:
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

            self.image_update_task = asyncio.ensure_future(self.update_image())
            return

        self.image_update_task.cancel()

        if self.active is None:
            self.item_select.disabled = False

        else:
            self.active.toggle()

        self.item_select.options = self.resort_options(type_for_slot(button.custom_id))
        self.item_select.placeholder = button.item.name if button.item else "empty"
        self.active = button


class MechBuilder(commands.Cog):
    def __init__(self, bot: SMBot) -> None:
        self.bot = bot

    @commands.slash_command()
    async def mech(self, _: CommandInteraction) -> None:
        pass

    @mech.sub_command()
    async def show(
        self, inter: CommandInteraction, player: Player, name: str | None = None
    ) -> None:
        """Displays your mech and its stats. {{ MECH_SHOW }}

        Parameters
        -----------
        name: Name of build to show. If not passed, it will be your most recent build. {{ MECH_SHOW_NAME }}
        """
        if name is None:
            mech = player.active_build

            if mech is None:
                await inter.send("You do not have any builds.", ephemeral=True)
                return

            name = player.active_build_name

        elif name in player.builds:
            mech = player.builds[name]

        else:
            await inter.send(
                f'No build named "{name}" found.',
                allowed_mentions=AllowedMentions.none(),
            )
            return

        embed = Embed(title=f'Mech build "{name}"')
        embed.add_field("Stats:", mech.print_stats(player.arena_buffs))

        if mech.torso is None:
            embed.color = inter.author.color
            await inter.send(embed=embed)
            return

        embed.color = mech.torso.element.color

        await mech.load_images(self.bot.session)
        embed.set_image(file=image_to_file(mech.image, f"{name}.png"))
        await inter.send(embed=embed)

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

        await inter.send(string)

    @mech.sub_command()
    @commands.max_concurrency(1, commands.BucketType.user)
    async def build(
        self, inter: CommandInteraction, player: Player, name: str | None = None
    ) -> None:
        """Interactive UI for modifying a mech build. {{ MECH_BUILD }}

        Parameters
        -----------
        name: The name of existing build or one to create. If not passed, it will be randomized. {{ MECH_BUILD_NAME }}
        """

        if name is None:
            mech = player.get_or_create_build()
            name = player.active_build_name

        elif name not in player.builds:
            mech = player.new_build(name)

        else:
            mech = player.builds[name]

        embed = Embed(title=f'Mech build "{name}"', color=inter.author.color)
        embed.add_field(name="Stats:", value=mech.print_stats())

        view = MechView(mech, self.bot, embed, player, timeout=100)

        if mech.torso is None:
            await inter.send(embed=embed, view=view)

        else:
            embed.color = mech.torso.element.color

            await mech.load_images(self.bot.session)
            filename = f"{self.mech:id}.png"

            embed.set_image(file=image_to_file(mech.image, filename))
            await inter.send(embed=embed, view=view)

        view.bot_msg = await inter.original_message()

        if await view.wait():
            await inter.edit_original_message(view=None)

    @show.autocomplete("name")
    @build.autocomplete("name")
    async def build_autocomplete(self, inter: CommandInteraction, input: str) -> list[str]:
        """Autocomplete for player builds"""
        player = self.bot.get_player(inter)
        input = input.lower()
        return [name for name in player.builds if name.lower().startswith(input)]


def setup(bot: SMBot) -> None:
    bot.add_cog(MechBuilder(bot))
    logger.info('Cog "MechBuilder" loaded')
