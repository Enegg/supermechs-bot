import contextlib
import types
from collections import abc
from typing import TYPE_CHECKING, Any, Final, overload

import attrs

import disnake.abc
from disnake import (
    ApplicationCommandInteraction as CommandInteraction,
    File,
    MediaGalleryItem,
    Message,
    MessageFlags,
    MessageInteraction,
    WebhookMessage,
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
        """Add to the builder a component that has children. Returned callable appends to its children."""
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

    @contextlib.contextmanager
    def collect_row(self, *, id: int = 0) -> abc.Generator[abc.Callable[[ActionRowChild], None]]:
        """Context manager that returns a callable which appends buttons into an `ActionRow`.

        At exit, the `ActionRow` is created and added only if there's at least one button.

        ```
        with builder.button_row() as add_button:
            if condition_a:
                add_button(ui.Button(...))
            if condition_b:
                add_button(ui.Button(...))
        """
        # no need for try ... finally, no state to cleanup
        buttons: list[ActionRowChild] = []
        yield buttons.append
        if buttons:
            self.components.append(ui.ActionRow(*buttons, id=id))

    def followup(
        self, inter: MessageInteraction[Any], /, ephemeral: bool = False
    ) -> Coroutine[WebhookMessage]:
        return inter.followup.send(
            files=self.files,
            components=self.components,
            flags=MessageFlags(ephemeral=ephemeral, is_components_v2=True),
            wait=True,
        )

    def send_response(
        self, inter: CommandInteraction[Any] | MessageInteraction[Any], /, ephemeral: bool = False
    ) -> Coroutine[None]:
        return inter.response.send_message(
            files=self.files,
            components=self.components,
            flags=MessageFlags(ephemeral=ephemeral, is_components_v2=True),
        )

    def edit_response(self, inter: MessageInteraction[Any], /) -> Coroutine[None]:
        return inter.response.edit_message(files=self.files, components=self.components)

    def send_to(self, target: disnake.abc.Messageable, /) -> Coroutine[Message]:
        return target.send(files=self.files, components=self.components)
