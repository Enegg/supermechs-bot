from __future__ import annotations

from typing import *

import disnake
from disnake import ButtonStyle, SelectOption
from disnake.ui import Button, Select, View

from enums import Icons

if TYPE_CHECKING:
    from SM_classes import Item, Mech


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
    'mod8': 'module',
    'tele': 'teleporter',
    'hook': 'grappling_hook',
    'charge': 'charge_engine'}

def translate_type(_type: str) -> str:
    if _type.startswith(('side', 'top')):
        return ('SIDE_', 'TOP_')[_type.startswith('top')] + ('RIGHT', 'LEFT')[int(_type[-1]) % 2]

    if _type.startswith('mod'):
        return 'MODULE'

    return _type.upper()



async def no_op(*args, **kwargs) -> dict[str, Any]:
    return {}


class MechView(View):
    def __init__(self, mech: Mech, items: dict[str, Item], callback: Callable[[disnake.MessageInteraction], Awaitable[dict[str, Any]]]):
        super().__init__()
        self.build = mech
        self.items = items
        self.active: ItemButton | None = None

        for pos, row in enumerate((
            ('top1', 'drone', 'top2', 'mod1', 'mod2'),
            ('side3', 'torso', 'side4', 'mod3', 'mod4'),
            ('side1', 'legs', 'side2', 'mod5', 'mod6'),
            ('charge', 'tele', 'hook', 'mod7', 'mod8'))):
            for id in row:
                emoji = Icons[translate_type(id)].emoji
                self.add_item(ItemButton(emoji=emoji, row=pos, custom_id=id, item=mech._items[id]))

        EMPTY = SelectOption(label='empty', description='Select to remove', emoji='🗑️')

        async def quit_callback(inter: Any):
            self.clear_items()
            self.stop()
            return {}

        self.dropdown = ItemSelect(placeholder='Select slot', options=[EMPTY], disabled=True, row=4)
        self.fifth_row = (
            ToggleButton(label='Buffs', callback=no_op, row=4),
            ActionButton(label='Update stats', style=ButtonStyle.primary, callback=callback, row=4),
            ActionButton(label='Quit', style=ButtonStyle.red, callback=quit_callback, row=4))

        for button in self.fifth_row:
            self.add_item(button)

        self.item_type_ref: dict[str, list[SelectOption]] = dict(
            drone=[EMPTY],
            torso=[EMPTY],
            legs=[EMPTY],
            top_weapon=[EMPTY],
            side_weapon=[EMPTY],
            charge_engine=[EMPTY],
            teleporter=[EMPTY],
            grappling_hook=[EMPTY],
            module=[EMPTY])


        for item in items.values():
            _list = self.item_type_ref[item.type.lower()]

            if len(_list) == 25:
                continue

            _list.append(SelectOption(label=item.name, emoji=item.element.emoji))


    def toggle_style(self, button: ItemButton) -> None:
        button.cycle_style()

        if self.active is button:
            self.swap_buttons()
            self.dropdown.toggle_text(None)
            self.active = None
            return

        if self.active is None:
            self.swap_buttons()

        else:
            self.active.cycle_style()

        if (_type := button.custom_id) in trans_table:
            _type = trans_table[_type]

        self.dropdown.options = self.item_type_ref[_type]
        self.dropdown.toggle_text(button.item)
        self.active = button


    def swap_buttons(self) -> None:
        if not self.dropdown.disabled:
            self.remove_item(self.dropdown)
            self.dropdown.disabled = True

            for button in self.fifth_row:
                self.add_item(button)

        else:
            for button in self.fifth_row:
                self.remove_item(button)

            self.dropdown.disabled = False
            self.add_item(self.dropdown)


    def push_item(self, item: Item | None):
        assert self.active is not None
        self.active.item = item
        # self.active.label = None if item is None else item.name
        self.build[self.active.custom_id] = item
        self.toggle_style(self.active)


class ItemSelect(Select[MechView]):
    def toggle_text(self, item: Item | None):
        if item is None:
            self.placeholder = 'empty'

        else:
            self.placeholder = item.name


    async def callback(self, interaction: disnake.MessageInteraction):
        assert self.view is not None
        item_name, = self.values

        if item_name == 'empty':
            self.view.push_item(None)

        else:
            item = self.view.items[item_name]
            self.view.push_item(item)

        await interaction.response.edit_message(view=self.view)


class ItemButton(Button[MechView]):
    custom_id: str

    def __init__(self, emoji: str, row: int, custom_id: str, item: Item=None):
        style = ButtonStyle.secondary if item is None else ButtonStyle.success
        super().__init__(style=style, emoji=emoji, row=row, custom_id=custom_id)
        self.item = item


    def cycle_style(self):
        if self.style is ButtonStyle.secondary or self.style is ButtonStyle.success:
            self.style = ButtonStyle.primary

        elif self.style is ButtonStyle.primary and self.item is not None:
            self.style = ButtonStyle.success

        else:
            self.style = ButtonStyle.secondary


    async def callback(self, interaction: disnake.MessageInteraction):
        assert self.view is not None

        self.view.toggle_style(self)
        await interaction.response.edit_message(view=self.view)


class ItemView(View):
    def __init__(self, *, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)


class ToggleButton(Button[View]):
    def __init__(self, *, style_off: ButtonStyle=ButtonStyle.secondary, style_on: ButtonStyle=ButtonStyle.success, callback: Callable[[disnake.MessageInteraction], Awaitable[dict[str, Any]]], **kwargs: Any):
        super().__init__(style=style_off, **kwargs)
        self.styles = style_off, style_on
        self.call = callback


    def toggle(self) -> None:
        if self.style is self.styles[0]:
            self.style = self.styles[1]

        else:
            self.style = self.styles[0]


    async def callback(self, interaction: disnake.MessageInteraction):
        self.toggle()
        await interaction.response.edit_message(**await self.call(interaction), view=self.view)


class ActionButton(Button[View]):
    def __init__(self, *, callback: Callable[[disnake.MessageInteraction], Awaitable[dict[str, Any]]], **kwargs: Any):
        super().__init__(**kwargs)
        self.call = callback


    async def callback(self, interaction: disnake.MessageInteraction):
        await interaction.response.defer()
        await interaction.edit_original_message(**await self.call(interaction), view=self.view)
