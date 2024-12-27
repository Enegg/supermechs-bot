from collections import abc
from enum import Enum, auto
from typing import Literal, Self, TypeAlias, TypedDict

import attrs

import disnake
from disnake import ui

__all__ = ("MessageTemplate",)

Components: TypeAlias = (
    ui.MessageUIComponent
    | abc.Sequence[ui.MessageUIComponent | abc.Sequence[ui.MessageUIComponent]]
)


class EditMode(Enum):
    KEEP = auto()
    REMOVE = auto()


class SendParams(TypedDict, total=False):
    content: str | None
    embeds: list[disnake.Embed]
    files: list[disnake.File]
    components: Components
    flags: disnake.MessageFlags


class EditParams(TypedDict, total=False):
    content: str | None
    embeds: list[disnake.Embed]
    files: list[disnake.File]
    attachments: list[disnake.Attachment] | None
    components: Components


@attrs.define(kw_only=True)
class MessageTemplate:
    content: str | EditMode = attrs.field(default=EditMode.KEEP, kw_only=False)
    embeds: list[disnake.Embed] | Literal[EditMode.KEEP] = EditMode.KEEP
    files: list[disnake.File] | Literal[EditMode.KEEP] = EditMode.KEEP
    attachments: EditMode = EditMode.KEEP
    components: Components | Literal[EditMode.KEEP] = EditMode.KEEP

    @classmethod
    def with_purged_contents(cls) -> Self:
        return cls(
            content=EditMode.REMOVE,
            embeds=[],
            files=[],
            attachments=EditMode.REMOVE,
            components=(),
        )

    def with_content(self, content: str | EditMode, /) -> Self:
        self.content = content
        return self

    def add_embeds(self, *embeds: disnake.Embed) -> Self:
        if isinstance(self.embeds, EditMode):
            self.embeds = list(embeds)

        else:
            self.embeds += embeds
        return self

    def with_embeds(self, embeds: abc.Iterable[disnake.Embed] | EditMode) -> Self:
        if not isinstance(embeds, EditMode):
            self.embeds = list(embeds)

        elif embeds is EditMode.REMOVE:
            self.embeds = []

        else:
            self.embeds = embeds

        return self

    def add_files(self, *files: disnake.File) -> Self:
        if isinstance(self.files, EditMode):
            self.files = list(files)

        else:
            self.files += files
        return self

    def with_files(self, files: abc.Iterable[disnake.File] | EditMode) -> Self:
        if not isinstance(files, EditMode):
            self.files = list(files)

        elif files is EditMode.REMOVE:
            self.files = []

        else:
            self.files = files
        return self

    def with_attachments(self, attachments: EditMode) -> Self:
        self.attachments = attachments
        return self

    def with_components(self, components: Components | EditMode) -> Self:
        if components is EditMode.REMOVE:
            components = ()

        self.components = components
        return self

    def get_send_params(self) -> SendParams:
        params: SendParams = {}

        if not isinstance(self.content, EditMode):
            params["content"] = self.content

        if self.embeds is not EditMode.KEEP and self.embeds:
            params["embeds"] = self.embeds

        if self.files is not EditMode.KEEP and self.files:
            params["files"] = self.files

        return params

    def get_edit_params(self) -> EditParams:
        params: EditParams = {}

        if self.content is EditMode.REMOVE:
            params["content"] = None

        elif self.content is not EditMode.KEEP:
            params["content"] = self.content

        if self.embeds is not EditMode.KEEP:
            params["embeds"] = self.embeds

        if self.files is not EditMode.KEEP:
            params["files"] = self.files

        if self.attachments is not EditMode.KEEP:
            params["attachments"] = None

        if self.components is not EditMode.KEEP:
            params["components"] = self.components

        return params
