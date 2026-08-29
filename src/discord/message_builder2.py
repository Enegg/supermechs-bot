from collections import abc
from typing import TYPE_CHECKING, Any, Final

import attrs

from disnake import (
    ApplicationCommandInteraction as _CommandInteraction,
    Color,
    File,
    MessageFlags,
    MessageInteraction as _MessageInteraction,
    ui,
)

if TYPE_CHECKING:
    from disnake.ui._types import MessageTopLevelComponent as _MessageTopLevelComponent
    from disnake.ui.container import ContainerChildUIComponent as _ContainerChildUIComponent

__all__ = ("MessageBuilder",)

type MessageComponent = _MessageTopLevelComponent
type ContainerChild = _ContainerChildUIComponent
type MessageInteraction = _MessageInteraction[Any]
type CommandInteraction = _CommandInteraction[Any]


@attrs.define
class MessageBuilder:
    components: Final[list[MessageComponent]] = attrs.Factory(list)
    files: Final[list[File]] = attrs.Factory(list)

    def add_file(self, file: File, /) -> File:
        self.files.append(file)
        return file

    def add_component[Component: MessageComponent](self, component: Component, /) -> Component:
        self.components.append(component)
        return component

    def container(
        self,
        *components: ContainerChild,
        accent_color: Color | None = None,
        spoiler: bool = False,
        id: int = 0,
    ) -> abc.Callable[[ContainerChild], None]:
        container = ui.Container(*components, accent_colour=accent_color, spoiler=spoiler, id=id)
        self.components.append(container)
        return container.children.append

    async def followup(self, inter: MessageInteraction, /, ephemeral: bool = False) -> None:
        await inter.followup.send(
            files=self.files,
            components=self.components,
            flags=MessageFlags(ephemeral=ephemeral, is_components_v2=True),
        )

    async def send(
        self, inter: CommandInteraction | MessageInteraction, /, ephemeral: bool = False
    ) -> None:
        await inter.response.send_message(
            files=self.files,
            components=self.components,
            flags=MessageFlags(ephemeral=ephemeral, is_components_v2=True),
        )

    async def edit(self, inter: MessageInteraction, /) -> None:
        await inter.response.edit_message(files=self.files, components=self.components)
