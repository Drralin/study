import curses

from .errors import FMError
from .operations import FileManager, fmt_size

KEYS = [("F1", "Справка"), ("F2", "Имя"), ("F3", "Просм"), ("F4", "Текст"), ("F5", "Копия"),
        ("F6", "Перен"), ("F7", "Папка"), ("F8", "Удал"), ("F9", "Файл"), ("F10", "Выход")]

HELP_TEXT = """Псевдографический режим файлового менеджера

  Стрелки вверх/вниз   выбор элемента
  Enter                войти в папку / открыть файл
  Backspace            на уровень вверх
  Tab                  переключить панель
  F2  или r            переименовать файл
  F3  или v            просмотр файла
  F4  или e            дописать строку в файл
  F5  или c            копировать файл в папку другой панели
  F6  или m            переместить файл в папку другой панели
  F7  или n            создать папку
  F8  или d            удалить файл или папку
  F9  или f            создать пустой файл
  F10 или q            выход

Нажмите любую клавишу"""


class Panel:
    def __init__(self, fm):
        self.fm = fm
        self.index = 0
        self.top = 0
        self.items = []
        self.refresh()

    def refresh(self):
        self.items = ([("..", True, 0)] if self.fm.box.cwd != self.fm.box.root else []) + self.fm.listing()
        self.index = min(self.index, max(len(self.items) - 1, 0))

    def current(self):
        return self.items[self.index] if self.items else None


class App:
    def __init__(self, screen, fm, user, settings):
        self.screen = screen
        self.user = user
        root = fm.box.root
        self.panels = [Panel(fm), Panel(FileManager(root, fm.quota, fm.encoding))]
        self.active = 0
        self.message = f"Добро пожаловать, {user}! F1 — справка"
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLUE)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_CYAN)

    @property
    def panel(self):
        return self.panels[self.active]

    @property
    def other(self):
        return self.panels[1 - self.active]

    def draw_panel(self, panel, x, width, height, active):
        win = self.screen
        blue = curses.color_pair(1)
        for row in range(height):
            win.addstr(1 + row, x, " " * width, blue)
        title = f" {panel.fm.where()} "
        win.addstr(1, x, "┌" + "─" * (width - 2) + "┐", blue)
        win.addstr(1, x + max(1, (width - len(title)) // 2), title[:width - 2],
                   curses.color_pair(2) if active else blue)
        for row in range(2, height):
            win.addstr(row, x, "│", blue)
            win.addstr(row, x + width - 1, "│", blue)
        win.addstr(height, x, "└" + "─" * (width - 2) + "┘", blue)
        win.addstr(2, x + 1, f" {'Имя':<{width - 15}}{'Размер':>11} ", curses.color_pair(3))
        rows = height - 3
        if panel.index < panel.top:
            panel.top = panel.index
        if panel.index >= panel.top + rows:
            panel.top = panel.index - rows + 1
        for i, (name, is_dir, size) in enumerate(panel.items[panel.top:panel.top + rows]):
            label = ("/" + name) if is_dir and name != ".." else name
            info = "<ПАПКА>" if is_dir else fmt_size(size)
            text = f" {label[:width - 15]:<{width - 15}}{info:>11} "
            attr = blue | (curses.A_BOLD if is_dir else 0)
            if active and panel.top + i == panel.index:
                attr = curses.color_pair(2)
            win.addstr(3 + i, x + 1, text, attr)

    def draw(self):
        self.screen.erase()
        h, w = self.screen.getmaxyx()
        used, total = self.panels[0].fm.quota_info()
        quota = f"квота: {fmt_size(used)} / {fmt_size(total)}" if total else f"занято: {fmt_size(used)}"
        header = f" Файловый менеджер — {self.user}   {quota} "
        self.screen.addstr(0, 0, header.ljust(w), curses.color_pair(6))
        half = w // 2
        for i, x, width in ((0, 0, half), (1, half, w - half)):
            self.draw_panel(self.panels[i], x, width, h - 3, i == self.active)
        self.screen.addstr(h - 2, 0, (" " + self.message)[:w - 1].ljust(w - 1), curses.color_pair(5))
        x = 0
        cell = max(w // len(KEYS), 6)
        for key, label in KEYS:
            if x + cell > w:
                break
            self.screen.addstr(h - 1, x, key, curses.color_pair(5) | curses.A_BOLD)
            self.screen.addstr(h - 1, x + len(key), label[:cell - len(key)].ljust(cell - len(key)),
                               curses.color_pair(6))
            x += cell
        self.screen.refresh()

    def ask(self, prompt):
        h, w = self.screen.getmaxyx()
        curses.curs_set(1)
        text = ""
        while True:
            line = f" {prompt}: {text}"
            self.screen.addstr(h - 2, 0, line[:w - 1].ljust(w - 1), curses.color_pair(4))
            self.screen.move(h - 2, min(len(line), w - 2))
            ch = self.screen.get_wch()
            if ch in ("\n", "\r", curses.KEY_ENTER):
                break
            if ch == "\x1b":
                text = None
                break
            if ch in (curses.KEY_BACKSPACE, "\x7f", "\b"):
                text = text[:-1]
            elif isinstance(ch, str) and ch.isprintable():
                text += ch
        curses.curs_set(0)
        return text.strip() if text else None

    def view(self, title, text):
        lines = text.splitlines() or ["(файл пуст)"]
        top = 0
        while True:
            self.screen.erase()
            h, w = self.screen.getmaxyx()
            self.screen.addstr(0, 0, f" Просмотр: {title}   (стрелки — прокрутка, q — закрыть) ".ljust(w),
                               curses.color_pair(6))
            for i, line in enumerate(lines[top:top + h - 1]):
                self.screen.addstr(1 + i, 0, line[:w - 1])
            self.screen.refresh()
            ch = self.screen.get_wch()
            if ch == curses.KEY_DOWN and top < len(lines) - 1:
                top += 1
            elif ch == curses.KEY_UP and top > 0:
                top -= 1
            elif ch not in (curses.KEY_DOWN, curses.KEY_UP):
                return

    def act(self, key):
        item = self.panel.current()
        fm = self.panel.fm
        name = item[0] if item else None
        is_dir = item[1] if item else False
        if key in (curses.KEY_UP,):
            self.panel.index = max(self.panel.index - 1, 0)
        elif key in (curses.KEY_DOWN,):
            self.panel.index = min(self.panel.index + 1, len(self.panel.items) - 1)
        elif key == "\t":
            self.active = 1 - self.active
        elif key in ("\n", "\r", curses.KEY_ENTER):
            if name == "..":
                self.message = "Папка: " + fm.leave()
            elif is_dir:
                self.message = "Папка: " + fm.enter(name)
                self.panel.index = 0
            elif name:
                self.view(name, fm.read_file(name))
        elif key in (curses.KEY_BACKSPACE, "\x7f", "\b"):
            self.message = "Папка: " + fm.leave()
        elif key in (curses.KEY_F1, "h"):
            self.view("Справка", HELP_TEXT)
        elif key in (curses.KEY_F3, "v") and name and not is_dir:
            self.view(name, fm.read_file(name))
        elif key in (curses.KEY_F4, "e") and name and not is_dir:
            text = self.ask(f"Дописать строку в {name}")
            if text is not None:
                self.message = f"Дописано {fm.write_file(name, text + chr(10), append=True)} байт в {name}"
        elif key in (curses.KEY_F5, "c") and name and not is_dir:
            self.message = "Скопировано: " + fm.copy_file(name, self.other.fm.where())
        elif key in (curses.KEY_F6, "m") and name and not is_dir:
            self.message = "Перемещено: " + fm.move_file(name, self.other.fm.where())
        elif key in (curses.KEY_F2, "r") and name and not is_dir:
            new = self.ask(f"Новое имя для {name}")
            if new:
                self.message = "Переименовано: " + fm.rename_file(name, new)
        elif key in (curses.KEY_F7, "n"):
            new = self.ask("Имя новой папки")
            if new:
                self.message = "Создана папка " + fm.make_dir(new)
        elif key in (curses.KEY_F9, "f"):
            new = self.ask("Имя нового файла")
            if new:
                self.message = "Создан файл " + fm.make_file(new)
        elif key in (curses.KEY_F8, "d") and name and name != "..":
            answer = self.ask(f"Удалить {'папку' if is_dir else 'файл'} «{name}»? (y/n)")
            if answer and answer.lower() in ("y", "д", "да", "yes"):
                self.message = "Удалено: " + (fm.remove_dir(name) if is_dir else fm.remove_file(name))
        elif key in (curses.KEY_F10, "q"):
            return False
        return True

    def run(self):
        while True:
            for p in self.panels:
                p.refresh()
            self.draw()
            key = self.screen.get_wch()
            try:
                if not self.act(key):
                    return
            except FMError as e:
                self.message = f"Ошибка: {e}"
            except OSError as e:
                self.message = f"Ошибка ОС: {e.strerror}"


def run_tui(fm, user, settings):
    try:
        curses.wrapper(lambda screen: App(screen, fm, user, settings).run())
    except curses.error as e:
        print("Окно терминала слишком маленькое или терминал не поддерживает curses:", e)
