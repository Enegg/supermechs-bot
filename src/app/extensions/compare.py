from collections import abc
from typing import Final, Literal, NamedTuple

from app.disnake_types import CommandInteraction
from disnake import Event, MessageFlags
from disnake.ext import commands

from app import i18n, ui
from app.assets import COLORS, EMOJIS
from app.commands.autocompleters import item_name_autocomplete
from app.devtools import debug_components
from app.extensions.item_lookup.helpers import item_transform_range
from app.managers import gfx, packs
from app.plugins_factory import create_plugin

import dupermechs.all as sm

plugin = create_plugin(__name__)
setup, teardown = plugin.create_extension_handlers()


ITEM_SLOT_PLURAL: abc.Mapping[sm.Item.Slot, str] = {
    sm.Item.Slot.torso: "torsos",
    sm.Item.Slot.legs: "legs",
    sm.Item.Slot.drone: "drones",
    sm.Item.Slot.side_weapon: "side weapons",
    sm.Item.Slot.top_weapon: "top weapons",
    sm.Item.Slot.charge: "charges",
    sm.Item.Slot.teleport: "teleports",
    sm.Item.Slot.hook: "hooks",
    sm.Item.Slot.shield: "shields",
    sm.Item.Slot.module: "modules",
    sm.Item.Slot.perk: "perks",
    sm.Item.Slot.kit: "kits",
}
ITEM_SLOT_NAME: abc.Mapping[sm.Item.Slot, str] = {
    sm.Item.Slot.torso: "torso",
    sm.Item.Slot.legs: "legs",
    sm.Item.Slot.drone: "drone",
    sm.Item.Slot.side_weapon: "side weapon",
    sm.Item.Slot.top_weapon: "top weapon",
    sm.Item.Slot.charge: "charge",
    sm.Item.Slot.teleport: "teleport",
    sm.Item.Slot.hook: "hook",
    sm.Item.Slot.shield: "shield",
    sm.Item.Slot.module: "module",
    sm.Item.Slot.perk: "perk",
    sm.Item.Slot.kit: "kit",
}
FAKE_URL = "http://0.0.0.0"


class CompareContext(NamedTuple):
    i1_id: sm.Item.Id
    i1_stage_index: int
    i1_level_index: int

    i2_id: sm.Item.Id
    i2_stage_index: int
    i2_level_index: int

    levels_page: int
    edited_item: Literal[0, 1] | int = 0  # noqa: PYI051
    damage_average: bool = False
    buffs_enabled: bool = False


class ComponentIds:
    prefix: Final = "item-compare"

    item_1: Final = "item1"
    item_2: Final = "item2"
    stage_select: Final = "stages"
    level_select: Final = "levels"
    buffs_button: Final = "buffs"
    avg_button: Final = "avg"
    titan_button: Final = "dvt"

    debug_reload_button: Final = "boo"


@plugin.slash_command()
async def compare(
    inter: CommandInteraction,
    item_1_name: str = commands.Param(name="item_1", autocomplete=item_name_autocomplete),
    item_2_name: str = commands.Param(name="item_2", autocomplete=item_name_autocomplete),
) -> None:
    gettext = i18n.get_gettext(inter)

    for item_1 in packs.filter_items(legacy=False):
        if item_1.name == item_1_name:
            break
    else:
        msg = gettext("unknown-item-name", name=item_1_name)
        raise commands.UserInputError(msg)
    # TODO: merge those loops
    for item_2 in packs.filter_items(legacy=False):
        if item_2.name == item_2_name:
            break
    else:
        msg = gettext("unknown-item-name", name=item_2_name)
        raise commands.UserInputError(msg)

    i1_stage_index = len(item_1.stages) - 1
    i2_stage_index = len(item_2.stages) - 1

    i1_levels = item_1.stages[i1_stage_index].levels
    i2_levels = item_1.stages[i2_stage_index].levels

    ctx = CompareContext(
        i1_id=item_1.id,
        i1_stage_index=i1_stage_index,
        i1_level_index=len(i1_levels) - 1,
        i2_id=item_2.id,
        i2_stage_index=i2_stage_index,
        i2_level_index=len(i2_levels) - 1,
        levels_page=ui.option_to_page_count(len(i1_levels)),
    )

    container = get_compare_summary(gettext=gettext, item_1=item_1, item_2=item_2, ctx=ctx)
    await inter.response.send_message(
        components=container, flags=MessageFlags(is_components_v2=True)
    )


@plugin.listener(Event.message_interaction)
async def on_item_compare_interaction(inter: ui.MessageInteraction) -> None:
    if not inter.data.custom_id.startswith(ComponentIds.prefix):
        return

    gettext = i18n.get_gettext(inter)
    component, ctx = parse_component_id(inter.data.custom_id)
    item_pack = packs.get_item_pack()

    try:
        item_1 = item_pack.reloaded_items[ctx.i1_id]
        item_2 = item_pack.reloaded_items[ctx.i2_id]

    except KeyError:
        await inter.response.edit_message(components=ui.Container(
            ui.TextDisplay("Oops"), accent_colour=COLORS.error
        ))  # fmt: skip
        return

    if (
        len(item_1.stages) < ctx.i1_stage_index
        or len(item_1.stages[ctx.i1_stage_index].levels) < ctx.i1_level_index
        or len(item_2.stages) < ctx.i2_stage_index
        or len(item_2.stages[ctx.i2_stage_index].levels) < ctx.i2_level_index
    ):
        # oops
        valid_i1_stage_index = min(ctx.i1_stage_index, len(item_1.stages) - 1)
        valid_i1_level_index = min(
            ctx.i1_level_index, len(item_1.stages[valid_i1_stage_index].levels) - 1
        )
        valid_i2_stage_index = min(ctx.i2_stage_index, len(item_2.stages) - 1)
        valid_i2_level_index = min(
            ctx.i2_level_index, len(item_2.stages[valid_i2_stage_index].levels) - 1
        )
        await inter.followup.send(
            f"Something borked:\n{ctx.i1_stage_index=}\n{ctx.i1_level_index=}\n{ctx.i2_stage_index=}\n{ctx.i2_level_index=}"
        )
        ctx = ctx.__replace__(
            i1_stage_index=valid_i1_stage_index,
            i1_level_index=valid_i1_level_index,
            i2_stage_index=valid_i2_stage_index,
            i2_level_index=valid_i2_level_index,
            levels_page=0,
        )
        await inter.response.edit_message(
            components=get_compare_summary(gettext=gettext, item_1=item_1, item_2=item_2, ctx=ctx)
        )
        return

    match component:
        case ComponentIds.debug_reload_button:
            pass

        case _:
            # logger.warning("%s - unknown component: %r", ComponentIds.prefix, component)  # noqa: ERA001
            pass

    container = get_compare_summary(gettext=gettext, item_1=item_1, item_2=item_2, ctx=ctx)
    if __debug__:
        debug_components(container)
    await inter.response.edit_message(components=container)


def make_component_id(component: str, ctx: CompareContext) -> str:
    flags = ctx.damage_average | ctx.buffs_enabled << 1
    return (
        f"{ComponentIds.prefix}:{component}"
        f":{ctx.i1_id:x}:{ctx.i1_stage_index}:{ctx.i1_level_index}"
        f":{ctx.i2_id:x}:{ctx.i2_stage_index}:{ctx.i2_level_index}"
        f":{ctx.levels_page}:{ctx.edited_item}:{flags:x}"
    )


def parse_component_id(id: str, /) -> tuple[str, CompareContext]:
    (
        _,
        component,
        i1_id,
        i1_stage_index,
        i1_level_index,
        i2_id,
        i2_stage_index,
        i2_level_index,
        levels_page,
        edited_item,
        flags,
    ) = id.split(":", maxsplit=10)
    flags = int(flags, 16)
    return (
        component,
        CompareContext(
            i1_id=sm.Item.Id(int(i1_id, 16)),
            i1_stage_index=int(i1_stage_index),
            i1_level_index=int(i1_level_index),
            i2_id=sm.Item.Id(int(i2_id, 16)),
            i2_stage_index=int(i2_stage_index),
            i2_level_index=int(i2_level_index),
            levels_page=int(levels_page),
            edited_item=int(edited_item),
            damage_average=flags & 1 == 1,
            buffs_enabled=flags >> 1 & 1 == 1,
        ),
    )


def get_subtitle(item_1: sm.Item, item_2: sm.Item) -> str:
    is_same_element = item_1.element is item_2.element
    is_same_slot = item_1.slot_id is item_2.slot_id

    if is_same_element and is_same_slot:
        subtitle_parts = [EMOJIS.get_element(item_1.element).mention]

        if item_1.element is not sm.Item.Element.other:
            subtitle_parts.append(item_1.element.name)

        subtitle_parts.append(ITEM_SLOT_PLURAL[item_1.slot_id])
        subtitle_parts[1] = subtitle_parts[1].capitalize()
        subtitle_parts.append(EMOJIS.get_item_slot(item_1.slot_id).mention)

    elif is_same_element:
        subtitle_parts = [EMOJIS.get_element(item_1.element).mention]

        if item_1.element is not sm.Item.Element.other:
            subtitle_parts.append(item_1.element.name)

        subtitle_parts.append(ITEM_SLOT_NAME[item_1.slot_id])
        subtitle_parts[1] = subtitle_parts[1].capitalize()
        subtitle_parts += [
            EMOJIS.get_item_slot(item_1.slot_id).mention,
            "|",
            ITEM_SLOT_NAME[item_2.slot_id].capitalize(),
            EMOJIS.get_item_slot(item_2.slot_id).mention,
        ]

    elif is_same_slot and sm.Item.Element.other not in (item_1.element, item_2.element):
        subtitle_parts = [
            EMOJIS.get_element(item_1.element).mention,
            item_1.element.name.capitalize(),
            "|",
            EMOJIS.get_element(item_2.element).mention,
            item_2.element.name,
            ITEM_SLOT_PLURAL[item_1.slot_id],
            EMOJIS.get_item_slot(item_2.slot_id).mention,
        ]

    else:
        subtitle_parts = [EMOJIS.get_element(item_1.element).mention]

        if item_1.element is not sm.Item.Element.other:
            subtitle_parts.append(item_1.element.name)
        subtitle_parts.append(ITEM_SLOT_NAME[item_1.slot_id])
        subtitle_parts[1] = subtitle_parts[1].capitalize()
        subtitle_parts += [
            EMOJIS.get_item_slot(item_1.slot_id).mention,
            "|",
            EMOJIS.get_element(item_2.element).mention,
        ]
        if item_2.element is not sm.Item.Element.other:
            subtitle_parts.append(item_2.element.name)
        subtitle_parts.append(ITEM_SLOT_NAME[item_2.slot_id])
        # subtitle_parts[1] = subtitle_parts[1].capitalize()  # noqa: ERA001
        subtitle_parts.append(EMOJIS.get_item_slot(item_2.slot_id).mention)

    return " ".join(subtitle_parts)


def get_compare_summary(
    gettext: i18n.GetText, item_1: sm.Item, item_2: sm.Item, ctx: CompareContext
) -> ui.Container:
    is_same_element = item_1.element is item_2.element
    # is_same_slot = item_1.slot_id is item_2.slot_id  # noqa: ERA001

    container, add_component = ui.container(
        accent_color=COLORS.get_element(item_1.element) if is_same_element else None
    )

    title_lines = [
        f"## Item 1: {item_1.name}",
        f"## Item 2: {item_2.name}",
        f"*{get_subtitle(item_1, item_2)}*",
        f"-# {item_transform_range(item_1)} | {item_transform_range(item_2)}",
    ]
    add_component(ui.TextDisplay("\n".join(title_lines)))

    i1_sprite_url = gfx.get_image_url((item_1.id, item_1.stages[ctx.i1_stage_index].tier), FAKE_URL)
    i2_sprite_url = gfx.get_image_url((item_2.id, item_2.stages[ctx.i2_stage_index].tier), FAKE_URL)
    add_component(ui.MediaGallery(
        ui.media_gallery_item(i1_sprite_url),
        ui.media_gallery_item(i2_sprite_url),
    ))  # fmt: skip

    add_component(ui.ActionRow(ui.ActionButton(
        custom_id=make_component_id(ComponentIds.debug_reload_button, ctx),
        label="Refresh",
        emoji="🔄"
    )))  # fmt: skip
    return container
