import typing

from disnake import Locale

from app import init, paths, structs
from app.core.state import I18nStore

from supermechs.enums import ItemStat


def test_locales() -> None:
    i18n = I18nStore()
    init.load_i18n(paths.LOCALE_DIR, i18n)

    for file_path in paths.LOCALE_DIR.glob(f"*{paths.LOCALE_FILE_EXT}"):
        locale = Locale[file_path.stem]
        missing: list[str] = []

        for stat in ItemStat:
            try:
                i18n.stat_l10ns[stat, locale]

            except KeyError:
                missing.append(stat.name)

        for key in typing.get_args(structs.I18nKey.__value__):
            try:
                i18n.message_l10ns[key, locale]

            except KeyError:
                missing.append(key)

        if missing:
            print(f"{locale} is missing: {', '.join(missing)}")
