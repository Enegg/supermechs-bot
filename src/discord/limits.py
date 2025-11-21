from typing import Final

__all__ = ("ComponentLimits", "EmbedLimits", "InteractionLimits", "MessageLimits")


class EmbedLimits:
    """Limits imposed on embeds."""

    title: Final = 256
    """Maximum length of an embed's title."""
    description: Final = 4096
    """Maximum length of an embed's description."""
    fields: Final = 10
    """Maximum number of fields per embed."""
    field_name: Final = 256
    """Maximum length of an embed's field's name."""
    field_value: Final = 1024
    """Maximum length of an embed's field's value."""
    footer_text: Final = 2048
    """Maximum length of an embed's footer's text."""
    author_name: Final = 256
    """Maximum length of an embed's author's name."""
    total: Final = 6000
    """Maximum number of characters over all parts of an embed."""


class MessageLimits:
    """Limits imposed on sending messages."""

    content: Final = 2000
    """Maximum length of a message's content."""
    embeds: Final = 10
    """Maximum number of embeds per message."""
    files: Final = 10
    """Maximum number of files per message."""
    action_rows: Final = 5
    """Maximum number of action rows per message. (v1)"""


class ComponentLimits:
    """Limits imposed on UI components."""

    custom_id: Final = 100
    """Maximum length of a component's custom id."""
    action_row_buttons: Final = 5
    """Maximum number of buttons within an action row."""
    button_label: Final = 80
    """Maximum length of a Button's label."""
    string_select_options: Final = 25
    """Maximum number of SelectOptions in a StringSelect."""
    select_placeholder: Final = 150
    """Maximum length of a Select's placeholder."""
    select_option_label: Final = 100
    """Maximum length of a SelectOption's label."""
    select_option_value: Final = 100
    """Maximum length of a SelectOption's value."""
    select_option_description: Final = 100
    """Maximum length of a SelectOption's description."""
    text_display_content: Final = 4000
    """Maximum length of a TextDisplay's content."""
    text_input_value: Final = 4000
    """Maximum length of a TextInput's value."""
    text_input_placeholder: Final = 100
    """Maximum length of a TextInput's placeholder."""
    media_description: Final = 1024
    """Maximum length of a media component's description."""
    gallery_items: Final = 10
    """Maximum number of items a MediaGallery can have."""
    label_label: Final = 45
    """Maximum length of a Label's label."""


class InteractionLimits:
    """Limits imposed on interaction responses."""

    autocomplete_options: Final = 25
    """Maximum number of options an autocomplete can return."""
    response_timeout: Final = 3
    """Number of seconds until discord times out an interaction."""
    deferred_response_timeout: Final = 60 * 15
    """Number of seconds an interaction remains valid for after deferring."""
