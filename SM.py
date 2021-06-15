from __future__ import annotations


import asyncio
from itertools import zip_longest
import random
import time
from typing import *  # type: ignore


import aiohttp
import discord
from discord.ext import commands


from config import IMAGE_LINK_TEMPLATES, ITEMS_JSON_LINK, NONE_EMOJI
from discotools import perms, EmbedUI, scheduler, spam_command, make_choice_embed, user_choice
from functions import search_for, split_to_fields, filter_flags


OPERATIONS = {
    '+20%':  {'eneCap', 'heaCap', 'eneReg', 'heaCap', 'heaCol', 'phyDmg', 'expDmg', 'eleDmg', 'heaDmg', 'eneDmg'},
    '+40%': {'phyRes', 'expRes', 'eleRes'},
    'reduce': {'backfire'}}
ITEM_TYPES = {
    'TOP_WEAPON':  ('https://i.imgur.com/LW7ZCGZ.png',   '<:topr:730115786735091762>'),
    'SIDE_WEAPON': ('https://i.imgur.com/CBbvOnQ.png',  '<:sider:730115747799629940>'),
    'TORSO':       ('https://i.imgur.com/iNtSziV.png',  '<:torso:730115680363347968>'),
    'LEGS':        ('https://i.imgur.com/6NBLOhU.png',   '<:legs:730115699397361827>'),
    'DRONE':       ('https://i.imgur.com/oqQmXTF.png',  '<:drone:730115574763618394>'),
    'CHARGE':      ('https://i.imgur.com/UnDqJx8.png', '<:charge:730115557239685281>'),
    'TELEPORTER':  ('https://i.imgur.com/Fnq035A.png',   '<:tele:730115603683213423>'),
    'HOOK':        ('https://i.imgur.com/8oAoPcJ.png',   '<:hook:730115622347735071>'),
    'MODULE':      ('https://i.imgur.com/dQR8UgN.png',    '<:mod:730115649866694686>')}
TIER_COLORS = ('⚪', '🔵', '🟣', '🟠', '🟤', '⚪')
ITEM_TIERS  = ('C',   'R',   'E',  'L',   'M',  'D')
TIERS_TO_COLORS = dict(zip(ITEM_TIERS, TIER_COLORS))
SLOT_EMOJIS = {
    'topl':   '<:topl:730115768431280238>',
    'topr':   '<:topr:730115786735091762>',
    'dron':  '<:drone:730115574763618394>',
    'sidl':  '<:sidel:730115729365663884>',
    'sidr':  '<:sider:730115747799629940>',
    'tors':  '<:torso:730115680363347968>',
    'legs':   '<:legs:730115699397361827>',
    'chrg': '<:charge:730115557239685281>',
    'tele':   '<:tele:730115603683213423>',
    'hook':   '<:hook:730115622347735071>',
    'modl':    '<:mod:730115649866694686>',
    'none': NONE_EMOJI}
STAT_NAMES = {
    'weight':    ['Weight',                    '<:weight:725870760484143174>'],
    'health':    ['HP',                        '<:health:725870887588462652>'],
    'eneCap':    ['Energy',                    '<:energy:725870941883859054>'],
    'eneReg':    ['Regeneration',               '<:regen:725871003665825822>'],
    'heaCap':    ['Heat',                        '<:heat:725871043767435336>'],
    'heaCol':    ['Cooling',                  '<:cooling:725871075778363422>'],
    'phyRes':    ['Physical resistance',       '<:phyres:725871121051811931>'],
    'expRes':    ['Explosive resistance',      '<:expres:725871136935772294>'],
    'eleRes':    ['Electric resistance',      '<:elecres:725871146716758077>'],
    'phyDmg':    ['Damage',                    '<:phydmg:725871208830074929>'],
    'phyResDmg': ['Resistance drain',       '<:phyresdmg:725871259635679263>'],
    'expDmg':    ['Damage',                    '<:expdmg:725871223338172448>'],
    'heaDmg':    ['Heat damage',               '<:headmg:725871613639393290>'],
    'heaCapDmg': ['Heat capacity drain',   '<:heatcapdmg:725871478083551272>'],
    'heaColDmg': ['Cooling damage',        '<:coolingdmg:725871499281563728>'],
    'expResDmg': ['Resistance drain',       '<:expresdmg:725871281311842314>'],
    'eleDmg':    ['Damage',                    '<:eledmg:725871233614479443>'],
    'eneDmg':    ['Energy drain',              '<:enedmg:725871599517171719>'],
    'eneCapDmg': ['Energy capacity drain',  '<:enecapdmg:725871420126789642>'],
    'eneRegDmg': ['Regeneration damage',     '<:regendmg:725871443815956510>'],
    'eleResDmg': ['Resistance drain',       '<:eleresdmg:725871296381976629>'],
    'range':     ['Range',                      '<:range:725871752072134736>'],
    'push':      ['Knockback',                   '<:push:725871716613488843>'],
    'pull':      ['Pull',                        '<:pull:725871734141616219>'],
    'recoil':    ['Recoil',                    '<:recoil:725871778282340384>'],
    'retreat':   ['Retreat',                  '<:retreat:725871804236955668>'],
    'advance':   ['Advance',                  '<:advance:725871818115907715>'],
    'walk':      ['Walking',                     '<:walk:725871844581834774>'],
    'jump':      ['Jumping',                     '<:jump:725871869793796116>'],
    'uses':      ['',                            '<:uses:725871917923303688>'],  # special case so the text has singular & plural forms
    'backfire':  ['Backfire',                '<:backfire:725871901062201404>'],
    'heaCost':   ['Heat cost',                '<:heatgen:725871674007879740>'],
    'eneCost':   ['Energy cost',             '<:eneusage:725871660237979759>']}
ELEMENTS = {'PHYSICAL':  (0xffb800, STAT_NAMES['phyDmg'][1]),
            'EXPLOSIVE': (0xb71010, STAT_NAMES['expDmg'][1]),
            'ELECTRIC':  (0x106ed8, STAT_NAMES['eleDmg'][1]),
            'COMBINED':  (0x211d1d, '🔰')}
ELEMENTS: dict[str, tuple[int, str]]


class AnyStats(TypedDict, total=False):
    weight: int
    health: int
    eneCap: int
    eneReg: int
    heaCap: int
    heaCol: int
    bulletCap: int
    rocketCap: int
    phyRes: int
    expRes: int
    eleRes: int
    phyDmg: tuple[int, int]
    phyResDmg: int
    eleDmg: tuple[int, int]
    eneDmg: int
    eneCapDmg: int
    eneRegDmg: int
    eleResDmg: int
    expDmg: tuple[int, int]
    heaDmg: int
    heaCapDmg: int
    heaColDmg: int
    expResDmg: int
    walk: int
    jump: int
    range: tuple[int, int]
    push: int
    pull: int
    recoil: int
    advance: int
    retreat: int
    uses: int
    backfire: int
    heaCost: int
    eneCost: int
    bulletCost: int
    rocketCost: int



class ItemDict(TypedDict):
    name: str
    type: str
    element: str
    transform_range: str
    stats:  AnyStats
    divine: AnyStats



def ressolve_kwargs(args: Iterable[str]) -> tuple[dict[str, str], set[str]]:
    """Takes command arguments as an input and tries to match them as key item pairs"""
    if isinstance(args, str):
        args = args.split()

    args = [a.strip().replace('=', ':').lower() for a in args]
    specs: dict[str, str] = {}  # dict of data type: desired data, like 'element': 'explosive'
    ignored_args: set[str] = set()

    is_value = False
    pending_kw = ''
    value = ''

    for arg in args:
        if is_value:
            is_value = False

            if ':' not in arg:
                specs[pending_kw] = value
                continue

        if ':' not in arg:
            ignored_args.add(arg) # pos args not ressolved yet
            continue

        if arg.endswith(':'):  # if True, next arg is a value
            is_value = True
            pending_kw = arg.lstrip(':')

        else:
            key, value = arg.split(':')
            specs[key] = value.strip()

    return specs, ignored_args


def get_specs(item: ItemDict) -> dict[str, str]:
    return {'type':  ITEM_TYPES[item['type']][1],
            'element': ELEMENTS[item['element']][1],
            'tier': TIERS_TO_COLORS[item['transform_range'].split('-')[0]]}


def emoji_for_browseitems(specs: dict[str, str], spec_filter: Container[str]) -> str:
    return ''.join(v for k, v in specs.items() if k not in spec_filter)


# helper functions for ,stats
def buff(stat: str, enabled: bool, value: int | None) -> int | str:
    """Returns a value buffed respectively to stat type"""
    if value is None:
        return '?'
    if not enabled:
        return value
    if stat in OPERATIONS['+20%']:
        return round(value * 1.2)
    if stat in OPERATIONS['+40%']:
        return round(value * 1.4)
    if stat in OPERATIONS['reduce']:
        return round(value * 0.8)
    return value


def default_embed(embed: EmbedUI, item: ItemDict, divine: bool, buffs_enabled: bool) -> None:
    _min, _max = item['transform_range'].split('-')

    if (maximal := ITEM_TIERS.index(_max)) < 4:
        tier = maximal

    else:
        tier = 4 + divine

    colors = list(TIER_COLORS)
    colors[tier] = f'({colors[tier]})'
    embed.add_field(
        name='Transform range: ', 
        value=''.join(colors[ITEM_TIERS.index(_min):ITEM_TIERS.index(_max)+1]),
        inline=False)

    spaced = False
    item_stats = ''  # the main string

    for stat in item['stats']:
        if stat in {'backfire', 'heaCost', 'eneCost'} and not spaced:
            item_stats += '\n'
            spaced = True

        # divine handler
        pool = 'divine' if divine and stat in item['divine'] else 'stats'
        # number range handler
        stat_value = item[pool][stat]

        if isinstance(stat_value, list):
            if len(stat_value) == 1:
                value = buff(stat, buffs_enabled, stat_value[0])  # handling one spot range

            elif stat_value[1] == 0:
                value = stat_value[0]

            else:
                value = '-'.join(str(buff(stat, buffs_enabled, n)) for n in stat_value)

        else:
            value = buff(stat, buffs_enabled, stat_value)

        item_stats += f'{STAT_NAMES[stat][1]} **{value}** {STAT_NAMES[stat][0]}\n'

    if 'advance' in item['stats'] or 'retreat' in item['stats']:
        item_stats += f"{STAT_NAMES['jump'][1]} **Jumping required**"

    note = ' (buffs applied)' if buffs_enabled else ''
    embed.add_field(name=f'Stats{note}:', value=item_stats, inline=False)


def compact_embed(embed: EmbedUI, item: ItemDict, divine: bool, buffs_enabled: bool) -> None:
    _min, _max = item['transform_range'].split('-')

    if (maximal := ITEM_TIERS.index(_max)) < 4:
        tier = maximal

    else:
        tier = 4 + divine

    colors = list(TIER_COLORS)
    colors[tier] = f'({colors[tier]})'
    color_str = ''.join(colors[ITEM_TIERS.index(_min):ITEM_TIERS.index(_max)+1])
    lines = [color_str]

    for stat in item['stats']:
        # divine handler
        pool = 'divine' if divine and stat in item['divine'] else 'stats'
        # number range handler
        stat_value = item[pool][stat]

        if isinstance(stat_value, list):
            if len(stat_value) == 1:
                value = buff(stat, buffs_enabled, stat_value[0])  # handling one spot range

            elif stat_value[1] == 0:
                value = stat_value[0]

            else:
                value = '-'.join(str(buff(stat, buffs_enabled, n)) for n in stat_value)

        else:
            value = buff(stat, buffs_enabled, stat_value)

        lines.append(f'{STAT_NAMES[stat][1]} **{value}**')

    if 'advance' in item['stats'] or 'retreat' in item['stats']:
        lines.append(f"{STAT_NAMES['jump'][1]}❗")

    line_count = len(lines)
    div = 4 + (line_count % 5 == 0)

    note = ' (buffed)' if buffs_enabled else ''
    field_text = ('\n'.join(lines[i:i+div]) for i in range(0, line_count, div))
    name_field_zip = zip_longest((f'Stats{note}:',), field_text, fillvalue=NONE_EMOJI)

    for name, field in name_field_zip:
        embed.add_field(name=name, value=field)



class SuperMechs(commands.Cog):
    """Set of commands related to the SuperMechs game."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.image_url_cache: dict[str, str] = {}
        self.no_img:     set[str] = set()
        self.no_stats:   set[str] = set()
        self.abbrevs:    dict[str, list[str]] = {}
        self.items_dict: dict[str, ItemDict] = {}
        self.session = aiohttp.ClientSession()
        self.bot.loop.create_task(self.get_item_list()).add_done_callback(self.callback)


    def cog_unload(self):
        if not self.session.closed:
            self.bot.loop.create_task(self.session.close())


    def callback(self, *_):
        self.abbrevs, self.names = self.abbrevs_and_names()


    async def get_item_list(self):
        async with self.session.get(ITEMS_JSON_LINK) as response:
            self.item_list: list[ItemDict] = await response.json(encoding='utf-8', content_type=None)


    def abbrevs_and_names(self) -> tuple[dict[str, list[str]], dict[str, ItemDict]]:
        """Returns dict of abbrevs and dict of names and items:
        Energy Free Armor => EFA"""
        items:   dict[str, ItemDict] = {}
        abbrevs: dict[str, list[str]] = {}

        for item in self.item_list:
            name = item['name']
            items[name] = item

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


    async def get_image(self, item: ItemDict) -> str:
        if item['name'] in self.image_url_cache:
            return self.image_url_cache[item['name']]

        safe_name = item['name'].replace(' ', '')

        for url_temp in IMAGE_LINK_TEMPLATES:
            url = url_temp.format(safe_name)

            try:
                async with self.session.head(url, raise_for_status=True):
                    break

            except aiohttp.ClientResponseError:
                continue

        else:
            self.no_img.add(item['name'])
            url = ''

        self.image_url_cache[item['name']] = url
        return url


    @commands.command(aliases=['missno'])
    @perms(5)
    async def missingimages(self, ctx: commands.Context, scan: bool=False):
        """Debug command; returns names of items that don't have an image"""
        if scan:
            start = time.time()
            async with ctx.typing():
                for item in self.item_list:
                    if item['name'] in self.no_img:
                        continue

                    elif item['name'].replace(' ', '') in self.image_url_cache:
                        continue

                    await self.get_image(item)
            total = round(time.time() - start)
            txt = f', {total}s'

        else:
            txt = ''

        text = (f'```\n{self.no_img}```\n' if self.no_img else ''
                f'({len(self.no_img)}/{len(self.image_url_cache)}/{len(self.item_list)}){txt}')

        await ctx.send(text)


    @commands.command()
    async def frantic(self, ctx: commands.Context):
        """Show to a frantic user where is his place"""
        frantics = ['https://i.imgur.com/Bbbf4AH.mp4', 'https://i.gyazo.com/8f85e9df5d3b1ed16b3c81dc3bccc3e9.mp4']
        choice = random.choice(frantics)
        # embed = discord.Embed(type='video', url=choice)
        # embed = discord.Embed.from_dict({'url': choice, 'video': {
        #                                 'url': choice, 'width': 1204, 'height': 720}})
        await ctx.send(choice)
        # await ctx.send(embed=embed)


    @spam_command()
    @commands.command(aliases=['item'], usage='[full item name or part of it]')
    async def stats(self, ctx: commands.Context, *name_parts: str):
        """Finds an item and returns its stats"""
        add_r = ctx.message.add_reaction
        flags, iterable  = filter_flags({'-r', '-c'}, name_parts)
        name = ' '.join(iterable).lower()

        if len(name) < 2:
            await add_r('❌')
            return

        if not self.abbrevs or not self.names:
            self.callback()

        # returning the exact item name from short user input
        botmsg = None

        if name not in self.names:
            results = search_for(name, self.names)
            abbrev = self.abbrevs.get(name, [])
            matches = sorted(set(results + abbrev))

            if matches:
                number = len(matches)

                if number > 10:
                    await ctx.send('Over 10 matches found, be more specific.')
                    return
                # more than 1 match found
                if number > 1:
                    embed = make_choice_embed(ctx, matches)
                    botmsg, result = await user_choice(ctx, matches, {'embed': embed}, timeout=20)

                    if result is None:
                        return

                    name = result

                # only 1 match found
                else:
                    name = matches[0]

        # getting the item
        item = self.names.get(name, None)

        if item is None:
            for item in self.item_list:
                if item['name'].lower() == name.lower():
                    break

            else:
                await add_r('❌')
                return

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
        embed = EmbedUI(emojis, title=item['name'], desc=desc, color=ELEMENTS[item['element']][0])
        img_url = await self.get_image(item)

        if '-c' in flags:
            embed.set_thumbnail(url=img_url or ITEM_TYPES[item['type']][0])
            prepare_embed = compact_embed

        else:
            embed.set_thumbnail(url=ITEM_TYPES[item['type']][0])
            prepare_embed = default_embed

            if img_url:
                embed.set_image(url=img_url)

        embed.set_author(name=f'Requested by {ctx.author.display_name}', icon_url=str(ctx.author.avatar_url))
        embed.set_footer(text='Toggle arena buffs with B' + ' and divine stats with D' * ('🇩' in emojis))
        STAT_NAMES['uses'][0] = 'Use' if item['stats'].get('uses', None) == 1 else 'Uses'
        # adding item stats

        divine = buffs_enabled = False

        def pred(r: discord.Reaction, u: discord.Member):
            return u == ctx.author and r.message == msg and str(r) in emojis

        prepare_embed(embed, item, divine, buffs_enabled)

        if botmsg is not None:
            await botmsg.edit(embed=embed)
            msg = botmsg

        else:
            msg = await ctx.send(embed=embed)

        embed.msg = msg
        await embed.add_options(add_cancel=True)

        # -------------------------------------------- main loop --------------------------------------------
        while True:
            try:
                (react, _), event = (await scheduler(ctx, {'reaction_add', 'reaction_remove'}, pred, 20.0)).pop()
                react: discord.Reaction

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


    @commands.command(aliases=['bi', 'smlookup'],
        usage='[type:[tors/top/side/.../dron], elem:[exp/elec/phys/combined], tier:[C-D]]')
    async def browseitems(self, ctx: commands.Context, *args: str):
        """Lookup items by rarity, element and type"""
        specs, _ = ressolve_kwargs(args)

        valid_specs: dict[str, str] = {}
        search_keys = ('type', 'element', 'tier')

        for key, value in specs.items():
            result = search_for(key, search_keys)

            if not result or len(result) > 1:
                await ctx.send(
                    'Argument must match exactly one data type; '
                    f'"{key}" matched {result or "nothing"}')
                return

            key = result[0]
            spec = (ITEM_TYPES, ELEMENTS, ITEM_TIERS)[search_keys.index(key)]

            values = search_for(value, spec)

            if len(values) != 1:
                val = bool(values)
                await ctx.send(
                    f'Value "{value}" for parameter "{key}" has '
                    f'{("no", "too many")[val]} matches{": " * val}{", ".join(values).lower()}')
                return

            valid_specs.update({key: values[0]})

        if not valid_specs:
            raise commands.BadArgument('No valid arguments were given.')

        items: list[ItemDict] = []
        for item in self.item_list:
            matching_specs = set()
            for key, value in valid_specs.items():
                if key == 'tier':
                    _min, _max = item['transform_range'].split('-')
                    _range = ITEM_TIERS[ITEM_TIERS.index(_min):ITEM_TIERS.index(_max) + 1]
                    matching_specs.add(value in _range and not _range.index(value))
                    continue

                matching_specs.add(item[key] == value)

            if all(matching_specs):
                items.append(item)

        if not items:
            await ctx.send('No items matching criteria.')
            return

        tiers_rev_ordered = (*reversed(ITEM_TIERS),)
        elements_ordered  = (*ELEMENTS.keys(),)

        def sort_by_tier_elem_name(item: ItemDict) -> tuple[int, int, str]:
            return (
                tiers_rev_ordered.index(item['transform_range'][0]),
                elements_ordered.index(item['element']),
                item['name'])

        items.sort(key=sort_by_tier_elem_name)

        item_names = [f"{emoji_for_browseitems(get_specs(item), valid_specs)} {item['name']}" for item in items]
        fields = split_to_fields(item_names, 1, field_limit=1024)

        if 'element' in valid_specs:
            color = ELEMENTS[valid_specs['element']][0]

        elif 'tier' in valid_specs:
            color = {'C': 0xB1B1B1, 'R': 0x55ACEE, 'E': 0xCC41CC,
                     'L': 0xE0A23C, 'M': 0xFE6333, 'D': 0xFFFFFF}[valid_specs['tier']]

        else:
            color = discord.Color.random()

        embed = discord.Embed(
            title=f'Matching items ({len(items)})',
            description='\n'.join(f"{spec.capitalize().replace('_', ' ')}: {get_specs(items[0])[spec]}" for spec in valid_specs),
            color=color)

        embed.set_author(name=f'Requested by {ctx.author.display_name}', icon_url=str(ctx.author.avatar_url))

        for field in fields:
            embed.add_field(name=NONE_EMOJI, value='\n'.join(field), inline=True)
            if len(embed) > 6000:
                x = sum(len(field) for field in fields[fields.index(field):])
                embed.set_field_at(index=-1, name=NONE_EMOJI, value=f'...and {x} more', inline=False)
                break

        embed.set_footer(text=f'Character count: {len(embed) + 17}')
        await ctx.send(embed=embed)


    @spam_command()
    @commands.command(aliases=['MB'])
    async def mechbuilder(self, ctx: commands.Context, *args: str):
        """WIP command, currently on hold"""
        title = 'Mech builder' #'      ' <-- invisible non-space char
        icon = SLOT_EMOJIS
        none, mods = icon['none'], icon['modl'] * 2
        desc = (
            'Addresing items: `Weapon[n]:` `[name]`, `Module[n]:` `[name]`, `Torso:` `[name]` etc'
            f"\n`1` – {icon['topl']}{icon['dron']}{icon['topr']} – `2`{none}`1` – {mods} – `5`"
            f"\n`3` – {icon['sidl']}{icon['tors']}{icon['sidr']} – `4`{none}`2` – {mods} – `6`"
            f"\n`5` – {icon['sidl']}{icon['legs']}{icon['sidr']} – `6`{none}`3` – {mods} – `7`"
            f"\n`C` – {icon['chrg']}{icon['tele']}{icon['hook']} – `H`{none}`4` – {mods} – `8`")
        embed = discord.Embed(title=title, description=desc)
        await ctx.send(embed=embed)


    @commands.command()
    @perms(5)
    async def fetch(self, ctx: commands.Context):
        """Forces to update the item list"""
        await self.get_item_list()
        await ctx.message.add_reaction('✅')


def setup(bot: commands.Bot):
    bot.add_cog(SuperMechs(bot))
    print('SM loaded')
