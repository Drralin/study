import shlex

from .errors import FMError
from .operations import fmt_size

HELP = [
    ("Папки", [
        ("dnew <папка>", "создать папку"),
        ("ddel <папка>", "удалить папку вместе с содержимым"),
        ("dgo <папка>", "перейти в папку"),
        ("dup", "подняться на уровень вверх"),
        ("dlist [папка]", "показать содержимое папки"),
        ("here", "показать текущую папку"),
    ]),
    ("Файлы", [
        ("fnew <файл>", "создать пустой файл"),
        ("fwrite <файл> <текст>", "записать текст в файл (\\n — перевод строки)"),
        ("fadd <файл> <текст>", "дописать текст в конец файла"),
        ("fshow <файл>", "показать содержимое текстового файла"),
        ("fdel <файл>", "удалить файл"),
        ("fcopy <файл> <папка>", "скопировать файл в папку"),
        ("fmove <файл> <папка>", "переместить файл в папку"),
        ("fren <файл> <новое_имя>", "переименовать файл"),
    ]),
    ("Дополнительно", [
        ("fpack <файл|папка> <архив>", "упаковать в zip-архив"),
        ("funpack <архив> [папка]", "распаковать zip-архив"),
        ("quota", "занятое и свободное место"),
        ("help", "эта справка"),
        ("quit", "выход из файлового менеджера"),
    ]),
]


class CommandLine:
    def __init__(self, fm, user):
        self.fm = fm
        self.user = user
        self.running = True
        self.commands = {
            "dnew": (1, self.cmd_dnew), "ddel": (1, self.cmd_ddel), "dgo": (1, self.cmd_dgo),
            "dup": (0, self.cmd_dup), "dlist": (0, self.cmd_dlist), "here": (0, self.cmd_here),
            "fnew": (1, self.cmd_fnew), "fwrite": (2, self.cmd_fwrite), "fadd": (2, self.cmd_fadd),
            "fshow": (1, self.cmd_fshow), "fdel": (1, self.cmd_fdel), "fcopy": (2, self.cmd_fcopy),
            "fmove": (2, self.cmd_fmove), "fren": (2, self.cmd_fren), "fpack": (2, self.cmd_fpack),
            "funpack": (1, self.cmd_funpack), "quota": (0, self.cmd_quota), "help": (0, self.cmd_help),
            "quit": (0, self.cmd_quit),
        }

    def prompt(self):
        return f"{self.user}@fm:{self.fm.where()}> "

    def run(self):
        print("Введите help для списка команд.")
        while self.running:
            try:
                line = input(self.prompt())
            except (EOFError, KeyboardInterrupt):
                print()
                break
            self.execute(line)
        print("До свидания!")

    def execute(self, line):
        try:
            args = shlex.split(line)
        except ValueError as e:
            print(f"Ошибка разбора команды: {e}")
            return
        if not args:
            return
        name, args = args[0].lower(), args[1:]
        if name not in self.commands:
            print(f"Неизвестная команда «{name}». Список команд — help")
            return
        need, handler = self.commands[name]
        if len(args) < need:
            print(f"Команде {name} не хватает аргументов. Подсказка — help")
            return
        try:
            handler(*args)
        except FMError as e:
            print(f"Ошибка: {e}")
        except TypeError:
            print(f"Лишние аргументы для команды {name}. Подсказка — help")
        except OSError as e:
            print(f"Ошибка ОС: {e.strerror}")

    def cmd_dnew(self, name):
        print(f"Создана папка {self.fm.make_dir(name)}")

    def cmd_ddel(self, name):
        print(f"Удалена папка {self.fm.remove_dir(name)}")

    def cmd_dgo(self, name):
        print(f"Текущая папка: {self.fm.enter(name)}")

    def cmd_dup(self):
        print(f"Текущая папка: {self.fm.leave()}")

    def cmd_here(self):
        print(self.fm.where())

    def cmd_dlist(self, name=None):
        items = self.fm.listing(name)
        if not items:
            print("(папка пуста)")
        for item, is_dir, size in items:
            print(f"  [папка] {item}/" if is_dir else f"  {fmt_size(size):>10}  {item}")

    def cmd_fnew(self, name):
        print(f"Создан файл {self.fm.make_file(name)}")

    def cmd_fwrite(self, name, *words):
        size = self.fm.write_file(name, " ".join(words).replace("\\n", "\n") + "\n")
        print(f"Записано {size} байт в {name}")

    def cmd_fadd(self, name, *words):
        size = self.fm.write_file(name, " ".join(words).replace("\\n", "\n") + "\n", append=True)
        print(f"Дописано {size} байт в {name}")

    def cmd_fshow(self, name):
        text = self.fm.read_file(name)
        print(f"----- {name} -----")
        print(text, end="" if text.endswith("\n") or not text else "\n")
        print("-" * (len(name) + 12))

    def cmd_fdel(self, name):
        print(f"Удалён файл {self.fm.remove_file(name)}")

    def cmd_fcopy(self, name, dest):
        print(f"Файл скопирован: {self.fm.copy_file(name, dest)}")

    def cmd_fmove(self, name, dest):
        print(f"Файл перемещён: {self.fm.move_file(name, dest)}")

    def cmd_fren(self, name, new_name):
        print(f"Файл переименован: {self.fm.rename_file(name, new_name)}")

    def cmd_fpack(self, name, archive):
        path, count = self.fm.pack(name, archive)
        print(f"Создан архив {path}, файлов: {count}")

    def cmd_funpack(self, archive, dest=None):
        path, count = self.fm.unpack(archive, dest)
        print(f"Распаковано файлов: {count} в {path}")

    def cmd_quota(self):
        used, total = self.fm.quota_info()
        if total:
            print(f"Занято {fmt_size(used)} из {fmt_size(total)}, свободно {fmt_size(max(total - used, 0))}"
                  f" ({used * 100 / total:.1f}%)")
        else:
            print(f"Занято {fmt_size(used)}, квота не задана")

    def cmd_help(self):
        for title, rows in HELP:
            print(f"{title}:")
            for cmd, text in rows:
                print(f"  {cmd:<28} {text}")

    def cmd_quit(self):
        self.running = False
