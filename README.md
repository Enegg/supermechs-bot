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

[SuperMechs](https://www.supermechs.com/)-themed discord bot, featuring:
- `/item` - lookup item statistics, transformation stages, upgrade levels
- `/legacy-item` - like `/item`, but for legacy items
- (TODO) `/compare` - compare stats of 2+ items
- (TODO) `/campaign` - lookup rewards & layout of campaign missions

## Installation
1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/#installing-uv)
2. `uv sync`
3. Create a `.env` file from [template](example.env)
4.  Run via `uv run src/app`
    - in VS Code, F5 runs configured debugger

## environment variables
| Variable          | Type | Description                                                      |
| ----------------- | ---- | ---------------------------------------------------------------- |
| `BOT_TOKEN`*      | str  | Discord bot token                                                |
| `DEV_GUILD_ID`*   | int  | ID of a guild dev-only commands will be registered to            |
| `LOGS_CHANNEL_ID` | int  | ID of a text channel error messages will be sent to              |
| `ITEM_PACK_URI`   | str  | Path/url of the items pack. If omitted, most features won't work |
| `GFX_PACK_URI`    | str  | Path/url of a graphics pack. Used for item packs in V3 format    |

\* required<br>

## command line arguments
| Flag                   | Type | Default      | Description                                   |
| ---------------------- | ---- | ------------ | --------------------------------------------- |
| `--token`              | str  |              | Bot token to use                              |
| `--env`                | path | `"dev.env"`  | Path to a .env file                           |
| `--dev-guild`          | int  |              | ID of the bot's developer guild               |
| `--item-pack`          | URI  |              | Path or URL of an item pack                   |
| `--gfx-pack`           | URI  |              | Path or URL of a graphics pack                |

\* `False` if running with [`python -O` flag](https://docs.python.org/3/using/cmdline.html#cmdoption-O)
