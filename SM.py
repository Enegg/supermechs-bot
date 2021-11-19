from __future__ import annotations

import asyncio
import os
import random
import time
from collections import deque
from itertools import zip_longest
from string import ascii_letters
from typing import *

import aiohttp
import disnake
from disnake.ext import commands

from config import DEFAULT_PACK_URL, IMAGE_LINK_TEMPLATES, NONE_EMOJI
from discotools import (EmbedUI, get_message, make_choice_embed, scheduler,
                        spam_command)
from functions import filter_flags, js_format, search_for
from image_manipulation import image_to_file
from SM_classes import (STAT_NAMES, Elements, Icons, Item, ItemDict, Mech,
                        Rarity)
from ui_components import MechView, ToggleButton, View

if TYPE_CHECKING:
    from UltraMech import HostedBot

OPERATIONS = {
    '+20%':  {'eneCap', 'heaCap', 'eneReg', 'heaCap', 'heaCol', 'phyDmg', 'expDmg', 'eleDmg', 'heaDmg', 'eneDmg'},
    '+40%': {'phyRes', 'expRes', 'eleRes'},
    'reduce': {'backfire'}}
LOCAL_IMAGES = {
    'Debug Item': r"D:\Obrazy\Games\Supermechs\Sprites\Deatomizer.png"}



class StringIterator(Iterator[str]):
    def __init__(self, string: str) -> None:
        self._unread: deque[str] = deque()
        self.iter = iter(string)
        self.last: str | None = None


    def __next__(self) -> str:
        if self._unread:
            self.last = self._unread.popleft()

        else:
            self.last = next(self.iter)

        return self.last


    def unread(self) -> None:
        if self.last is None:
            return

        self._unread.appendleft(self.last)
        self.last = None



def concat_op(op: str) -> str:
    return {'!': '≠', '<': '≤', '>': '≥', '=': '='}[op]


def parse_kwargs(args: Iterable[str]):
    """Takes command arguments as an input and tries to match them as key item pairs"""
    # keyword <whitespace> (optional operator: ":" "=" "!=" "≠" "<=" "≤" ">=" "≥" "<" ">") <whitespace> (optional value), ...
    # keyword: TYPE, ELEMENT, TIER, NAME, STAT

    # start with finding operator - they restrict possible keywords, so it narrows searching
    chars = {'=', '<', '>', '!', ':', '≠', '≤', '≥'}

    parsed_args = []

    for arg in args:
        keyword = operator = value = ''
        str_parts = ['']

        space = False
        it = StringIterator(arg)

        for c in it:
            if c == ' ':
                space = True
                continue

            if c in chars:
                if not keyword:
                    keyword = ' '.join(str_parts)
                    str_parts = ['']

                if operator and operator != ':':
                    raise ValueError('Second operator found')

                n = next(it, None)

                if n is None:
                    raise ValueError('End of string while parsing operator')

                if n == '=':
                    try:
                        # !=, ==, <=, >=
                        c = concat_op(c)

                    except KeyError:
                        raise ValueError(f'Invalid operator: "{c}="')

                else:
                    it.unread()

                operator = c
                space = False  # whatever the value, set to False
                continue

            # either keyword or value
            if space:
                str_parts.append('')
                space = False

            str_parts[-1] += c

        if not keyword:
            keyword = ' '.join(str_parts).strip()

        else:
            value = ' '.join(str_parts).strip()

        parsed_args.append((keyword, operator, value))

    return parsed_args










    # args = [a.strip().replace('=', ':').lower() for a in args]
    # specs: dict[str, str] = {}  # dict of data type: desired data, like 'element': 'explosive'
    # ignored_args: set[str] = set()

    # is_value = False
    # pending_kw = ''
    # value = ''

    # for arg in args:
    #     if is_value:
    #         is_value = False

    #         if ':' not in arg:
    #             specs[pending_kw] = value
    #             continue

    #     if ':' not in arg:
    #         ignored_args.add(arg) # pos args not ressolved yet
    #         continue

    #     if arg.endswith(':'):  # if True, next arg is a value
    #         is_value = True
    #         pending_kw = arg.lstrip(':')

    #     else:
    #         key, value = arg.split(':')
    #         specs[key] = value.strip()

    # return specs, ignored_args


# helper functions for ,stats
def buff(stat: str, enabled: bool, value: int) -> int:
    """Returns a value buffed respectively to stat type"""
    if not enabled:
        return value
    if stat in OPERATIONS['+20%']:
        return round(value * 1.2)
    if stat in OPERATIONS['+40%']:
        return round(value * 1.4)
    if stat in OPERATIONS['reduce']:
        return round(value * 0.8)
    return value


def missing(stat: str, enabled: bool, value: int | None) -> str:
    if value is None:
        return '?'

    return str(buff(stat, enabled, value))


def buff_difference(stat: str, enabled: bool, value: int | None) -> tuple[str, int]:
    """Returns a value buffed respectively to stat type and the difference between it and base"""
    if value is None:
        return '?', 0

    buffed = buff(stat, enabled, value)
    return str(buffed), buffed - value


def default_embed(embed: disnake.Embed, item: ItemDict, divine: bool, buffs_enabled: bool) -> None:
    _min, _max = item['transform_range'].split('-')

    lower = Rarity[_min].level
    upper = Rarity[_max].level

    if upper < 4:
        tier = upper

    else:
        tier = 4 + divine

    colors = list(map(str, Rarity))
    colors[tier] = f'({colors[tier]})'
    embed.add_field(
        name='Transform range: ',
        value=''.join(colors[lower:upper + 1]),
        inline=False)

    spaced = False
    item_stats = ''  # the main string
    cost_stats = {'backfire', 'heaCost', 'eneCost'}

    for stat in item['stats']:
        if stat in cost_stats and not spaced:
            item_stats += '\n'
            spaced = True

        # divine handler
        pool = 'divine' if divine and stat in item['divine'] else 'stats'
        # number range handler
        stat_value: int | list[int] = item[pool][stat]

        if isinstance(stat_value, list):
            # treat [x, 0] and [x] as x
            if len(stat_value) == 1 or stat_value[1] == 0:
                value, diff = buff_difference(stat, buffs_enabled, stat_value[0])
                change = f' **{diff:+}**' if diff else ''

            # otherwise [x, y] becomes "x-y"
            else:
                x, y = stat_value
                v1, d1 = buff_difference(stat, buffs_enabled, x)
                v2, d2 = buff_difference(stat, buffs_enabled, y)

                change = f' **{d1:+} {d2:+}**' if d1 or d2 else ''
                value = f'{v1}-{v2}'

        else:
            value, diff = buff_difference(stat, buffs_enabled, stat_value)
            change = f' **{diff:+}**' if diff else ''

        name, emoji = STAT_NAMES[stat]

        if stat == 'uses':
            name = 'Use' if stat_value == 1 else 'Uses'

        item_stats += f'{emoji} **{value}**{change} {name}\n'

    if 'advance' in item['stats'] or 'retreat' in item['stats']:
        item_stats += f"{STAT_NAMES['jump'].emoji} **Jumping required**"

    note = ' (buffs applied)' if buffs_enabled else ''
    embed.add_field(name=f'Stats{note}:', value=item_stats, inline=False)


def compact_embed(embed: disnake.Embed, item: ItemDict, divine: bool, buffs_enabled: bool) -> None:
    _min, _max = item['transform_range'].split('-')

    lower = Rarity[_min].level
    upper = Rarity[_max].level

    if upper < 4:
        tier = upper

    else:
        tier = 4 + divine

    colors = list(map(str, Rarity))
    colors[tier] = f'({colors[tier]})'
    color_str = ''.join(colors[lower:upper + 1])
    lines = [color_str]

    for stat in item['stats']:
        # divine handler
        pool = 'divine' if divine and stat in item['divine'] else 'stats'
        # number range handler
        stat_value = item[pool][stat]

        if isinstance(stat_value, list):
            if len(stat_value) == 1:
                value = missing(stat, buffs_enabled, stat_value[0])  # handling one spot range

            elif stat_value[1] == 0:
                value = stat_value[0]

            else:
                value = '-'.join(str(missing(stat, buffs_enabled, n)) for n in stat_value)

        else:
            value = missing(stat, buffs_enabled, stat_value)

        lines.append(f'{STAT_NAMES[stat].emoji} **{value}**')

    if 'advance' in item['stats'] or 'retreat' in item['stats']:
        lines.append(f"{STAT_NAMES['jump'].emoji}❗")

    line_count = len(lines)
    div = 4 + (line_count % 5 == 0)

    note = ' (buffed)' if buffs_enabled else ''
    field_text = ('\n'.join(lines[i:i+div]) for i in range(0, line_count, div))
    name_field_zip = zip_longest((f'Stats{note}:',), field_text, fillvalue=NONE_EMOJI)

    for name, field in name_field_zip:
        embed.add_field(name=name, value=field)


def random_str(length: int) -> str:
    return ''.join(random.sample(ascii_letters, length))


class SuperMechs(commands.Cog):
    """Set of commands related to the SuperMechs game."""

    def __init__(self, bot: HostedBot):
        self.bot = bot
        self.image_url_cache: dict[str, str] = {}
        self.no_img:     set[str] = set()
        self.no_stats:   set[str] = set()

        self.player_builds: dict[int, dict[str, Mech]] = {}  # TODO: replace with actual database
        self.players: dict[int, str] = {}


    async def cog_load(self):
        await self.load_item_pack(DEFAULT_PACK_URL)
        self.abbrevs, self.names = self.abbrevs_and_names()


    async def load_item_pack(self, pack_url: str):
        async with self.bot.session.get(pack_url) as response:
            pack = await response.json(encoding='utf-8', content_type=None)

        base_url: str = pack['config']['base_url']
        self.base_url = base_url
        self.item_list: list[ItemDict] = pack['items']
        self.items_dict = {item_dict['name']: Item(base_url=base_url, **item_dict) for item_dict in self.item_list}  # type: ignore


    def create_mech(self, ctx: commands.Context, name: str=None, *, overwrite: bool=False) -> Mech:
        id = ctx.author.id
        player_dict = self.player_builds.setdefault(id, {})

        if name is None:
            name = random_str(6)

            while name in player_dict:
                name = random_str(6)

        elif name in player_dict and not overwrite:
            raise ValueError('Name already in the dict')

        new = Mech()
        player_dict[name] = new
        self.players[id] = name  # set current mech to newly created
        return new


    def get_current_mech(self, ctx: commands.Context) -> Mech:
        id = ctx.author.id

        if id in self.players:
            return self.player_builds[id][self.players[id]]

        return self.create_mech(ctx)


    def swap_mech(self, ctx: commands.Context, name: str) -> None:
        id = ctx.author.id

        if id not in self.players:
            raise ValueError

        self.players[id] = name


    def abbrevs_and_names(self) -> tuple[dict[str, list[str]], dict[str, ItemDict]]:
        """Returns dict of abbrevs and dict of names and items:
        Energy Free Armor => EFA"""
        items:   dict[str, ItemDict] = {}
        abbrevs: dict[str, list[str]] = {}

        for item in self.item_list:
            name = item['name']
            items[name.lower()] = item

            if len(name) < 8:
                continue

            if (IsNotPascal := name[1:].islower()) and ' ' not in name:
                continue

            abbrev = [''.join(a for a in name if a.isupper()).lower()]

            if not IsNotPascal and ' ' not in name: # takes care of PascalCase names
                last = 0
                for i, a in enumerate(name):
                    if a.isupper():
                        string = name[last:i].lower()
                        if string:
                            abbrev.append(string)

                        last = i

                abbrev.append(name[last:].lower())

            for abb in abbrev:
                abbrevs.setdefault(abb, [name]).append(name)

        return abbrevs, items


    async def get_image_url(self, item: ItemDict) -> str:
        if item['name'] in self.image_url_cache:
            return self.image_url_cache[item['name']]

        if item['name'] in LOCAL_IMAGES:
            return LOCAL_IMAGES[item['name']]

        if 'image' in item and self.base_url is not None:
            url = js_format(item['image'], url=self.base_url)
            self.image_url_cache[item['name']] = url
            return url

        safe_name = item['name'].replace(' ', '')

        for url_temp in IMAGE_LINK_TEMPLATES:
            url = url_temp.format(safe_name)

            try:
                async with self.bot.session.head(url, raise_for_status=True):
                    break

            except aiohttp.ClientResponseError:
                continue

        else:
            self.no_img.add(item['name'])
            url = ''

        self.image_url_cache[item['name']] = url
        return url


    @commands.command(aliases=['missno'])
    @commands.is_owner()
    async def missingimages(self, ctx: commands.Context, scan: bool=False):
        """Debug command; returns names of items that don't have an image"""
        if scan:
            start = time.time()

            async with ctx.typing():
                tasks = {
                    self.get_image_url(item) for item in self.item_list
                    if item['name'] not in self.no_img
                    if item['name'].replace(' ', '') not in self.image_url_cache}

                await asyncio.wait(tasks, return_when='ALL_COMPLETED')

            time_taken = f', {round(time.time() - start, 1)}s'

        else:
            time_taken = ''

        text = (f'```\n{self.no_img}```\n' if self.no_img else r'{}') + \
                f'({len(self.no_img)}/{len(self.image_url_cache)}/{len(self.item_list)}){time_taken}'

        await ctx.send(text)


    @commands.command()
    async def frantic(self, ctx: commands.Context):
        """Show to a frantic user where is his place"""
        frantics = ['https://i.imgur.com/Bbbf4AH.mp4', 'https://i.gyazo.com/8f85e9df5d3b1ed16b3c81dc3bccc3e9.mp4']
        choice = random.choice(frantics)
        await ctx.send(choice)


    @spam_command()
    @commands.command(aliases=['item'], usage='[full item name or part of it]')
    async def stats(self, ctx: commands.Context, *name_parts: str):
        """Finds an item and returns its stats"""
        flags, iterable = filter_flags({'-r', '-c'}, name_parts)
        name = ' '.join(iterable).lower()

        if len(name) < 2:
            raise commands.UserInputError(
                'Name / abbreviation needs to be 3+ characters long.'
                if name else
                'No item name or abbreviation passed.')

        # returning the exact item name from short user input
        botmsg = None

        if name not in self.names:  # not a valid name, lookup by abreviations
            matches = set(search_for(name, self.names)) | set(self.abbrevs.get(name, []))

            if number := len(matches):
                if number > 10:
                    await ctx.send('Over 10 matches found, be more specific.')
                    return

                if number > 1:
                    sorted_matches = sorted(matches)
                    embed = make_choice_embed(ctx, sorted_matches)
                    botmsg = await ctx.send(embed=embed)

                    try:
                        reply = await get_message(ctx, timeout=20)

                    except asyncio.TimeoutError:
                        await botmsg.add_reaction('⏰')
                        return

                    try:
                        name = sorted_matches[int(reply.content) - 1]

                    except IndexError:
                        await reply.add_reaction('❔')
                        return

                    await reply.delete()

                # only 1 match found
                else:
                    name, = matches

        # getting the item
        item = self.names.get(name, None)

        if item is None:
            for item in self.item_list:
                if item['name'].lower() == name.lower():
                    break

            else:
                raise commands.UserInputError('Item not found.')

            self.names[name] = item

        # debug flag
        if '-r' in flags:
            await ctx.send(f'`{item}`')
            return

        emojis = ['🇧', '❌']

        if 'divine' in item:
            emojis.insert(1, '🇩')

        # embedding
        desc = f"{item['element'].capitalize()} {item['type'].replace('_', ' ').lower()}"
        embed = EmbedUI(emojis, title=item['name'], desc=desc, color=Elements[item['element']].color)
        img_url = await self.get_image_url(item)

        # check for http so we don't make unnecessary IO access
        if not img_url.startswith('http') and os.path.isfile(img_url):
            file = disnake.File(img_url, filename="image.png")
            img_url = 'attachment://image.png'

        else:
            file = None

        if '-c' in flags:
            if file:
                embed.set_image(url=img_url)
                embed.set_thumbnail(url=Icons[item['type']].URL)

            else:
                embed.set_thumbnail(url=img_url or Icons[item['type']].URL)

            prepare_embed = compact_embed

        else:
            embed.set_thumbnail(url=Icons[item['type']].URL)
            prepare_embed = default_embed

            if img_url:
                embed.set_image(url=img_url)

        embed.set_author(name=f'Requested by {ctx.author.display_name}', icon_url=ctx.author.display_avatar)
        embed.set_footer(text='Toggle arena buffs with B' + ' and divine stats with D' * ('🇩' in emojis))
        # adding item stats

        divine = buffs_enabled = False
        prepare_embed(embed, item, divine, buffs_enabled)

        view = View()
        # view.add_item(ToggleButton(label='Buffs'))

        if botmsg is not None:
            msg = await botmsg.edit(embed=embed, view=view)

        elif file is None:
            msg = await ctx.send(embed=embed, view=view)

        else:
            msg = await ctx.send(embed=embed, view=view, file=file)


        embed.msg = msg
        await embed.add_options(add_cancel=True)

        def pred(r: disnake.Reaction, u: disnake.Member):
            return u == ctx.author and r.message == msg and str(r) in emojis

        # -------------------------------------------- main loop --------------------------------------------
        while True:
            try:
                ((react, _), event), = await scheduler(ctx, {'reaction_add', 'reaction_remove'}, pred, 20.0)
                react: disnake.Reaction

            except asyncio.TimeoutError:
                break

            action_type = event == 'reaction_add'
            reaction = str(react)

            if reaction == '❌':
                break

            embed.clear_fields()

            if reaction == '🇩':
                divine = action_type

            else:
                buffs_enabled = action_type

            prepare_embed(embed, item, divine, buffs_enabled)
            await embed.edit()

        await msg.edit(embed=embed.set_footer())
        await msg.clear_reactions()


    @commands.command(aliases=['bi', 'smlookup'])
    async def browseitems(self, ctx: commands.Context, *, args: str):
        """Lookup items by rarity, element and type"""
        preparsed = map(str.strip, args.split(','))
        parse_kwargs(preparsed)


    @commands.command()
    @commands.is_owner()
    async def fetch(self, ctx: commands.Context, url: str):
        """Forces to update the item list"""
        await self.load_item_pack(url)
        await ctx.message.add_reaction('✅')


    @commands.group(invoke_without_command=True)
    async def mech(self, ctx: commands.Context, name: Optional[str]):
        id = ctx.author.id

        if name is None:
            mech = self.get_current_mech(ctx)
            name = self.players[id]

        elif id not in self.players:
            mech = self.create_mech(ctx, name)

        else:
            try:
                mech = self.player_builds[id][name]

            except KeyError:
                raise commands.UserInputError('Name not found.') from None

        embed = disnake.Embed(title=f'Mech build "{name}"', description=str(mech), color=ctx.author.color)
        embed.add_field(name='Stats:', value=mech.display_stats)

        if mech.torso is None:
            await ctx.send(embed=embed)
            return

        embed.color = mech.torso.element.color
        filename = f'{self.players[id]}.png'
        embed.set_image(url=f'attachment://{filename}')

        async with ctx.typing():
            await mech.load_images(self.bot.session)
            file = image_to_file(mech.image, filename)
            await ctx.send(embed=embed, file=file)


    @mech.command(name='list')
    async def browse(self, ctx: commands.Context):
        id = ctx.author.id

        if id not in self.players:
            await ctx.send('You do not have any mech builds.')
            return

        string = '\n\n'.join(f'**{name}**:\n{build}' for name, build in self.player_builds[id].items())

        await ctx.send(string)


    @mech.command()
    async def new(self, ctx: commands.Context, name: str):
        """Creates a new mech with given name, and sets it as default"""
        try:
            self.create_mech(ctx, name)

        except ValueError:
            await ctx.send('Name already exists')

        else:
            await ctx.message.add_reaction('✅')


    @mech.command()
    async def edit(self, ctx: commands.Context, *name_parts: str):
        """Edits a part of current mech"""
        name = ' '.join(name_parts).lower()
        names = list(s.strip() for s in name.split(','))

        botmsg: disnake.Message | None = None
        failed: list[str] = []

        mech = self.get_current_mech(ctx)

        for string in names:
            if string[0].isdigit():
                num, string = string.split(' ', 1)
                pos = int(num)

            else:
                pos = None

            name = string.strip()

            if name not in self.names:  # not a valid name, lookup by abreviations
                matches = set(search_for(name, self.names)) | set(self.abbrevs.get(name, []))

                if number := len(matches):
                    if number > 10:
                        await ctx.send('Over 10 matches found, be more specific.')
                        return

                    if number > 1:
                        sorted_matches = sorted(matches)
                        embed = make_choice_embed(ctx, sorted_matches)

                        if botmsg is not None:
                            await botmsg.edit(embed=embed)

                        else:
                            botmsg = await ctx.send(embed=embed)

                        try:
                            reply = await get_message(ctx, timeout=20)

                        except asyncio.TimeoutError:
                            await botmsg.add_reaction('⏰')
                            return

                        try:
                            name = sorted_matches[int(reply.content) - 1]

                        except IndexError:
                            await reply.add_reaction('❔')
                            failed.append(name)
                            continue

                        await reply.delete()

                    # only 1 match found
                    else:
                        name, = matches

            # getting the item
            item_dict = self.names.get(name, None)

            if item_dict is None:
                for item_dict in self.item_list:
                    if item_dict['name'].lower() == name.lower():
                        break

                else:
                    failed.append(name)
                    continue

                self.names[name] = item_dict

            item = Item(**item_dict)  # type: ignore
            item.image_url = await self.get_image_url(item_dict)

            if pos is None:
                mech[item_dict['type']] = item

            else:
                mech[item_dict['type'], pos] = item

        if botmsg is not None:
            await botmsg.delete()

        if failed:
            await ctx.send('Failed to add: ' + ', '.join(f'"{item}"' for item in failed))

        else:
            await ctx.message.add_reaction('✅')


    @mech.command()
    async def build(self, ctx: commands.Context):
        id = ctx.author.id
        mech = self.get_current_mech(ctx)
        name = self.players[id]
        embed = disnake.Embed(title=f'Mech build "{name}"', color=ctx.author.color if mech.torso is None else mech.torso.element.color)
        embed.add_field(name='Stats:', value=mech.display_stats)

        async def callback(inter: disnake.MessageInteraction):
            embed.set_field_at(0, name='Stats:', value=mech.display_stats)

            if mech.torso is None:
                return {'embed': embed}

            embed.color = mech.torso.element.color
            filename = random_str(8) + '.png'

            await mech.load_images(self.bot.session)
            file = image_to_file(mech.image, filename)
            embed.set_image(url=f'attachment://{filename}')
            return {'embed': embed, 'file': file, 'attachments': []}

        view = MechView(mech, self.items_dict, callback)
        await ctx.send(embed=embed, view=view)



    @commands.command()
    @commands.is_owner()
    async def debug(self, ctx: commands.Context):

        mech = self.get_current_mech(ctx)
        breakpoint()
        # await ctx.send(mech.__dict__)


def setup(bot: HostedBot):
    bot.add_cog(SuperMechs(bot))
    print('SM loaded')
