# supermechs-bot
<p allign="center">
  <a href="https://github.com/astral-sh/ruff">
  <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"/>
  </a>
  <a>
  <img src="https://img.shields.io/github/commit-activity/w/Enegg/supermechs-bot.svg?style=flat-square" alt="Commit activity"/>
  </a>
</p>

[SuperMechs](https://www.supermechs.com/)-themed discord bot featuring item lookup, comparison, mech building, & more.

## Installation
0. **Python 3.10+ is required**
1. `pip install pdm`
2. `pdm install`

## `.env` variables
| Variable          | Description                                           | Type | Required                     |
| ----------------- | ----------------------------------------------------- | ---- | ---------------------------- |
| `BOT_TOKEN`       | Prod bot token                                        | str  | If running with `-O` flag    |
| `BOT_TOKEN_DEV`   | Development bot token                                 | str  | If running without `-O` flag |
| `HOME_GUILD_ID`   | ID of a guild dev-only commands will be registered to | int  | Always                       |
| `LOGS_CHANNEL_ID` | ID of a text channel the bot will send tracebacks to  | int  | Always                       |