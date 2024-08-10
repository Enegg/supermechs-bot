import disnake

__all__ = ("debug_footer",)


def debug_footer(embed: disnake.Embed, /, *, replace: bool = False) -> None:
    """Add a footer to the embed with the character total and values of url fields."""
    if replace:
        embed.remove_footer()

    parts: list[str] = ["Debug:", f"Size: {len(embed)}"]

    if existing_footer := embed.footer.text:
        parts.insert(0, existing_footer)

    if (url := embed.image.url) is not None and url.startswith("attachment://"):
        parts.append(f"Image: {url}")

    if (url := embed.thumbnail.url) is not None and url.startswith("attachment://"):
        parts.append(f"Thumb: {url}")

    embed.set_footer(text="\n".join(parts))
