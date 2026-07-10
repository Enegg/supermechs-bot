import logging
import os
from collections import abc
from typing import NewType

import disnake
from disnake.ext import commands

type Factory[RetT] = abc.Callable[[], RetT]
"""0-argument callable returning an object of given type."""
type Pathish = os.PathLike[str] | str
"""Path-like or a string representing a path."""
type AsyncFunc[**P, RetT] = abc.Callable[P, abc.Awaitable[RetT]]
"""Function yielding an awaitable."""
ByteSize = NewType("ByteSize", int)

type FilterType = logging.Filter | abc.Callable[[logging.LogRecord], logging.LogRecord | bool]
"""Type of an object acceptable as a Filter."""

# disnake
type Bot = commands.InteractionBot
type Interaction = disnake.Interaction[Bot]
type CommandInteraction = disnake.CommandInteraction[Bot]
type MessageInteraction = disnake.MessageInteraction[Bot]
type ModalInteraction = disnake.ModalInteraction[Bot]
