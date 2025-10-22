import enum

__all__ = ("ComponentLimits", "EmbedLimits", "InteractionLimits", "MessageLimits")


class EmbedLimits(enum.IntEnum):
    """Limits imposed on embeds & their sub-components."""

    title = 256
    """Maximum length of an embed's title."""
    description = 4096
    """Maximum length of an embed's description."""
    fields = 10
    """Maximum number of fields per embed."""
    field_name = 256
    """Maximum length of an embed's field's name."""
    field_value = 1024
    """Maximum length of an embed's field's value."""
    footer_text = 2048
    """Maximum length of an embed's footer's text."""
    author_name = 256
    """Maximum length of an embed's author's name."""
    total = 6000
    """Maximum number of characters over all parts of an embed."""


class MessageLimits(enum.IntEnum):
    """Limits imposed on sending messages."""

    content = 2000
    """Maximum length of a message's content."""
    embeds = 10
    """Maximum number of embeds per message."""
    files = 10
    """Maximum number of files per message."""
    action_rows = 5
    """Maximum number of action rows per message."""


class ComponentLimits(enum.IntEnum):
    """Limits imposed on UI components."""

    custom_id = 100
    """Maximum length of a component's custom id."""
    buttons_in_row = 5
    """Maximum number of buttons within an action row."""
    button_label = 80
    """Maximum length of a button's label."""
    select_options = 25
    """Maximum number of select options per string select menu."""
    select_placeholder = 150
    """Maximum length of a select's placeholder."""
    select_option_label = 100
    """Maximum length of a select's option's label."""
    select_option_value = 100
    """Maximum length of a select's option's value."""
    select_option_description = 100
    """Maximum length of a select's option's description."""
    text_display_content = 4000
    """Maximum length of a text display's content."""
    text_input_value = 4000
    """Maximum length of a modal's text input's value."""
    text_input_placeholder = 100
    """Maximum length of a modal's text input's placeholder."""
    media_description = 1024
    """Maximum length of a media component's description."""
    gallery_items = 10
    """Maximum range of items a MediaGallery can have."""
    label_label = 45
    """Maximum length of a Label's label."""


class InteractionLimits(enum.IntEnum):
    """Limits imposed on responding to interactions."""

    autocomplete_options = 25
    """Maximum number of options an autocomplete can return."""
    response_timeout = 3
    """Number of seconds until discord times out an interaction."""
    deferred_response_timeout = 60 * 15
    """Number of seconds an interaction remains valid for after deferring."""
