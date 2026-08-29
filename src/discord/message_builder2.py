import types
from collections import abc
from typing import TYPE_CHECKING, Any, Final, overload

import attrs

import disnake.abc
from disnake import (
    ApplicationCommandInteraction as _CommandInteraction,
    File,
    MediaGalleryItem,
    Message,
    MessageFlags,
    MessageInteraction as _MessageInteraction,
    ui,
)

if TYPE_CHECKING:
    from disnake.ui._types import (
        ActionRowMessageComponent as _ActionRowMessageComponent,
        MessageTopLevelComponent as _MessageTopLevelComponent,
    )
    from disnake.ui.container import ContainerChildUIComponent as _ContainerChildUIComponent

__all__ = ("MessageBuilder",)

type ActionRowChild = _ActionRowMessageComponent
type SectionChild = ui.TextDisplay
type ContainerChild = _ContainerChildUIComponent

type MessageActionRow = ui.ActionRow[ActionRowChild]
type ParentComponent = MessageActionRow | ui.MediaGallery | ui.Section | ui.Container
type MessageComponent = _MessageTopLevelComponent

type MessageInteraction = _MessageInteraction[Any]
type CommandInteraction = _CommandInteraction[Any]

type Coroutine[T] = types.CoroutineType[Any, Any, T]


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

    @overload
    def nested_component(
        self, component: MessageActionRow, /
    ) -> abc.Callable[[ActionRowChild], None]: ...
    @overload
    def nested_component(
        self, component: ui.MediaGallery, /
    ) -> abc.Callable[[MediaGalleryItem], None]: ...
    @overload
    def nested_component(self, component: ui.Section, /) -> abc.Callable[[SectionChild], None]: ...
    @overload
    def nested_component(
        self, component: ui.Container, /
    ) -> abc.Callable[[ContainerChild], None]: ...
    def nested_component(self, component: ParentComponent, /) -> abc.Callable[[Any], None]:
        self.components.append(component)
        match component:
            case (
                ui.MediaGallery(items=c)
                | ui.Section(children=c)
                | ui.Container(children=c)
                | ui.ActionRow(_children=c)  # pyright: ignore[reportPrivateUsage]
            ):
                return c.append

            case _:
                msg = f"{type(component).__name__} is not a parent component"
                raise TypeError(msg)

    def followup(self, inter: MessageInteraction, /, ephemeral: bool = False) -> Coroutine[None]:
        return inter.followup.send(
            files=self.files,
            components=self.components,
            flags=MessageFlags(ephemeral=ephemeral, is_components_v2=True),
        )

    def send_response(
        self, inter: CommandInteraction | MessageInteraction, /, ephemeral: bool = False
    ) -> Coroutine[None]:
        return inter.response.send_message(
            files=self.files,
            components=self.components,
            flags=MessageFlags(ephemeral=ephemeral, is_components_v2=True),
        )

    def edit_response(self, inter: MessageInteraction, /) -> Coroutine[None]:
        return inter.response.edit_message(files=self.files, components=self.components)

    def send_to(self, target: disnake.abc.Messageable, /) -> Coroutine[Message]:
        return target.send(files=self.files, components=self.components)
