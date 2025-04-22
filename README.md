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

## Setup
- Create a `.env` file from [template](example.env)
- Ensure the `.venv` is active (`.venv\Scripts\activate`)
- Run via `python src/app`, or F5


## `.env` variables
| Variable            | Type  | Description                                           |
| ------------------- | ----- | ----------------------------------------------------- |
| `BOT_TOKEN`*        | str   | Discord bot token                                     |
| `HOME_GUILD_ID`*    | int   | ID of a guild dev-only commands will be registered to |
| `LOGS_CHANNEL_ID`   | int   | ID of a text channel error messages will be sent to   |
| `DEFAULT_PACK_URI`  | str   | Path/url of the default items pack                    |
| `MISSING_IMAGE_URI` | str   | Path/url of a placeholder image                       |
| `MAX_IMAGE_SIZE`    | int** | Max size of an image fetched from user source         |
| `CHUNK_SIZE`        | int** | Size of a chunk used while requesting data            |

\* required<br>
\*\* supports binary prefixes (10MiB, 5KiB, etc)

## CLI flags
| Flag                   | Type | Default      | Description                                   |
| ---------------------- | ---- | ------------ | --------------------------------------------- |
| `--dotenv_path`        | str  | `"dev.env"`  | Path to the .env file                         |
| `--indev`              | bool | `__debug__`* | Whether the bot is in development mode        |
| `--debug_command_sync` | bool | `__debug__`* | Whether disnake should log detailed sync info |

\* `False` if running with [`python -O` flag](https://docs.python.org/3/using/cmdline.html#cmdoption-O)
