import argparse
import getpass
import sys

from filemanager.cli import CommandLine
from filemanager.config import DEFAULT_SETTINGS, load_settings
from filemanager.errors import FMError
from filemanager.operations import FileManager
from filemanager.users import UserStore


def authorize(store):
    while True:
        print("1 — вход, 2 — регистрация, 0 — выход")
        try:
            choice = input("Выбор: ").strip()
            if choice == "0":
                return None
            if choice not in ("1", "2"):
                print("Введите 1, 2 или 0")
                continue
            name = input("Имя пользователя: ").strip()
            password = getpass.getpass("Пароль: ")
            if choice == "2":
                if password != getpass.getpass("Повторите пароль: "):
                    print("Пароли не совпадают")
                    continue
                store.register(name, password)
                print(f"Пользователь {name} зарегистрирован, создана домашняя папка")
            else:
                store.login(name, password)
            return name
        except FMError as e:
            print(f"Ошибка: {e}")
        except (EOFError, KeyboardInterrupt):
            print()
            return None


def main():
    parser = argparse.ArgumentParser(description="Учебный файловый менеджер")
    parser.add_argument("--settings", default=DEFAULT_SETTINGS, help="путь к файлу настроек")
    parser.add_argument("--tui", action="store_true", help="псевдографический интерфейс")
    args = parser.parse_args()

    try:
        settings = load_settings(args.settings)
    except (OSError, ValueError, KeyError) as e:
        sys.exit(f"Не удалось прочитать настройки {args.settings}: {e}")

    print(f"Файловый менеджер. Рабочая папка: {settings.workspace}")
    store = UserStore(settings.users_file, settings.workspace)
    user = authorize(store)
    if not user:
        return
    fm = FileManager(store.home(user), settings.quota_bytes, settings.encoding)
    if args.tui:
        try:
            from filemanager.tui import run_tui
        except ImportError:
            sys.exit("Для псевдографического режима в Windows установите пакет: pip install windows-curses")
        run_tui(fm, user, settings)
    else:
        CommandLine(fm, user).run()


if __name__ == "__main__":
    main()
