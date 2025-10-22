from collections import abc
from enum import Enum, auto
from typing import TYPE_CHECKING, Literal, Self, TypedDict

import attrs

import disnake

if TYPE_CHECKING:
    from disnake.ui._types import MessageComponents as _MessageComponents

__all__ = ("EditMode", "MessageBuilder")

type ComponentsV2 = _MessageComponents


class EditMode(Enum):
    KEEP = auto()
    REMOVE = auto()


class SendParams(TypedDict, total=False):
    files: list[disnake.File]
    allowed_mentions: disnake.AllowedMentions
    components: ComponentsV2
    flags: disnake.MessageFlags


class EditParams(TypedDict, total=False):
    files: list[disnake.File]
    allowed_mentions: disnake.AllowedMentions
    attachments: list[disnake.Attachment] | None
    components: ComponentsV2


@attrs.define(kw_only=True)
class MessageBuilder:
    files: list[disnake.File] | Literal[EditMode.KEEP] = EditMode.KEEP
    allowed_mentions: disnake.AllowedMentions | Literal[EditMode.KEEP] = EditMode.KEEP
    attachments: EditMode = EditMode.KEEP
    components: ComponentsV2 | Literal[EditMode.KEEP] = EditMode.KEEP

    @classmethod
    def with_purged_contents(cls) -> Self:
        return cls(files=[], attachments=EditMode.REMOVE, components=())

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

    def with_components(self, components: ComponentsV2 | EditMode) -> Self:
        if components is EditMode.REMOVE:
            components = ()

        self.components = components
        return self

    def get_send_params(self) -> SendParams:
        params: SendParams = {}

        if self.files is not EditMode.KEEP and self.files:
            params["files"] = self.files

        if self.allowed_mentions is not EditMode.KEEP:
            params["allowed_mentions"] = self.allowed_mentions

        if self.components is not EditMode.KEEP:
            params["components"] = self.components

        return params

    def get_edit_params(self) -> EditParams:
        params: EditParams = {}

        if self.files is not EditMode.KEEP:
            params["files"] = self.files

        if self.allowed_mentions is not EditMode.KEEP:
            params["allowed_mentions"] = self.allowed_mentions

        if self.attachments is not EditMode.KEEP:
            params["attachments"] = None

        if self.components is not EditMode.KEEP:
            params["components"] = self.components

        return params
