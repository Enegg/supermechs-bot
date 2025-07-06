# supermechs-bot
<p allign="center">
  <a href="https://github.com/astral-sh/ruff">
  <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"/>
  </a>
  <a href="https://github.com/astral-sh/uv">
  <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv"/>
  </a>
  <a>
  <img src="https://img.shields.io/github/commit-activity/w/Enegg/supermechs-bot.svg?style=flat-square" alt="Commit activity"/>
  </a>
</p>

[SuperMechs](https://www.supermechs.com/)-themed discord bot featuring item lookup, comparison, mech building, & more.

## Installation
1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/#installing-uv)
2. `uv sync`
3. Create a `.env` file from [template](example.env)
4.  Run via `uv run src/app`
    - in VSCode, F5 runs configured debugger

## `.env` variables
| Variable          | Type  | Description                                                   |
| ----------------- | ----- | ------------------------------------------------------------- |
| `BOT_TOKEN`*      | str   | Discord bot token                                             |
| `DEV_GUILD_ID`*   | int   | ID of a guild dev-only commands will be registered to         |
| `LOGS_CHANNEL_ID` | int   | ID of a text channel error messages will be sent to           |
| `ITEM_PACK_URI`   | str   | Path/url of the items pack. *May* be omitted, but most features won't work |
| `GFX_PACK_URI`    | str   | Path/url of a graphics pack. Used for item packs in V3 format |
| `MAX_IMAGE_SIZE`  | int** | Max size of an image fetched from user source                 |
| `CHUNK_SIZE`      | int** | Size of a chunk used while requesting data                    |

\* required<br>
\*\* supports binary prefixes (10MiB, 5KiB, etc)

## CLI flags
| Flag                   | Type | Default      | Description                                   |
| ---------------------- | ---- | ------------ | --------------------------------------------- |
| `--dotenv_path`        | str  | `"dev.env"`  | Path to the .env file                         |
| `--indev`              | bool | `__debug__`* | Whether the bot is in development mode        |
| `--debug_command_sync` | bool | `__debug__`* | Whether disnake should log detailed sync info |

\* `False` if running with [`python -O` flag](https://docs.python.org/3/using/cmdline.html#cmdoption-O)
