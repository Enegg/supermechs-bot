import enum
from typing import Final, NamedTuple

import disnake
from app.disnake_types import CommandInteraction, MessageInteraction

from app import paths, ui
from app.managers import missions
from app.plugins_factory import create_plugin

plugin = create_plugin(__name__)


class MissionDifficulty(enum.Enum):
    normal = "normal"
    hard = "hard"
    insane = "insane"


DIFFICULTY_COLORS: Final = {
    MissionDifficulty.normal: disnake.Color(0),
    MissionDifficulty.hard: disnake.Color(0),
    MissionDifficulty.insane: disnake.Color(0),
}


class UIContext(NamedTuple):
    mission_id: str
    difficulty: MissionDifficulty = MissionDifficulty.normal


class ComponentIds:
    __slots__ = ()

    prefix: Final = "campaign"

    diff_button_n: Final = "normal"
    diff_button_h: Final = "hard"
    diff_button_i: Final = "insane"


def make_component_id(name: str, ctx: UIContext) -> str:
    return f"{ComponentIds.prefix}:{name}:{ctx.mission_id}:{ctx.difficulty.value}"


def parse_component_id(id: str, /) -> tuple[str, UIContext]:
    _, name, mission_id, difficulty = id.split(":", 3)
    return (name, UIContext(mission_id=mission_id, difficulty=MissionDifficulty(difficulty)))


@plugin.slash_command()
async def campaign(inter: CommandInteraction) -> None:
    """Display information about a mission."""
    mission = missions.missions[0]

    ctx = UIContext(mission.id)
    container, files = get_mission_summary(mission, ctx)

    await inter.response.send_message(
        components=container, files=files, flags=disnake.MessageFlags(is_components_v2=True)
    )


@plugin.listener(disnake.Event.message_interaction)
async def on_mission_interaction(inter: MessageInteraction) -> None:
    component_id, ctx = parse_component_id(inter.data.custom_id)
    mission = next(m for m in missions.missions if m.id == ctx.mission_id)

    match component_id:
        case ComponentIds.diff_button_n:
            ctx = ctx.__replace__(difficulty=MissionDifficulty.normal)

        case ComponentIds.diff_button_h:
            ctx = ctx.__replace__(difficulty=MissionDifficulty.hard)

        case ComponentIds.diff_button_i:
            ctx = ctx.__replace__(difficulty=MissionDifficulty.insane)

        case _:
            plugin.logger.warning("%s - unknown component: %r", ComponentIds.prefix, component_id)

    container, files = get_mission_summary(mission, ctx)
    del files
    await inter.response.edit_message(components=container)


def get_mission_summary(
    mission: missions.MissionDto, ctx: UIContext
) -> tuple[ui.Container, list[disnake.File]]:
    container = ui.Container(accent_colour=DIFFICULTY_COLORS[ctx.difficulty])
    files: list[disnake.File] = []

    if mission.type is missions.MissionType.normal:
        title = f"## Mission {mission.level}\n### {mission.chapter}"

    elif mission.type is missions.MissionType.side:
        title = f"## Side mission {mission.level}\n### {mission.chapter}"

    elif mission.type is missions.MissionType.portal:
        title = mission.chapter

    else:
        raise RuntimeError

    container.children.append(ui.TextDisplay(title))

    if ctx.difficulty is MissionDifficulty.normal:
        diff_info = mission.diff_normal

    elif ctx.difficulty is MissionDifficulty.hard:
        diff_info = mission.diff_hard

    else:
        diff_info = mission.diff_insane

    rewards_lines: list[str] = ["**Rewards:**"]

    if diff_info.first_clear_tokens:
        rewards_lines.append(f"🟥 **{diff_info.first_clear_tokens}** tokens (first clear)")
    if diff_info.coins:
        rewards_lines.append(f"🪙 **{diff_info.coins}** gold")
    if mission.box is missions.BoxReward.standard:
        rewards_lines.append("📦 **0-1** mix box")
    elif mission.box is missions.BoxReward.fortune:
        rewards_lines.append("📦🎁 **0-1** mix or fortune box")
    if diff_info.exp:
        rewards_lines.append(f"🌟 **{diff_info.exp}** EXP")
    if diff_info.tickets:
        rewards_lines.append(f"🎫 **{diff_info.tickets}** tickets")

    container.children.append(ui.TextDisplay("\n".join(rewards_lines)))
    container.children.append(ui.Separator(divider=True))
    container.children.append(ui.TextDisplay(f"⛽ **{diff_info.fuel_cost}** fuel cost"))

    container.children.append(ui.ActionRow(
        ui.ActionButton(
            custom_id=make_component_id(ComponentIds.diff_button_n, ctx),
            style=ui.ButtonStyle.blurple if ctx.difficulty is MissionDifficulty.normal else ui.ButtonStyle.gray,
            label="Normal",
            disabled=ctx.difficulty is MissionDifficulty.normal,
        ),
        ui.ActionButton(
            custom_id=make_component_id(ComponentIds.diff_button_h, ctx),
            style=ui.ButtonStyle.blurple if ctx.difficulty is MissionDifficulty.hard else ui.ButtonStyle.gray,
            label="Hard",
            disabled=ctx.difficulty is MissionDifficulty.hard,
        ),
        ui.ActionButton(
            custom_id=make_component_id(ComponentIds.diff_button_i, ctx),
            style=ui.ButtonStyle.blurple if ctx.difficulty is MissionDifficulty.insane else ui.ButtonStyle.gray,
            label="Insane",
            disabled=ctx.difficulty is MissionDifficulty.insane,
        ),
    ))  # fmt: skip

    image_path = paths.MISSION_IMAGES_DIR / f"{mission.id}.png"

    if image_path.exists():
        file = disnake.File(image_path)
        files.append(file)
        container.children.append(ui.MediaGallery(ui.media_gallery_item(file)))

    else:
        container.children.append(ui.TextDisplay("*Image not available*"))

    return container, files


setup, teardown = plugin.create_extension_handlers()
