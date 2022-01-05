from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable, Coroutine, Generic, TypeVar

import aiohttp
import disnake
from disnake import ButtonStyle, SelectOption
from disnake.ui import Button, Select, View, button, select
from disnake.ui.item import DecoratedItem
from disnake.ui.item import Item as UIItem
from disnake.ui.item import ItemCallbackType
from disnake.utils import MISSING

from enums import STAT_NAMES, Elements, Icons
from images import image_to_file
from SM_classes import AnyItem, ArenaBuffs, InvItem, Mech
from utils import random_str

T = TypeVar('T')
I = TypeVar('I', bound=UIItem)
V = TypeVar('V', bound=View, covariant=True)

Callback = Callable[[I, disnake.MessageInteraction], Coroutine[Any, Any, None]]


def button_cls(*, cls: type[I] = Button, **kwargs: Any) -> Callable[[ItemCallbackType[I]], DecoratedItem[I]]:
    """A decorator that works like `disnake.ui.button`,
    but allows for custom Button subclasses."""

    def decorator(func: ItemCallbackType[I]) -> DecoratedItem[I]:
        if not inspect.iscoroutinefunction(func):
            raise TypeError("button function must be a coroutine function")

        func.__discord_ui_model_type__ = cls
        func.__discord_ui_model_kwargs__ = kwargs
        return func  # type: ignore

    return decorator


trans_table = {
    'top1': 'top_weapon',
    'top2': 'top_weapon',
    'side1': 'side_weapon',
    'side2': 'side_weapon',
    'side3': 'side_weapon',
    'side4': 'side_weapon',
    'mod1': 'module',
    'mod2': 'module',
    'mod3': 'module',
    'mod4': 'module',
    'mod5': 'module',
    'mod6': 'module',
    'mod7': 'module',
    'mod8': 'module'}


def translate_type(_type: str) -> str:
    if _type.startswith(('side', 'top')):
        return ('TOP_' if _type.startswith('top') else 'SIDE_') + (
            'LEFT' if int(_type[-1]) % 2 else 'RIGHT')

    if _type.startswith('mod'):
        return 'MODULE'

    return _type.upper()


async def no_op(*args: Any, **kwargs: Any) -> None:
    """Awaitable that does nothing."""
    return


EMPTY_OPTION = SelectOption(label='empty', description='Select to remove', emoji='🗑️')


class ToggleButton(Button[V]):
    """A two-state button."""
    custom_id: str
    view: V

    def __init__(
        self,
        *,
        style_off: ButtonStyle = ButtonStyle.secondary,
        style_on:  ButtonStyle = ButtonStyle.success,
        callback: Callback[ToggleButton] = no_op,
        on: bool = False,
        **kwargs: Any
    ) -> None:
        kwargs.setdefault('style', style_on if on else style_off)
        super().__init__(**kwargs)
        self.style_off = style_off
        self.style_on = style_on
        self.call = callback

    def toggle(self) -> None:
        """Toggles the state of the button between on and off."""
        self.style = self.style_on if self.style is self.style_off else self.style_off

    @property
    def on(self) -> bool:
        """Whether the button is currently on."""
        return self.style is self.style_on

    @on.setter
    def on(self, value: bool) -> None:
        self.style = self.style_on if value else self.style_off

    async def callback(self, inter: disnake.MessageInteraction) -> None:
        await self.call(self, inter)


class TrinaryButton(ToggleButton[V], Generic[V, T]):
    """A tri-state button."""
    item: T

    def __init__(
        self,
        *,
        item: T = MISSING,
        style_off:  ButtonStyle = ButtonStyle.gray,
        style_on:   ButtonStyle = ButtonStyle.primary,
        style_item: ButtonStyle = ButtonStyle.success,
        on: bool = False,
        **kwargs: Any
    ) -> None:
        kwargs.setdefault('style', style_on if on else style_item if item else style_off)
        super().__init__(**kwargs, style_on=style_on, style_off=style_off, on=on)
        self.style_item = style_item
        self.item = item

    def toggle(self) -> None:
        """Toggles the state of the button between on and off."""
        if self.style is not self.style_on:
            self.style = self.style_on

        elif self.item is not None:
            self.style = self.style_item

        else:
            self.style = self.style_off

    @property
    def on(self) -> bool:
        """Whether the button is currently on."""
        return self.style is self.style_on

    @on.setter
    def on(self, value: bool) -> None:
        self.style = self.style_on if value else self.style_item if self.item else self.style_off


class OptionPaginator:
    """Paginator of `SelectOption`s for Select menus"""

    def __init__(self, up: SelectOption, down: SelectOption, options: list[SelectOption] = MISSING) -> None:
        self.all_options = options or []
        self.page = 0
        self.up = up
        self.down = down

    def __len__(self) -> int:
        base = len(self.all_options)

        if base <= 25:
            return 1

        elif base <= 48:
            return 2

        full, part = divmod(base - 48, 23)

        return 2 + full + bool(part)

    def get_options(self) -> list[SelectOption]:
        """Returns a list of `SelectOption`s that should appear at current page."""
        if len(self) == 1:
            return self.all_options

        if self.page == 0:
            return self.all_options[:24] + [self.down]

        if self.page == len(self) - 1:
            return [self.up] + self.all_options[self.page*23 + 1:]

        return [self.up] + self.all_options[self.page*23 + 1:self.page*23 + 24] + [self.down]

    @property
    def options(self) -> list[SelectOption]:
        """All underlying `SelectOption`s"""
        return self.all_options

    @options.setter
    def options(self, new: list[SelectOption]) -> None:
        self.page = 0
        self.all_options = new


class PersonalView(View):
    """View which does not respond to interactions of anyone but the invoker."""

    def __init__(self, *, user_id: int, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.user_id = user_id

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        return inter.author.id == self.user_id


class PaginatorView(PersonalView):
    """View implementing simple button pagination."""
    buttons: list[list[Button[PaginatorView]]]

    def __init__(self, *, user_id: int, timeout: float | None = 180, columns_per_page: int = 3) -> None:
        super().__init__(user_id=user_id, timeout=timeout)
        self.active: Button[PaginatorView] | None = None
        self.columns_per_page = int(columns_per_page)

        self.visible: list[Button[PaginatorView]] = []
        self.columns = len(max(self.buttons, key=len))
        self.page = 0

    def update_page(self) -> None:
        """Removes buttons no longer on the screen and adds those that should be on screen"""
        for button in self.visible:
            self.remove_item(button)

        self.visible.clear()
        width = self.columns_per_page
        offset = width * self.page

        for row in self.buttons:
            for button in row[offset:width+offset]:
                self.add_item(button)
                self.visible.append(button)


class ItemView(View):
    def __init__(
        self,
        embed: disnake.Embed,
        item: AnyItem,
        callback: Callable[[disnake.Embed, AnyItem, bool], None],
        *,
        timeout: float | None = 180
    ) -> None:
        super().__init__(timeout=timeout)
        self.call = callback
        self.embed = embed
        self.item = item

        callback(embed, item, False)

    @button_cls(label='Buffs', cls=ToggleButton['ItemView'])
    async def buff_button(self, button: ToggleButton[ItemView], inter: disnake.MessageInteraction) -> None:
        button.toggle()
        self.embed.clear_fields()
        self.call(self.embed, self.item, button.on)
        await inter.response.defer()
        await inter.edit_original_message(embed=self.embed, view=self)

    @button(label='Quit', style=disnake.ButtonStyle.red)
    async def quit_button(self, button: Button[ItemView], inter: disnake.MessageInteraction) -> None:
        self.stop()
        await inter.response.defer()


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

        self.active: TrinaryButton[MechView, AnyItem | None] | None = None
        self.image_update_task = asyncio.Future()

        self.paginator = OptionPaginator(
            SelectOption(
                label='Previous items',
                value='option:up',
                emoji='🔼',
                description='Click to show previous items'),
            SelectOption(
                label='More items',
                value='option:down',
                emoji='🔽',
                description='Click to show more items'))

        self.buttons: list[list[Button[MechView]]] = [
            [
                TrinaryButton(
                    emoji=Icons[translate_type(id)].emoji,
                    row=pos,
                    custom_id=id,
                    item=mech.__items__[id],
                    callback=self.slot_button_cb
                )
                for id in row
            ]
            for pos, row in enumerate((
                ('top1', 'drone', 'top2', 'charge', 'mod1', 'mod2', 'mod3', 'mod4'),
                ('side3', 'torso', 'side4', 'tele', 'mod5', 'mod6', 'mod7', 'mod8'),
                ('side1', 'legs', 'side2', 'hook'),
            ))
        ]

        super().__init__(user_id=user_id, timeout=timeout, columns_per_page=4)

        for i in range(4):
            self.buttons[2].append(Button(label='⠀', custom_id=f'button:no_op{i}', disabled=True, row=2))

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
            self.item_type_ref[item.type.lower()].append(SelectOption(label=item.name, emoji=item.element.emoji))

        ref = [element.emoji for element in Elements]

        for item_list in self.item_type_ref.values():
            item_list.sort(key=lambda option: (ref.index(str(option.emoji)), option.label))

    def update_page(self) -> None:
        super().update_page()

        self.to_lock = [button for button in self.visible if button.label != '⠀']

        for button in self.persistent_buttons:
            self.add_item(button)
            self.visible.append(button)

    async def slot_button_cb(self, button: TrinaryButton[MechView, AnyItem | None], inter: disnake.MessageInteraction) -> None:
        self.update_style(button)
        await inter.response.edit_message(view=self)

    @button_cls(emoji=Icons.MODULE.emoji, custom_id='button:modules', row=0, cls=Button['MechView'])
    async def modules_button(self, button: Button[MechView], inter: disnake.MessageInteraction) -> None:
        self.page ^= 1
        button.emoji = Icons.TORSO.emoji if self.page else Icons.MODULE.emoji

        self.update_page()
        await inter.response.edit_message(view=self)

    @button_cls(label='Filters', custom_id='button:filters', row=2, cls=ToggleButton['MechView'])
    async def filters_button(self, button: ToggleButton[MechView], inter: disnake.MessageInteraction) -> None:
        button.toggle()
        self.toggle_menus()
        await inter.response.edit_message(view=self)

    @button_cls(label='Buffs', custom_id='button:buffs', row=1, cls=ToggleButton['MechView'])
    async def buffs_button(self, button: ToggleButton[MechView], inter: disnake.MessageInteraction) -> None:
        if self.buffs.is_at_zero:
            await inter.send(
                "This won't show any effect because all your buffs are at level zero.\n"
                "You can change that using `/buffs` command."
                , ephemeral=True)
            return

        button.toggle()

        mech = self.mech
        self.embed.set_field_at(
            0,
            name='Stats:',
            value=mech.print_stats(self.buffs if button.on else None))

        if mech.torso is not None:
            self.embed.color = mech.torso.element.color

        await inter.response.edit_message(embed=self.embed, view=self)

    @select(placeholder='Choose slot', custom_id='select:item', options=[EMPTY_OPTION], disabled=True, row=3)
    async def item_select(self, select: Select[MechView], inter: disnake.MessageInteraction) -> None:
        item_name, = select.values

        if item_name in {'option:up', 'option:down'}:
            if item_name == 'option:up':
                self.paginator.page -= 1

            else:
                self.paginator.page += 1

            select._underlying.options = self.paginator.get_options()
            await inter.response.edit_message(view=self)
            return

        select.placeholder = item_name
        item = None if item_name == 'empty' else self.items[item_name]

        assert self.active is not None
        self.active.item = item

        if item is not None:
            item = InvItem.from_item(item) # type: ignore

        self.mech[self.active.custom_id] = item

        self.update_style(self.active)

        self.embed.set_field_at(
            0,
            name='Stats:',
            value=self.mech.print_stats(
                self.buffs if self.buffs_button.on else None))

        if self.mech.torso is not None:
            self.embed.color = self.mech.torso.element.color

        await inter.response.edit_message(embed=self.embed, view=self)

    @select(custom_id='select:filters', placeholder='Select filters', min_values=0, max_values=4, row=4, options=[
        SelectOption(label='Physical items',  value='type:PHYS', emoji=Elements.PHYS.emoji),
        SelectOption(label='Explosive items', value='type:HEAT', emoji=Elements.HEAT.emoji),
        SelectOption(label='Electric items',  value='type:ELEC', emoji=Elements.ELEC.emoji),
        SelectOption(label='Combined items',  value='type:COMB', emoji=Elements.COMB.emoji)])
    async def filters_select(self, select: Select[MechView], inter: disnake.MessageInteraction) -> None:
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

        filename = random_str(8) + '.png'
        self.embed.set_image(url=f'attachment://{filename}')
        file = image_to_file(self.mech.image, filename)
        await self.bot_msg.edit(embed=self.embed, file=file, attachments=[])

    def filter_options(self, item_type: str) -> list[SelectOption]:
        """Returns a list of `SelectOption`s filtered by type"""
        all_options = self.item_type_ref[item_type]
        new_options = [EMPTY_OPTION]

        if len(all_options) <= 24:
            return new_options + all_options

        types = {str(option.emoji) for option in self.filters_select.options if option.default}

        new_options.extend(filter(lambda item: str(item.emoji) in types, all_options) if types else all_options)
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

    def update_style(self, button: TrinaryButton[MechView, AnyItem | None], /) -> None:
        """Changes active button, alters its and passed button's style, updates dropdown description"""
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
        self.item_select.placeholder = button.item.name if button.item else 'empty'
        self.active = button

    def update_paginator(self, item_type: str) -> None:
        if item_type in trans_table:
            item_type = trans_table[item_type]

        self.paginator.options = self.filter_options(item_type)
        self.item_select._underlying.options = self.paginator.get_options()


class ArenaBuffsView(PaginatorView):
    MAXED_BUFFS = ArenaBuffs.maxed()
    active: TrinaryButton[ArenaBuffsView, bool | None] | None

    def __init__(self, buffs_ref: ArenaBuffs, user_id: int, *, columns_per_page: int = 3, timeout: float | None = 180) -> None:
        super().__init__(user_id=user_id, timeout=timeout, columns_per_page=columns_per_page)
        self.buffs = buffs_ref

        self.buttons = [
            [
                TrinaryButton(
                    item=buffs_ref[id] == self.MAXED_BUFFS[id] or None,
                    callback=self.button_callback,
                    label=f'{buffs_ref.buff_as_str_aware(id)}'.rjust(4, '⠀'),
                    custom_id=id,
                    emoji=STAT_NAMES[id].emoji,
                    row=pos)
                for id in row
            ]
            for pos, row in enumerate((
                ('eneCap', 'heaCap', 'phyDmg', 'phyRes', 'health'),
                ('eneReg', 'heaCol', 'expDmg', 'expRes', 'backfire'),
                ('eneDmg', 'heaDmg', 'eleDmg', 'eleRes')))
        ]
        self.update_page()

    async def button_callback(self, button: TrinaryButton[ArenaBuffsView, bool | None], inter: disnake.MessageInteraction) -> None:
        self.toggle_style(button)
        await inter.response.edit_message(view=self)

    @button(label='Quit', style=ButtonStyle.red, row=3)
    async def quit_button(self, button: Button[ArenaBuffsView], inter: disnake.MessageInteraction) -> None:
        self.before_stop()
        self.stop()
        await inter.response.edit_message(view=self)

    @button(emoji='⬅️', style=ButtonStyle.blurple, row=3, disabled=True)
    async def left_button(self, button: Button[ArenaBuffsView], interaction: disnake.MessageInteraction) -> None:
        """Callback for left button"""
        self.page -= 1
        self.update_page()
        self.right_button.disabled = False

        if self.page == 0:
            button.disabled = True

        await interaction.response.edit_message(view=self)

    @button(emoji='➡️', style=ButtonStyle.blurple, row=3)
    async def right_button(self, button: Button[ArenaBuffsView], interaction: disnake.MessageInteraction) -> None:
        """Callback for right button"""
        self.page += 1
        self.update_page()
        self.left_button.disabled = False

        if (self.page + 1) * self.columns_per_page >= self.columns:
            button.disabled = True

        await interaction.response.edit_message(view=self)

    @select(options=[EMPTY_OPTION], disabled=True, row=4)
    async def dropdown(self, select: Select[ArenaBuffsView], interaction: disnake.MessageInteraction) -> None:
        level = int(select.values[0])

        active = self.active
        assert active is not None
        id = active.custom_id
        self.buffs.levels[id] = level

        if level == self.MAXED_BUFFS.levels[id]:
            active.item = True

        else:
            active.item = None

        active.label = self.buffs.buff_as_str_aware(id).rjust(4, '⠀')
        self.toggle_style(active)

        await interaction.response.edit_message(view=self)

    def toggle_style(self, button: TrinaryButton[ArenaBuffsView, bool | None]) -> None:
        button.toggle()

        if self.active is button:
            self.dropdown.placeholder = None
            self.dropdown.disabled = True
            self.active = None
            return

        if self.active is None:
            self.dropdown.disabled = False

        else:
            self.active.toggle()

        self.dropdown.placeholder = button.label

        self.dropdown.options = [
            SelectOption(label=f'{level}: {buff}', value=str(level))
            for level, buff in enumerate(self.buffs.iter_as_str(button.custom_id))]

        self.active = button

    def before_stop(self) -> None:
        self.remove_item(self.right_button)
        self.remove_item(self.left_button)
        self.remove_item(self.quit_button)
        self.remove_item(self.dropdown)

        for item in self.visible:
            item.disabled = True


class CompareView(View):
    def __init__(self, embed: disnake.Embed, item_a: AnyItem, item_b: AnyItem, *, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.embed = embed
        self.item_a = item_a
        self.item_b = item_b

    @button(label='Buffs A')
    async def buff_button_A(self, button: Button[CompareView], inter: disnake.MessageInteraction) -> None:
        if was_off := button.style is ButtonStyle.gray:
            button.style = ButtonStyle.green

        else:
            button.style = ButtonStyle.gray

        await inter.response.edit_message(view=self)
