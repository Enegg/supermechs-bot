from enum import Enum

__all__ = ("OPTION_LIMIT", "RESPONSE_TIMEOUT", "ComponentLimits", "EmbedLimits", "MessageLimits")

OPTION_LIMIT = 25
"""Limit related to select and autocomplete options."""
RESPONSE_TIMEOUT = 3
"""Maximum amount of time in seconds the bot can take to respond to an interaction."""


class EmbedLimits(int, Enum):
    title = 256
    description = 4096
    fields = 10
    field_name = 256
    field_value = 1024
    footer_text = 2048
    author_name = 256
    total = 6000


class MessageLimits(int, Enum):
    content = 2000
    embeds = 10
    files = 10
    action_rows = 5


class ComponentLimits(int, Enum):
    row_width = 5
    custom_id = 100
    button_label = 80
    select_options = 25
    select_placeholder = 150
    select_option_label = 100
    select_option_value = 100
    select_option_description = 100
    text_input_label = 45
    text_input_value = 4000
    text_input_placeholder = 100
