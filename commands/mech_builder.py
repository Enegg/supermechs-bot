from __future__ import annotations

import asyncio
import logging
import typing as t

import aiohttp
import disnake
import lib_types
from disnake import SelectOption
from disnake.ext import commands
from disnake.ui import Button, Select, select
from SuperMechs.enums import Element, Icon
from SuperMechs.images import image_to_file
from SuperMechs.inv_item import InvItem
from SuperMechs.item import AnyItem
from SuperMechs.mech import Mech
from SuperMechs.sm_base import ArenaBuffs
from typing_extensions import Self
from ui import PaginatorView, ToggleButton, TrinaryButton, button
from utils import EMPTY_OPTION, OptionPaginator, random_str

if t.TYPE_CHECKING:
    from bot import SMBot

logger = logging.getLogger("channel_logs")


trans_table = {
    "top1": "top_weapon",
    "top2": "top_weapon",
    "side1": "side_weapon",
    "side2": "side_weapon",
    "side3": "side_weapon",
    "side4": "side_weapon",
    "mod1": "module",
    "mod2": "module",
    "mod3": "module",
    "mod4": "module",
    "mod5": "module",
    "mod6": "module",
    "mod7": "module",
    "mod8": "module"}


def translate_type(_type: str) -> str:
    if _type.startswith(("side", "top")):
        return ("TOP_" if _type.startswith("top") else "SIDE_") + (
            "LEFT" if int(_type[-1]) % 2 else "RIGHT")

    if _type.startswith("mod"):
        return "MODULE"

    return _type.upper()


class MechView(PaginatorView):
    """Class implementing View for a button-based mech building"""
    bot_msg: disnake.Message

    def __init__(
        self,
        mech: Mech,
        embed: disnake.Embed,
        items: dict[str, AnyItem],
        arena_buffs: ArenaBuffs,
        session: aiohttp.ClientSession,
        *,
        user_id: int,
        timeout: float | None = 180
    ) -> None:
        self.mech = mech
        self.embed = embed
        self.items = items
        self.buffs = arena_buffs
        self.session = session

        self.active: TrinaryButton[Self, AnyItem | None] | None = None
        self.image_update_task = asyncio.Future()

        self.paginator = OptionPaginator(
            SelectOption(
                label="Previous items",
                value="option:up",
                emoji="🔼",
                description="Click to show previous items"),
            SelectOption(
                label="More items",
                value="option:down",
                emoji="🔽",
                description="Click to show more items"))

        self.buttons: list[list[Button[Self]]] = [
            [
                TrinaryButton(
                    emoji=Icon[translate_type(id)].emoji,
                    row=pos,
                    custom_id=id,
                    item=getattr(mech, id),
                    callback=self.slot_button_cb
                )
                for id in row
            ]
            for pos, row in enumerate((
                ("top1", "drone", "top2", "charge", "mod1", "mod2", "mod3", "mod4"),
                ("side3", "torso", "side4", "tele", "mod5", "mod6", "mod7", "mod8"),
                ("side1", "legs", "side2", "hook"),
            ))
        ]

        super().__init__(user_id=user_id, timeout=timeout, columns_per_page=4)

        for i in range(4):
            self.buttons[2].append(
                Button(label="⠀", custom_id=f"button:no_op{i}", disabled=True, row=2))

        self.persistent_buttons = (
            self.modules_button,
            self.filters_button,
            self.buffs_button)

        self.visible.extend(self.persistent_buttons)
        self.remove_item(self.filters_select)
        self.filters_select.row = 3
        self.update_page()

        self.item_type_ref: dict[str, list[SelectOption]] = dict(
            drone=[],
            torso=[],
            legs=[],
            top_weapon=[],
            side_weapon=[],
            charge=[],
            tele=[],
            hook=[],
            module=[])

        for item in items.values():
            self.item_type_ref[item.type.lower()].append(
                SelectOption(label=item.name, emoji=item.element.emoji))

        ref = [element.emoji for element in Element]

        for item_list in self.item_type_ref.values():
            item_list.sort(key=lambda option: (ref.index(str(option.emoji)), option.label))

    def update_page(self) -> None:
        super().update_page()

        self.to_lock = [button for button in self.visible if button.label != "⠀"]

        for button in self.persistent_buttons:
            self.add_item(button)
            self.visible.append(button)

    async def slot_button_cb(
        self, button: TrinaryButton[Self, AnyItem | None], inter: disnake.MessageInteraction
    ) -> None:
        self.update_style(button)
        await inter.response.edit_message(view=self)

    @button(cls=Button[Self], emoji=Icon.MODULE.emoji, custom_id="button:modules", row=0)
    async def modules_button(
        self, button: Button[Self], inter: disnake.MessageInteraction
    ) -> None:
        self.page ^= 1
        button.emoji = Icon.TORSO.emoji if self.page else Icon.MODULE.emoji

        self.update_page()
        await inter.response.edit_message(view=self)

    @button(label="Filters", custom_id="button:filters", row=2, cls=TrinaryButton[Self, t.Any])
    async def filters_button(
        self, button: TrinaryButton[Self, t.Any], inter: disnake.MessageInteraction
    ) -> None:
        button.toggle()
        self.toggle_menus()
        await inter.response.edit_message(view=self)

    @button(label="Buffs", custom_id="button:buffs", row=1, cls=ToggleButton[Self])
    async def buffs_button(
        self, button: ToggleButton[Self], inter: disnake.MessageInteraction
    ) -> None:
        if self.buffs.is_at_zero:
            await inter.send(
                "This won't show any effect because all your buffs are at level zero.\n"
                "You can change that using `/buffs` command.", ephemeral=True)
            return

        button.toggle()

        mech = self.mech
        self.embed.set_field_at(
            0,
            name="Stats:",
            value=mech.print_stats(self.buffs if button.on else None))

        if mech.torso is not None:
            self.embed.color = mech.torso.element.color

        await inter.response.edit_message(embed=self.embed, view=self)

    @select(
        placeholder="Choose slot",
        custom_id="select:item",
        options=[EMPTY_OPTION],
        disabled=True,
        row=3)
    async def item_select(self, select: Select[Self], inter: disnake.MessageInteraction) -> None:
        item_name, = select.values

        if item_name in {"option:up", "option:down"}:
            if item_name == "option:up":
                self.paginator.page -= 1

            else:
                self.paginator.page += 1

            select._underlying.options = self.paginator.get_options()
            await inter.response.edit_message(view=self)
            return

        select.placeholder = item_name
        item = None if item_name == "empty" else self.items[item_name]

        assert self.active is not None
        self.active.item = item

        if item is not None:  # HACK
            item = InvItem.from_item(item)  # type: ignore

        if self.active.custom_id == "torso":  # if torso removed, edit embed's color

            pass

        self.mech[self.active.custom_id] = item

        self.update_style(self.active)

        self.embed.set_field_at(
            0,
            name="Stats:",
            value=self.mech.print_stats(self.buffs if self.buffs_button.on else None))

        if self.mech.torso is not None:
            self.embed.color = self.mech.torso.element.color

        await inter.response.edit_message(embed=self.embed, view=self)

    @select(
        custom_id="select:filters",
        placeholder="Select filters",
        min_values=0,
        max_values=4,
        row=4,
        options=[
            SelectOption(label="Physical items",  value="type:PHYS", emoji=Element.PHYS.emoji),
            SelectOption(label="Explosive items", value="type:HEAT", emoji=Element.HEAT.emoji),
            SelectOption(label="Electric items",  value="type:ELEC", emoji=Element.ELEC.emoji),
            SelectOption(label="Combined items",  value="type:COMB", emoji=Element.COMB.emoji)]
    )
    async def filters_select(self, select: Select[Self], inter: disnake.MessageInteraction) -> None:
        values = set(select.values)

        for option in select.options:
            option.default = option.value in values

        if self.active is not None:
            self.update_paginator(self.active.custom_id)

        self.filters_button.on = False
        self.toggle_menus()
        await inter.response.edit_message(view=self)

    async def update_image(self) -> None:
        """Updates embed's image and the message"""
        if self.mech.has_image_cached:
            return

        # load images while waiting
        await asyncio.gather(asyncio.sleep(2.0), self.mech.load_images(self.session))

        filename = random_str(8) + ".png"
        self.embed.set_image(url=f"attachment://{filename}")
        file = image_to_file(self.mech.image, filename)
        await self.bot_msg.edit(embed=self.embed, file=file, attachments=[])

    def filter_options(self, item_type: str) -> list[SelectOption]:
        """Returns a list of `SelectOption`s filtered by type"""
        all_options = self.item_type_ref[item_type]
        new_options = [EMPTY_OPTION]

        if len(all_options) <= 24:
            return new_options + all_options

        types = {str(option.emoji) for option in self.filters_select.options if option.default}

        new_options.extend(
            filter(lambda item: str(item.emoji) in types, all_options)
            if types else
            all_options)
        return new_options

    def toggle_menus(self) -> None:
        """Swaps between item select and filter select"""

        if self.filters_button.on:
            self.remove_item(self.item_select)
            self.add_item(self.filters_select)

            for button in self.to_lock:
                button.disabled = True

            self.modules_button.disabled = True

        else:
            self.remove_item(self.filters_select)
            self.add_item(self.item_select)

            for button in self.to_lock:
                button.disabled = False

            self.modules_button.disabled = False

    def update_style(self, button: TrinaryButton[Self, AnyItem | None], /) -> None:
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

        self.update_paginator(button.custom_id)
        self.item_select.placeholder = button.item.name if button.item else "empty"
        self.active = button

    def update_paginator(self, item_type: str) -> None:
        if item_type in trans_table:
            item_type = trans_table[item_type]

        self.paginator.options = self.filter_options(item_type)
        self.item_select._underlying.options = self.paginator.get_options()


@commands.slash_command()
async def mech(_: lib_types.ApplicationCommandInteraction) -> None:
    pass


@mech.sub_command()
async def show(inter: lib_types.ApplicationCommandInteraction, name: t.Optional[str] = None) -> None:
    """Displays your mech and its stats

    Parameters
    -----------
    name: Name of build to show. If not passed, it will be your most recent build.
    """
    player = inter.bot.get_player(inter)

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
            f'No build found named "{name}".',
            allowed_mentions=disnake.AllowedMentions.none())
        return

    embed = disnake.Embed(title=f'Mech build "{name}"')
    embed.add_field(name="Stats:", value=mech.print_stats(player.arena_buffs))

    if mech.torso is None:
        embed.color = inter.author.color
        await inter.send(embed=embed)
        return

    embed.color = mech.torso.element.color
    filename = f"{name}.png"
    embed.set_image(url=f"attachment://{filename}")

    await mech.load_images(inter.bot.session)
    file = image_to_file(mech.image, filename)
    await inter.send(embed=embed, file=file)


@mech.sub_command(name="list")
async def browse(inter: lib_types.ApplicationCommandInteraction) -> None:
    """Displays a list of your builds"""
    player = inter.bot.get_player(inter)

    if not player.builds:
        await inter.send("You do not have any builds.", ephemeral=True)
        return

    string = f"Currently active: **{player.active_build_name}**\n"

    string += "\n\n".join(
        f"**{name}**:\n"
        f'{build.torso or "No torso"}'
        f', {build.legs or "no legs"}'
        f", {len(tuple(filter(None, build.iter_weapons())))} weapon(s)"
        f", {len(tuple(filter(None, build.iter_modules())))} module(s)"
        f"; {build.weight} weight"
        for name, build in player.builds.items())

    await inter.send(string)


@mech.sub_command()
@commands.max_concurrency(1, commands.BucketType.user)
async def build(inter: lib_types.ApplicationCommandInteraction, name: t.Optional[str] = None) -> None:
    """Interactive UI for modifying a mech build.

    Parameters
    -----------
    name: The name of existing build or one to create. If not passed, it will be randomized.
    """
    player = inter.bot.get_player(inter)

    if name is None:
        mech = player.get_or_create_build()
        name = player.active_build_name

    elif name not in player.builds:
        mech = player.new_build(name)

    else:
        mech = player.builds[name]

    embed = disnake.Embed(title=f'Mech build "{name}"', color=inter.author.color)
    embed.add_field(name="Stats:", value=mech.print_stats())

    view = MechView(
        mech,
        embed,
        inter.bot.items_cache,
        player.arena_buffs,
        inter.bot.session,
        user_id=inter.author.id,
        timeout=100)

    if mech.torso is None:
        await inter.send(embed=embed, view=view)

    else:
        embed.color = mech.torso.element.color

        await mech.load_images(inter.bot.session)
        filename = random_str(8) + ".png"

        file = image_to_file(mech.image, filename)
        embed.set_image(url=f"attachment://{filename}")

        await inter.send(embed=embed, view=view, file=file)

    view.bot_msg = await inter.original_message()

    if await view.wait():
        await inter.edit_original_message(view=None)


@show.autocomplete("name")
@build.autocomplete("name")
async def build_autocomplete(inter: lib_types.ApplicationCommandInteraction, input: str) -> list[str]:
    """Autocomplete for player builds"""
    player = inter.bot.get_player(inter)
    input = input.lower()
    return [name for name in player.builds if name.lower().startswith(input)]


def setup(bot: SMBot) -> None:
    bot.add_slash_command(mech)


def teardown(bot: SMBot) -> None:
    bot.remove_slash_command("mech")
