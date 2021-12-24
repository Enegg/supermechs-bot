from __future__ import annotations

import random
from itertools import zip_longest
from typing import TYPE_CHECKING, Iterable, cast

import aiohttp
import disnake
from disnake.ext import commands

from config import DEFAULT_PACK_URL, TEST_GUILDS
from functions import random_str, search_for
from image_manipulation import image_to_file
from SM_classes import (STAT_NAMES, AnyAttachment, ArenaBuffs, Item, ItemPack,
                        Player, Rarity)
from ui_components import ArenaBuffsView, ItemView, MechView

if TYPE_CHECKING:
    from UltraMech import HostedBot

# helper functions for ,stats
MAX_BUFFS = ArenaBuffs.maxed()

def buff(stat: str, enabled: bool, value: int) -> int:
    """Returns a value buffed respectively to stat type"""
    if not enabled or stat == 'health':
        return value

    return MAX_BUFFS.total_buff(stat, value)


def buff_difference(stat: str, enabled: bool, value: int) -> tuple[int, int]:
    """Returns a value buffed respectively to stat type and the difference between it and base"""
    if not enabled or stat == 'health':
        return value, 0

    return MAX_BUFFS.total_buff_difference(stat, value)


def default_embed(embed: disnake.Embed, item: Item[AnyAttachment], buffs_enabled: bool) -> None:
    rarity = item.rarity

    if isinstance(rarity, Rarity):
        color_str = f'({rarity})'

    else:
        _min, _max = rarity
        lower = _min.level
        upper = _max.level

        colors = list(map(str, Rarity))
        colors[upper] = f'({colors[upper]})'
        color_str = ''.join(colors[lower:upper + 1])

    embed.add_field(name='Transform range: ', value=color_str, inline=False)

    spaced = False
    item_stats = ''  # the main string
    cost_stats = {'backfire', 'heaCost', 'eneCost'}

    for stat, stat_value in item.stats.items():
        if not spaced and stat in cost_stats:
            item_stats += '\n'
            spaced = True

        # number range handler
        if not isinstance(stat_value, list):
            value, diff = buff_difference(stat, buffs_enabled, cast(int, stat_value))
            change = f' **{diff:+}**' if diff else ''

        elif stat_value[0] == stat_value[1]:
            value, diff = buff_difference(stat, buffs_enabled, stat_value[0])
            change = f' **{diff:+}**' if diff else ''

        else:
            x, y = stat_value
            v1, d1 = buff_difference(stat, buffs_enabled, x)
            v2, d2 = buff_difference(stat, buffs_enabled, y)

            change = f' ** {d1:+} {d2:+}**' if d1 or d2 else ''
            value = f'{v1}-{v2}'

        name, emoji = STAT_NAMES[stat]

        if stat == 'uses':
            name = 'Use' if stat_value == 1 else 'Uses'

        item_stats += f'{emoji} **{value}** {name}{change}\n'

    if 'advance' in item.stats or 'retreat' in item.stats:
        item_stats += f"{STAT_NAMES['jump'].emoji} **Jumping required**"

    embed.add_field(name='Stats:', value=item_stats, inline=False)


def compact_embed(embed: disnake.Embed, item: Item[AnyAttachment], buffs_enabled: bool) -> None:
    rarity = item.rarity

    if isinstance(rarity, Rarity):
        color_str = f'({rarity})'

    else:
        _min, _max = rarity
        lower = _min.level
        upper = _max.level

        colors = list(map(str, Rarity))
        colors[upper] = f'({colors[upper]})'
        color_str = ''.join(colors[lower:upper + 1])

    lines: list[str] = []

    for stat, stat_value in item.stats.items():
        if not isinstance(stat_value, list):
            value = buff(stat, buffs_enabled, cast(int, stat_value))

        elif stat_value[0] == stat_value[1]:
            value = buff(stat, buffs_enabled, stat_value[0])

        else:
            value = '-'.join(str(buff(stat, buffs_enabled, n)) for n in stat_value)

        lines.append(f'{STAT_NAMES[stat].emoji} **{value}**')

    if 'advance' in item.stats or 'retreat' in item.stats:
        lines.append(f"{STAT_NAMES['jump'].emoji}❗")

    line_count = len(lines)

    if line_count > 4 and not 0 != line_count % 4 < 3:  # == 0 or > 2
        div = 4

    elif not 0 != line_count % 3 < 2: # == 0 or > 1
        div = 3

    elif line_count < 4:
        div = 2

    else:
        div = 4

    field_text = ('\n'.join(lines[i:i+div]) for i in range(0, line_count, div))
    name_field_zip = zip_longest((color_str,), field_text, fillvalue='⠀')

    for name, field in name_field_zip:
        embed.add_field(name=name, value=field)


class SuperMechs(commands.Cog):
    """Set of commands related to the SuperMechs game."""
    items_dict: dict[str, Item[AnyAttachment]]
    abbrevs: dict[str, set[str]]

    def __init__(self, bot: HostedBot) -> None:
        self.bot = bot
        self.image_url_cache: dict[str, str] = {}
        self.no_img:   set[str] = set()
        self.no_stats: set[str] = set()
        self.players: dict[int, Player] = {}  # TODO: replace with actual database


    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.session


    async def cog_load(self) -> None:
        await self.load_item_pack(DEFAULT_PACK_URL)
        self.abbrevs = self.abbreviate_names(self.items_dict)


    async def load_item_pack(self, pack_url: str, /) -> None:
        """Loads an item pack from url and sets it as active pack."""
        async with self.session.get(pack_url) as response:
            pack: ItemPack = await response.json(encoding='utf-8', content_type=None)

        self.items_dict = {
            item_dict['name']: Item(**item_dict, pack=pack['config'])
            for item_dict in pack['items']}


    @staticmethod
    def abbreviate_names(names: Iterable[str], /) -> dict[str, set[str]]:
        """Returns dict of abbrevs:
        Energy Free Armor => EFA"""
        abbrevs: dict[str, set[str]] = {}

        for name in names:
            if len(name) < 8:
                continue

            is_single_word = ' ' not in name

            if (IsNotPascal := not name.isupper() and name[1:].islower()) and is_single_word:
                continue

            abbrev = {''.join(a for a in name if a.isupper()).lower()}

            if not is_single_word:
                abbrev.add(name.replace(' ', '').lower()) # Fire Fly => firefly

            if not IsNotPascal and is_single_word: # takes care of PascalCase names
                last = 0
                for i, a in enumerate(name):
                    if a.isupper():
                        if string := name[last:i].lower():
                            abbrev.add(string)

                        last = i

                abbrev.add(name[last:].lower())

            for abb in abbrev:
                abbrevs.setdefault(abb, {name}).add(name)

        return abbrevs


    def get_player(self, inter: disnake.ApplicationCommandInteraction, /) -> Player:
        id = inter.author.id

        if id not in self.players:
            self.players[id] = Player(id)

        return self.players[id]

    # ------------------------------------------- Commands -------------------------------------------

    @commands.slash_command()
    @commands.is_owner()
    async def fetch(self, inter: disnake.ApplicationCommandInteraction, url: str) -> None:
        """Loads item pack from given url

        Parameters
        -----------
        url:
            The pack url to load"""
        await self.load_item_pack(url)
        await inter.send('Success', ephemeral=True)


    @commands.slash_command()
    async def frantic(self, inter: disnake.ApplicationCommandInteraction) -> None:
        """Humiliate frantic users"""
        frantics = ['https://i.imgur.com/Bbbf4AH.mp4', 'https://i.gyazo.com/8f85e9df5d3b1ed16b3c81dc3bccc3e9.mp4']
        choice = random.choice(frantics)
        await inter.send(choice)


    @commands.slash_command()
    # @channel_lock(['bot', 'spam', 'supermechs', 'command', 'playground'])
    async def item(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name: str,
        compact: bool=False,
        invisible: bool=True,
        raw: bool=False
    ) -> None:
        """Finds an item and returns its stats

        Parameters
        -----------
        name:
            The name of the item or an abbreviation of it
        compact:
            Whether the embed sent back should be compact (breaks on mobile)
        invisible:
            Whether the bot response is visible only to you
        raw:
            Whether not to format the embed and send raw data instead
        """

        if name not in self.items_dict:
            raise commands.UserInputError('Item not found.')

        item = self.items_dict[name]

        # debug flag
        if raw:
            await inter.send(f'`{item!r}`', ephemeral=invisible)
            return

        if compact:
            embed = disnake.Embed(color=item.element.color
            ).set_author(name=item.name, icon_url=item.icon.URL
            ).set_thumbnail(url=item.image_url)
            view = ItemView(embed, item, compact_embed)

        else:
            embed = disnake.Embed(title=item.name,
                description=f"{item.element.name.capitalize()} {item.type.replace('_', ' ').lower()}",
                color=item.element.color
            ).set_thumbnail(url=item.icon.URL
            ).set_image(url=item.image_url)
            view = ItemView(embed, item, default_embed)

        await inter.send(embed=embed, view=view, ephemeral=invisible)
        await view.wait()
        await inter.edit_original_message(view=None)


    @commands.slash_command()
    # @channel_lock(['bot', 'spam', 'supermechs', 'command', 'playground'])
    async def mech(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass


    @mech.sub_command()
    async def show(self, inter: disnake.ApplicationCommandInteraction, name: str=None) -> None:
        """Displays your mech and its stats

        Parameters
        -----------
        name:
            Name of build to show. If not passed, it will be your most recent build.
        """
        player = self.get_player(inter)

        if name is None:
            mech = player.get_active_build()

            if mech is None:
                await inter.send("You do not have any builds.")
                return

            name = player.active_build

        elif name in player.builds:
            mech = player.builds[name]

        else:
            await inter.send(
                f'No build found named "{name}".',
                allowed_mentions=disnake.AllowedMentions.none())
            return

        embed = disnake.Embed(title=f'Mech build "{name}"')
        embed.add_field(name='Stats:', value=mech.print_stats(player.arena_buffs))

        if mech.torso is None:
            embed.color = inter.author.color
            await inter.send(embed=embed)
            return

        embed.color = mech.torso.element.color
        filename = f'{name}.png'
        embed.set_image(url=f'attachment://{filename}')

        await mech.load_images(self.session)
        file = image_to_file(mech.image, filename)
        await inter.send(embed=embed, file=file)


    @mech.sub_command(name='list')
    async def browse(self, inter: disnake.ApplicationCommandInteraction) -> None:
        """Displays a list of your builds"""
        player = self.get_player(inter)

        if not player.builds:
            await inter.send('You do not have any builds.')
            return

        string = f'Currently active: **{player.active_build}**\n'

        string += '\n\n'.join(
            f'**{name}**:\n'
            f'{build.torso or "No torso"}'
            f', {build.legs or "no legs"}'
            f', {len(tuple(filter(None, build.iter_weapons())))} weapon(s)'
            f', {len(tuple(filter(None, build.iter_modules())))} module(s)'
            f'; {build.weight} weight'
            for name, build in player.builds.items())

        await inter.send(string)


    @mech.sub_command()
    @commands.max_concurrency(1, commands.BucketType.user)
    async def build(self, inter: disnake.ApplicationCommandInteraction, name: str=None) -> None:
        """Interactive UI for modifying a mech build.

        Parameters
        -----------
        name:
            The name of existing build or one to create.
            If not passed, it will be randomized.
        """
        player = self.get_player(inter)

        if name is None:
            mech = player.get_or_create_build()
            name = player.active_build

        elif name not in player.builds:
            mech = player.new_build(name)

        else:
            mech = player.builds[name]

        embed = disnake.Embed(title=f'Mech build "{name}"', color=inter.author.color)
        embed.add_field(name='Stats:', value=mech.print_stats())

        view = MechView(mech, embed, self.items_dict, player.arena_buffs, self.session)

        async def on_timeout() -> None:
            await inter.edit_original_message(view=None)

        view.on_timeout = on_timeout

        if mech.torso is None:
            await inter.send(embed=embed, view=view)

        else:
            embed.color = mech.torso.element.color

            await mech.load_images(self.session)
            filename = random_str(8) + '.png'

            file = image_to_file(mech.image, filename)
            embed.set_image(url=f'attachment://{filename}')

            await inter.send(embed=embed, view=view, file=file)


    @show.autocomplete('name')
    @build.autocomplete('name')
    async def build_autocomplete(self, inter: disnake.ApplicationCommandInteraction, input: str) -> list[str]:
        """Autocomplete for player builds"""
        player = self.get_player(inter)
        input = input.lower()
        return [name for name in player.builds if name.lower().startswith(input)]


    @commands.slash_command()
    @commands.max_concurrency(1, commands.BucketType.user)
    async def buffs(self, inter: disnake.ApplicationCommandInteraction) -> None:
        """Interactive UI for modifying your arena buffs"""
        player = self.get_player(inter)
        view = ArenaBuffsView(player.arena_buffs)

        async def on_timeout() -> None:
            view.before_stop()
            await inter.edit_original_message(view=None)

        view.on_timeout = on_timeout

        await inter.send('**Arena Shop**', view=view)


    @commands.slash_command(guild_ids=TEST_GUILDS)
    @commands.is_owner()
    async def maxed(self, inter: disnake.ApplicationCommandInteraction) -> None:
        """Maxes out your buffs"""
        me = self.get_player(inter)
        me.arena_buffs.levels.update(ArenaBuffs.maxed().levels)
        await inter.send('Success', ephemeral=True)


    @commands.slash_command()
    async def compare(self, inter: disnake.ApplicationCommandInteraction, item1: str, item2: str) -> None:
        """Shows an interactive comparison of two items.

        Parameters
        -----------
        item1: First item to compare.
        item2: Second item to compare.
        """
        item_a = self.items_dict.get(item1)
        item_b = self.items_dict.get(item2)

        if item_a is None or item_b is None:
            raise commands.UserInputError('Either of specified items not found.')


    @item.autocomplete('name')
    @compare.autocomplete('item1')
    @compare.autocomplete('item2')
    async def item_autocomplete(self, inter: disnake.ApplicationCommandInteraction, input: str) -> list[str]:
        """Autocomplete for items"""
        if len(input) < 2:
            return ['Start typing to get suggestions...']

        items = sorted(set(search_for(input, self.items_dict)) | self.abbrevs.get(input.lower(), set()))

        if len(items) <= 25:
            return items

        return items[:25]



def setup(bot: HostedBot) -> None:
    bot.add_cog(SuperMechs(bot))
    print('SM loaded')
