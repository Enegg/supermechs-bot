from enum import Enum

__all__ = ("ComponentLimits", "EmbedLimits", "InteractionLimits", "MessageLimits")


class EmbedLimits(int, Enum):
    """Limits related to creating embeds."""

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


class MessageLimits(int, Enum):
    """Limits related to sending messages."""

    content = 2000
    """Maximum length of a message's content."""
    embeds = 10
    """Maximum number of embeds per message."""
    files = 10
    """Maximum number of files per message."""
    action_rows = 5
    """Maximum number of action rows per message."""


class ComponentLimits(int, Enum):
    """Limits related to sending UI components."""

    row_width = 5
    """Maximum total width of components within an action row."""
    custom_id = 100
    """Maximum length of a component's custom id."""
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
    text_input_label = 45
    """Maximum length of a modal's text input's label."""
    text_input_value = 4000
    """Maximum length of a modal's text input's value."""
    text_input_placeholder = 100
    """Maximum length of a modal's text input's placeholder."""


class InteractionLimits(int, Enum):
    """Limits related to interactions."""

    autocomplete_options = 25
    """Maximum number of options an autocomplete can return."""
    response_timeout = 3
    """Number of seconds until discord times out an interaction."""
    deferred_response_timeout = 60 * 15
    """Number of seconds an interaction remains valid for after deferring."""
