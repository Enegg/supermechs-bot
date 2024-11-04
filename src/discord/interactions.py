from collections import abc
from typing import Final, Self, TypeAlias

import attrs
from monads.option import Option, Some, from_none

import disnake
from disnake import ui
from disnake.utils import MISSING

__all__ = ("MessageTemplate",)

Components: TypeAlias = (
    ui.MessageUIComponent
    | abc.Sequence[ui.MessageUIComponent | abc.Sequence[ui.MessageUIComponent]]
)


@attrs.define
class MessageTemplate:
    content: Final[Option[str]]
    embeds: Final[abc.Sequence[disnake.Embed]]
    files: Final[abc.Sequence[disnake.File]]
    components: Final[Components]
    allowed_mentions: Final[Option[disnake.AllowedMentions]]
    flags: Final[Option[disnake.MessageFlags]]

    def __init__(
        self,
        content: str | None = None,
        *,
        embeds: abc.Sequence[disnake.Embed] = (),
        files: abc.Sequence[disnake.File] = (),
        components: Components = (),
        allowed_mentions: disnake.AllowedMentions | None = None,
        flags: disnake.MessageFlags | None = None,
    ) -> None:
        self.content = from_none(content)
        self.embeds = embeds
        self.files = files
        self.components = components
        self.allowed_mentions = from_none(allowed_mentions)
        self.flags = from_none(flags)

    def with_content(self, content: str, /) -> Self:
        return attrs.evolve(self, content=Some(content))

    def with_embeds(self, *embeds: disnake.Embed) -> Self:
        return attrs.evolve(self, embeds=(*self.embeds, embeds))

    def with_files(self, *files: disnake.File) -> Self:
        return attrs.evolve(self, files=(*self.files, files))

    def ephemeral(self) -> Self:
        flags = self.flags.unwrap_or_else(disnake.MessageFlags) | disnake.MessageFlags.ephemeral
        return attrs.evolve(self, flags=Some(flags))

    async def send_response(self, inter: disnake.Interaction, /, *, followup: bool = False) -> None:
        sender = inter.followup.send if followup else inter.response.send_message
        await sender(
            content=self.content.unwrap_or(None),
            embeds=list(self.embeds),
            files=list(self.files),
            allowed_mentions=self.allowed_mentions.unwrap_or(MISSING),
            components=self.components,
            flags=self.flags.unwrap_or(MISSING),
        )

    async def edit_response(self, inter: disnake.Interaction, /) -> None:
        await inter.response.edit_message(
            content=self.content.unwrap_or(MISSING),
            embeds=list(self.embeds),
            files=list(self.files),
            allowed_mentions=self.allowed_mentions.unwrap_or(MISSING),
            components=self.components,
        )

    async def send_or_edit_response(
        self, inter: disnake.Interaction, /, *, edit: bool = False
    ) -> None:
        method = self.edit_response if edit else self.send_response
        await method(inter)

    async def send_any_response(self, inter: disnake.Interaction, /) -> None:
        await self.send_response(inter, followup=inter.response.is_done())

    async def send_to_channel(self, channel: disnake.abc.Messageable, /) -> None:
        await channel.send(
            content=self.content.unwrap_or(None),
            embeds=list(self.embeds),
            files=list(self.files),
            flags=self.flags.unwrap_or(MISSING),
            allowed_mentions=self.allowed_mentions.unwrap_or(MISSING),
            components=self.components,
        )
