import typing as t

PACK_V1: t.Final[str] = "https://gist.githubusercontent.com/ctrlraul/3b5669e4246bc2d7dc669d484db89062/raw"
"""(Depreciated) The default pack URL in V1 format. Provides an image link for each item."""

PACK_V2: t.Final[str] = "https://gist.githubusercontent.com/ctrlraul/22b71089a0dd7fef81e759dfb3dda67b/raw"
"""The default pack URL in V2 format. Provides a large spritesheet containing all item images."""

PACK_V3: t.Final[str] = "https://raw.githubusercontent.com/Enegg/Item-packs/master/items.json"
"""The default pack URL in V3 format. Provides item stats at all of their tiers."""

WU_SERVER: t.Final[str] = "https://supermechs-workshop-server.thearchives.repl.co"
"""The websocket server URL."""

MISSING_IMAGE: t.Final[str] = "https://upload.wikimedia.org/wikipedia/commons/b/b1/Missing-image-232x150.png"
"""Placeholder URL for a missing image."""
