import io
import uuid
from json import JSONDecodeError

from disnake import Attachment, CommandInteraction, Embed, Locale, ui
from disnake.ext import commands, plugins
from disnake.utils import MISSING

import i18n
from assets import ASSETS
from bridges import mech_name_autocomplete
from bridges.embeds import embed_image, sikrit_footer
from bridges.ui import get_check
from devtools import debug_footer
from discord_utils import ComponentLimits, bytes_to_file, command_mention
from discord_utils.ui import ActionButton, wait_for_components
from discord_utils.ui.store import ComponentStore
from models import Player
from shared.item_packs import DEFAULT_PACK
from shared.utils import fold_binary_prefix
from user_input import StringLimits, sanitize_string

from .mech_manager import MechView

from supermechs.api import Stat, Type, mech_weight
from supermechs.ext.deserializers.exceptions import DataError
from supermechs.ext.workshop import dump_mechs, load_mechs

plugin = plugins.Plugin[commands.InteractionBot](name="Mech-manager", logger=__name__)


@plugin.load_hook(post=True)
async def on_load() -> None:
    import sync

    # wait until API command caches are populated
    await sync.SYNC_FINISHED.wait()
    buffs_command = plugin.bot.get_global_command_named("buffs")
    assert buffs_command is not None
    MechView.command_mention = command_mention(buffs_command)


@plugin.slash_command()
async def mech(inter: CommandInteraction) -> None:
    del inter


# TODO: localize this
MECH_SUMMARY_TEMPLATE = f"""\
- {ASSETS.types[Type.TORSO].emoji} {{TORSO}}
- {ASSETS.types[Type.LEGS].emoji} {{LEGS}}
- {ASSETS.sided_types[Type.SIDE_WEAPON].right.emoji} `{{WEAPONS}}` weapon(s)
- {ASSETS.types[Type.MODULE].emoji} `{{MODULES}}` module(s)
- {ASSETS.stats[Stat.weight].emoji} `{{WEIGHT}}`kg\
"""


@mech.sub_command()
async def catalog(inter: CommandInteraction, player: Player) -> None:
    """Catalog of your builds. {{ MECH_BROWSE }}"""
    if not player.builds:
        return await inter.response.send_message("You do not have any builds.", ephemeral=True)

    embed = Embed(title="Your builds", color=inter.author.color)

    if player.active_build is not None:
        embed.description = f"Currently active: **{player.active_build.name}**"

    fields: list[tuple[str, str]] = []

    for build in player.builds.values():
        mech = build.mech
        value = MECH_SUMMARY_TEMPLATE.format(
            TORSO="no torso" if mech.torso is None else mech.torso.name,
            LEGS="no legs" if mech.legs is None else mech.legs.name,
            WEAPONS=sum(1 for _ in filter(None, mech.iter_items("weapons"))),
            MODULES=sum(1 for _ in filter(None, mech.modules())),
            WEIGHT=mech_weight(mech),
        )
        fields.append((build.name, value))

    # TODO: paginate
    for title, value in fields:
        embed.add_field(title, value)

    if __debug__:
        debug_footer(embed)

    await inter.send(embed=embed, ephemeral=True)


@mech.sub_command()
@commands.max_concurrency(1, commands.BucketType.user)
async def build(
    inter: CommandInteraction,
    locale: Locale,
    player: Player,
    name: commands.String[str, 1, StringLimits.names] | None = None,
) -> None:
    """Interactive UI for modifying a mech build. {{ MECH_BUILD }}

    Parameters
    ----------
    name: The name of an existing build or of one to create. {{ MECH_BUILD_NAME }}
    """
    item_pack = DEFAULT_PACK.get_nowait()

    if name is None:
        build = player.get_active_or_create_build()

    else:
        build = player.get_or_create_build(sanitize_string(name))

    store = ComponentStore(interaction_check=get_check(inter.author))
    view = MechView(store, build, item_pack, player, locale)
    file = MISSING

    if False:  # FIXME
        if build.mech.torso is not None:
            renderer = object()
            await renderer.load_mech_images(mech)
            image = renderer.create_mech_image(mech)
            url, file = embed_image(image, view.mech_config)
            view.embed.set_image(url)

    sikrit_footer(view.embed, locale)

    if __debug__:
        debug_footer(view.embed)

    await inter.response.send_message(
        embed=view.embed, file=file, components=view.paginator.page, ephemeral=True
    )
    await store.listen(plugin.bot, timeout=180)
    await inter.edit_original_response(components=None)


@mech.sub_command(name="import")
@commands.max_concurrency(1, commands.BucketType.user)
async def import_(
    inter: CommandInteraction, gettext: i18n.GetText, player: Player, file: Attachment
) -> None:
    """Import mechs from a .JSON file. {{ MECH_IMPORT }}

    Parameters
    ----------
    file: A .JSON file as exported from WU. {{ MECH_IMPORT_FILE }}
    """
    # file size of 64KiB sounds like a pretty beefy amount of mechs
    MAX_SIZE = 1 << 16

    if file.size > MAX_SIZE:
        max_size, prefix = fold_binary_prefix(MAX_SIZE)
        msg = gettext("import-size-error").format(size=max_size, unit=prefix + "B")
        raise commands.UserInputError(msg)
    # the content type should be application/json,
    # but we may as well just rely on the loader to fail

    default_pack = DEFAULT_PACK.get_nowait()
    data = await file.read()
    try:
        mechs, failed = load_mechs(data, default_pack)

    except JSONDecodeError as exc:
        raise commands.UserInputError(str(exc)) from exc

    except DataError as exc:
        msg = f'{gettext("import-parse-error")}\n{exc}'
        raise commands.UserInputError(msg) from exc

    except Exception as exc:
        # holy moly
        msg = "Parsing failed with unexpected error:"
        plugin.logger.warning(msg, exc_info=exc)
        raise commands.UserInputError from exc

    string_builder = io.StringIO()

    if failed:
        string_builder.write(gettext("import-failed"))
        string_builder.write("\n")
        for reason in failed:
            string_builder.write(f"{reason}\n")

    if mechs:
        # TODO: warn about overwriting
        for mech, name in mechs:
            player.create_build(name, mech)
        string_builder.write(gettext("import-loaded"))
        string_builder.write(" ")
        string_builder.write(", ".join(f"`{name}`" for _, name in mechs))

    else:
        string_builder.write(gettext("import-none"))

    await inter.response.send_message(string_builder.getvalue(), ephemeral=True)


@mech.sub_command()
async def export(
    inter: CommandInteraction,
    player: Player,  # format: typing.Literal["json", "toml"] = "json"
    gettext: i18n.GetText,
) -> None:
    """Export your mechs into a WU-compatible .JSON file. {{ MECH_EXPORT }}

    Parameters
    ----------
    format: The file format to output data in.\
            Formats other than .json are not supported by WU. {{ MECH_EXPORT_FORMAT }}
    """
    build_count = len(player.builds)

    if build_count == 0:
        return await inter.response.send_message(gettext("export-none"), ephemeral=True)

    default_pack = DEFAULT_PACK.get_nowait()
    all_builds = tuple(player.builds.values())

    if build_count == 1:
        mechs = [all_builds[0].as_mech()]
        file = bytes_to_file(dump_mechs(mechs, default_pack.data.key), "mechs.json")
        return await inter.response.send_message(file=file, ephemeral=True)

    options = [(build.name, str(build.id)) for build in all_builds]
    del options[ComponentLimits.select_options :]
    options = dict(options)

    mech_select = ui.StringSelect(
        placeholder=gettext("export-select"),
        max_values=len(options),
        options=options,
    )
    button_all = ActionButton(label=gettext("export-all"))

    content = (
        None
        if build_count <= ComponentLimits.select_options
        else gettext("export-items-warning").format(
            build_count=build_count, display_limit=ComponentLimits.select_options
        )
    )
    await inter.response.send_message(
        content=content,
        components=[[mech_select], [button_all]],
        ephemeral=True,
    )
    try:
        component_inter, component = await wait_for_components(
            mech_select,
            button_all,
            client=plugin.bot,
            user_id=inter.author.id,
            timeout=600,
        )

    except TimeoutError:
        return await inter.delete_original_response()

    if component is button_all:
        mechs = (build.as_mech() for build in all_builds)

    else:
        assert component_inter.values is not None
        mechs = (player.builds[uuid.UUID(str_id)].as_mech() for str_id in component_inter.values)

    file = bytes_to_file(dump_mechs(mechs, default_pack.data.key), "mechs.json")
    await component_inter.response.edit_message(file=file, components=None)


build.autocomplete("name")(mech_name_autocomplete)


setup, teardown = plugin.create_extension_handlers()
