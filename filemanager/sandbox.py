from pathlib import Path, PurePosixPath

from .errors import FMError


class Sandbox:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.cwd = self.root

    def resolve(self, name, base=None):
        if not name:
            raise FMError("не указано имя")
        name = name.replace("\\", "/")
        start = self.root if name.startswith("/") else (base or self.cwd)
        target = (start / name.lstrip("/")).resolve()
        if target != self.root and self.root not in target.parents:
            raise FMError("выход за пределы рабочей папки запрещён")
        return target

    def show(self, path):
        rel = Path(path).resolve().relative_to(self.root)
        return str(PurePosixPath("/") / PurePosixPath(*rel.parts))

    def enter(self, name):
        target = self.resolve(name)
        if not target.is_dir():
            raise FMError(f"папка «{name}» не найдена")
        self.cwd = target
        return self.show(target)

    def leave(self):
        if self.cwd == self.root:
            raise FMError("вы уже в корне рабочей папки")
        self.cwd = self.cwd.parent
        return self.show(self.cwd)
