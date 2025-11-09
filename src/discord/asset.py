from typing import TYPE_CHECKING, Literal, Self, cast as cast_type

import attrs

from discord.urls import ALT_CDN, CDN

__all__ = ("Asset",)

type Png = Literal["png"]
type Gif = Literal["gif"]
type Lottie = Literal["json"]
type Static = Literal["webp", "jpeg", "jpg"] | Png
type StaticOrGif = Static | Gif


@attrs.frozen
class Asset[FmtT: StaticOrGif | Lottie]:
    type Size = Literal[0, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]

    type PngAsset = Asset[Png]
    type GifAsset = Asset[Gif]
    type LottieAsset = Asset[Lottie]
    type StaticAsset = Asset[Static]
    type StaticOrGifAsset = Asset[StaticOrGif]

    base_url: str
    """The base URL of the asset, excluding format and size."""
    format: FmtT = cast_type("FmtT", "png")
    """The file format of the asset."""
    size: Size = 0
    """The dimensions of the image asset. `0` uses the default size for that asset."""

    if TYPE_CHECKING:

        def __init__(self, base_url: str, format: FmtT = "png", size: Size = 0) -> None: ...

    def with_format(self, format: FmtT, /) -> Self:
        # TODO: copy.replace
        return attrs.evolve(self, format=format)

    def with_size(self, size: Size, /) -> Self:
        return attrs.evolve(self, size=size)

    @property
    def full_url(self) -> str:
        """The full URL of the asset, including format and size."""
        if self.size == 0:
            return f"{self.base_url}.{self.format}"
        return f"{self.base_url}.{self.format}?size={self.size}"

    @classmethod
    def _from_icon(
        cls,
        type: Literal["app", "team", "role"],
        object_id: int,
        icon_hash: str,
    ) -> StaticAsset:
        return Asset(base_url=f"{CDN}/{type}-icons/{object_id}/{icon_hash}")

    @classmethod
    def from_emoji(cls, emoji_id: int, animated: bool = False) -> StaticOrGifAsset:
        return Asset(base_url=f"{CDN}/emojis/{emoji_id}", format="gif" if animated else "webp")

    @classmethod
    def guild_icon(cls, guild_id: int, guild_icon: str) -> StaticOrGifAsset:
        return Asset(
            base_url=f"{CDN}/icons/{guild_id}/{guild_icon}",
            format="gif" if guild_icon.startswith("a_") else "png",
        )

    @classmethod
    def guild_splash(cls, guild_id: int, splash: str) -> StaticAsset:
        return Asset(base_url=f"{CDN}/splashes/{guild_id}/{splash}")

    @classmethod
    def guild_discovery_splash(cls, guild_id: int, splash: str) -> StaticAsset:
        return Asset(base_url=f"{CDN}/discovery-splashes/{guild_id}/{splash}")

    @classmethod
    def guild_banner(cls, guild_id: int, banner: str) -> StaticOrGifAsset:
        return Asset(
            base_url=f"{CDN}/banners/{guild_id}/{banner}",
            format="gif" if banner.startswith("a_") else "png",
        )

    @classmethod
    def user_banner(cls, user_id: int, banner: str) -> StaticOrGifAsset:
        return Asset(
            base_url=f"{CDN}/banners/{user_id}/{banner}",
            format="gif" if banner.startswith("a_") else "png",
        )

    @classmethod
    def default_user_avatar(cls, index: int) -> PngAsset:
        return Asset(base_url=f"{CDN}/embed/avatars/{index}")

    @classmethod
    def user_avatar(cls, user_id: int, avatar: str) -> StaticOrGifAsset:
        return Asset(
            base_url=f"{CDN}/avatars/{user_id}/{avatar}",
            format="gif" if avatar.startswith("a_") else "png",
        )

    @classmethod
    def guild_member_avatar(cls, guild_id: int, user_id: int, avatar: str) -> StaticOrGifAsset:
        return Asset(
            base_url=f"{CDN}/guilds/{guild_id}/users/{user_id}/avatars/{avatar}",
            format="gif" if avatar.startswith("a_") else "png",
        )

    @classmethod
    def avatar_decoration(cls, asset: str) -> PngAsset:
        return Asset(base_url=f"{CDN}/avatar-decoration-presets/{asset}")

    @classmethod
    def application_icon(cls, app_id: int, icon: str) -> StaticAsset:
        return cls._from_icon("app", app_id, icon)

    @classmethod
    def application_cover(cls, app_id: int, cover: str) -> StaticAsset:
        return cls._from_icon("app", app_id, cover)

    @classmethod
    def application_asset(cls, app_id: int, asset_id: str) -> StaticAsset:
        return Asset(base_url=f"{CDN}/app-assets/{app_id}/{asset_id}")

    @classmethod
    def achievement_icon(cls, app_id: int, achievement_id: str, icon: str) -> StaticAsset:
        return Asset(
            base_url=f"{CDN}/app-assets/{app_id}/achievements/{achievement_id}/icons/{icon}"
        )

    @classmethod
    def store_page_asset(cls, app_id: int, asset_id: str) -> StaticAsset:
        return Asset(base_url=f"{CDN}/app-assets/{app_id}/store/{asset_id}")

    @classmethod
    def sticker_pack_banner(cls, asset_id: str) -> StaticAsset:
        # hardcoded ID. Fun!
        return Asset(base_url=f"{CDN}/app-assets/710982414301790216/store/{asset_id}")

    @classmethod
    def team_icon(cls, team_id: int, icon: str) -> StaticAsset:
        return cls._from_icon("team", team_id, icon)

    @classmethod
    def sticker_static(cls, sticker_id: int) -> PngAsset:
        return Asset(base_url=f"{CDN}/stickers/{sticker_id}", format="png")

    @classmethod
    def sticker_lottie(cls, sticker_id: int) -> LottieAsset:
        return Asset(base_url=f"{CDN}/stickers/{sticker_id}", format="json")

    @classmethod
    def sticker_gif(cls, sticker_id: int) -> GifAsset:
        return Asset(base_url=f"{ALT_CDN}/stickers/{sticker_id}", format="gif")

    @classmethod
    def role_icon(cls, role_id: int, icon: str) -> StaticAsset:
        return cls._from_icon("role", role_id, icon)

    @classmethod
    def guild_scheduled_event_cover(cls, event_id: int, cover: str) -> StaticAsset:
        return Asset(base_url=f"{CDN}/guild-events/{event_id}/{cover}")

    @classmethod
    def guild_member_banner(cls, guild_id: int, user_id: int, banner: str) -> StaticOrGifAsset:
        return Asset(
            base_url=f"{CDN}/guilds/{guild_id}/users/{user_id}/banners/{banner}",
            format="gif" if banner.startswith("a_") else "png",
        )
