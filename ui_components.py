from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Coroutine, Generic, TypeVar

import aiohttp
import disnake
from disnake import ButtonStyle, SelectOption
from disnake.ui import Button
from disnake.ui import Item as UIItem
from disnake.ui import Select, View, button, select

from enums import STAT_NAMES, Icons
from functions import random_str
from image_manipulation import image_to_file
from SM_classes import AnyAttachment, ArenaBuffs

if TYPE_CHECKING:
    from SM_classes import Item, Mech

T = TypeVar('T')
BT = TypeVar('BT', bound=UIItem)

Callback = Callable[[BT, disnake.MessageInteraction], Coroutine[Any, Any, None]]

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
    return


EMPTY_OPTION = SelectOption(label='empty', description='Select to remove', emoji='🗑️')


class ItemView(View):
    def __init__(
        self,
        embed: disnake.Embed,
        item: Item[AnyAttachment],
        callback: Callable[[disnake.Embed, Item[AnyAttachment], bool], None],
        *,
        timeout: float | None = 180
    ) -> None:
        super().__init__(timeout=timeout)
        self.call = callback
        self.embed = embed
        self.item = item

        callback(embed, item, False)


    @button(label='Buffs')
    async def buff_button(self, button: Button[ItemView], inter: disnake.MessageInteraction) -> None:
        if was_off := button.style is ButtonStyle.gray:
            button.style = ButtonStyle.green

        else:
            button.style = ButtonStyle.gray

        self.embed.clear_fields()
        self.call(self.embed, self.item, was_off)
        await inter.response.defer()
        await inter.edit_original_message(embed=self.embed, view=self)


    @button(label='Quit', style=disnake.ButtonStyle.red)
    async def quit_button(self, button: Button[ItemView], inter: disnake.MessageInteraction) -> None:
        self.stop()
        await inter.response.defer()


class MechView(View):
    """Class implementing View for a button-based mech building"""
    def __init__(
        self,
        mech: Mech,
        embed: disnake.Embed,
        items: dict[str, Item[AnyAttachment]],
        arena_buffs: ArenaBuffs,
        session: aiohttp.ClientSession,
        *,
        timeout: float | None = 180
    ) -> None:
        super().__init__(timeout=timeout)
        self.build = mech
        self.embed = embed
        self.items = items
        self.buffs = arena_buffs
        self.session = session
        self.active: TrinaryButton[Item[AnyAttachment] | None] | None = None

        for pos, row in enumerate((
            ('top1', 'drone', 'top2', 'mod1', 'mod2'),
            ('side3', 'torso', 'side4', 'mod3', 'mod4'),
            ('side1', 'legs', 'side2', 'mod5', 'mod6'),
            ('charge', 'tele', 'hook', 'mod7', 'mod8')
            )):
            for id in row:
                self.add_item(TrinaryButton(
                    emoji=Icons[translate_type(id)].emoji,
                    row=pos,
                    custom_id=id,
                    item=mech._items[id],
                    callback=self.button_callback))

        async def dropdown_callback(interaction: disnake.MessageInteraction) -> None:
            item_name, = self.dropdown.values

            if item_name == 'empty':
                self.push_item(None)

            else:
                item = self.items[item_name]
                self.push_item(item)

            embed.set_field_at(
                0,
                name='Stats:',
                value=mech.print_stats(
                    arena_buffs if self.buffs_enabled else None))

            if mech.torso is not None:
                embed.color = mech.torso.element.color

            await interaction.response.edit_message(embed=embed, view=self)

        self.dropdown = Select(disabled=True, row=4)
        self.dropdown.callback = dropdown_callback

        self.item_type_ref: dict[str, list[SelectOption]] = dict(
            drone=[EMPTY_OPTION],
            torso=[EMPTY_OPTION],
            legs=[EMPTY_OPTION],
            top_weapon=[EMPTY_OPTION],
            side_weapon=[EMPTY_OPTION],
            charge=[EMPTY_OPTION],
            tele=[EMPTY_OPTION],
            hook=[EMPTY_OPTION],
            module=[EMPTY_OPTION])


        for item in items.values():
            _list = self.item_type_ref[item.type.lower()]

            if len(_list) == 25:
                continue

            _list.append(SelectOption(label=item.name, emoji=item.element.emoji))


    async def button_callback(self, button: TrinaryButton[Item[AnyAttachment] | None], inter: disnake.MessageInteraction) -> None:
        self.toggle_style(button)
        await inter.response.edit_message(view=self)


    @button(label='Buffs', row=4)
    async def buffs_button(self, button: Button[MechView], inter: disnake.MessageInteraction) -> None:
        if was_off := button.style is ButtonStyle.gray:
            button.style = ButtonStyle.green

        else:
            button.style = ButtonStyle.gray

        mech = self.build
        self.embed.set_field_at(
            0,
            name='Stats:',
            value=mech.print_stats(self.buffs if was_off else None))

        if mech.torso is not None:
            self.embed.color = mech.torso.element.color

        await inter.response.edit_message(embed=self.embed, view=self)


    @button(label='Update image', style=ButtonStyle.blurple, row=4)
    async def image_button(self, button: Button[MechView], inter: disnake.MessageInteraction) -> None:
        """Updates embed image if the image changed"""
        await inter.response.defer()
        mech = self.build

        if mech.has_image_cached:
            return

        await mech.load_images(self.session)
        filename = random_str(8) + '.png'

        self.embed.set_image(url=f'attachment://{filename}')
        file = image_to_file(mech.image, filename)
        await inter.edit_original_message(embed=self.embed, file=file, attachments=[])


    @button(label='Quit', style=ButtonStyle.red, row=4)
    async def quit_button(self, button: Button[MechView], inter: disnake.MessageInteraction) -> None:
        self.clear_items()
        self.stop()
        await inter.response.edit_message(view=self)


    def toggle_style(self, button: TrinaryButton[Item[AnyAttachment] | None], /) -> None:
        """Changes active button, alters its and passed button's style, updates dropdown description"""
        button.cycle_style()

        if self.active is button:
            self.swap_buttons()
            self.dropdown.placeholder = 'empty'
            self.active = None
            return

        if self.active is None:
            self.swap_buttons()

        else:
            self.active.cycle_style()

        if (_type := button.custom_id) in trans_table:
            _type = trans_table[_type]

        self.dropdown.options = self.item_type_ref[_type]
        self.dropdown.placeholder = button.item.name if button.item else 'empty'
        self.active = button


    def swap_buttons(self) -> None:
        """Swaps between buffs/image/quit buttons and dropdown menu."""
        if self.dropdown.disabled:
            self.remove_item(self.buffs_button)  # type: ignore
            self.remove_item(self.image_button)  # type: ignore
            self.remove_item(self.quit_button)  # type: ignore
            self.add_item(self.dropdown)

        else:
            self.remove_item(self.dropdown)
            self.add_item(self.buffs_button)  # type: ignore
            self.add_item(self.image_button)  # type: ignore
            self.add_item(self.quit_button)  # type: ignore

        self.dropdown.disabled ^= True


    def push_item(self, item: Item[AnyAttachment] | None) -> None:
        """Binds to or removes an item from active button and updates style"""
        assert self.active is not None
        self.active.item = item
        self.build[self.active.custom_id] = item
        self.toggle_style(self.active)


    @property
    def buffs_enabled(self) -> bool:
        return self.buffs_button.style is ButtonStyle.green


class ArenaBuffsView(View):
    MAXED_BUFFS = ArenaBuffs.maxed()

    def __init__(self, buffs_ref: ArenaBuffs, *, columns_per_page: int=3, timeout: float | None=180) -> None:
        super().__init__(timeout=timeout)
        self.active: TrinaryButton[bool] | None = None
        self.buffs = buffs_ref
        self.columns_per_page = int(columns_per_page)

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
        self.visible: list[Button[View]] = []
        self.columns = len(max(self.buttons, key=len))
        self.page = 0
        self.update_page()


    async def button_callback(self, button: TrinaryButton[bool], inter: disnake.MessageInteraction) -> None:
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
        value_str, = select.values
        level = int(value_str)

        self.push_value(level)
        await interaction.response.edit_message(view=self)


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


    def toggle_style(self, button: TrinaryButton[bool]) -> None:
        button.cycle_style()

        if self.active is button:
            self.dropdown.placeholder = None
            self.dropdown.disabled = True
            self.active = None
            return

        if self.active is None:
            self.dropdown.disabled = False

        else:
            self.active.cycle_style()

        self.dropdown.placeholder = button.label

        self.dropdown.options = [
            SelectOption(label=f'{level}: {buff}', value=str(level))
            for level, buff in enumerate(self.buffs.iter_as_str(button.custom_id))]

        self.active = button


    def before_stop(self) -> None:
        self.remove_item(self.right_button)  # type: ignore
        self.remove_item(self.left_button)  # type: ignore
        self.remove_item(self.quit_button)  # type: ignore
        self.remove_item(self.dropdown)  # type: ignore

        for item in self.visible:
            item.disabled = True


    def push_value(self, level: int) -> None:
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


class CompareView(View):
    def __init__(self, embed: disnake.Embed, item_a: Item[AnyAttachment], item_b: Item[AnyAttachment], *, timeout: float | None = 180):
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


class TrinaryButton(Button[View], Generic[T]):
    """A tri-state button."""
    custom_id: str
    item: T | None

    def __init__(
        self,
        item: T=None,
        callback: Callback[TrinaryButton[T]]=no_op,
        style_off: ButtonStyle=ButtonStyle.gray,
        style_on: ButtonStyle=ButtonStyle.primary,
        style_item: ButtonStyle=ButtonStyle.success,
        **kwargs: Any
    ) -> None:
        super().__init__(**kwargs, style=style_off if item is None else style_item)
        self.style_off = style_off
        self.style_on = style_on
        self.style_item = style_item
        self.call = callback
        self.item = item


    def cycle_style(self) -> None:
        if self.style is not self.style_on:
            self.style = self.style_on

        elif self.item is not None:
            self.style = self.style_item

        else:
            self.style = self.style_off


    async def callback(self, inter: disnake.MessageInteraction) -> None:
        await self.call(self, inter)


class ToggleButton(Button[View]):
    """A two-state button."""

    def __init__(self, *,
        style_off: ButtonStyle = ButtonStyle.secondary,
        style_on:  ButtonStyle = ButtonStyle.success,
        callback: Callback[ToggleButton],
        on: bool=False,
        **kwargs: Any
    ) -> None:
        super().__init__(style=style_on if on else style_off, **kwargs)
        self.style_off = style_off
        self.style_on  = style_on
        self.call = callback


    def toggle(self) -> None:
        self.style = self.style_on if self.style is self.style_off else self.style_off


    @property
    def on(self) -> bool:
        return self.style is self.style_on


    async def callback(self, interaction: disnake.MessageInteraction) -> None:
        self.toggle()
        await self.call(self, interaction)
