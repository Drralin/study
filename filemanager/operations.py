import shutil
import zipfile
from pathlib import Path

from .errors import FMError
from .sandbox import Sandbox


class FileManager:
    def __init__(self, root, quota_bytes=0, encoding="utf-8"):
        self.box = Sandbox(root)
        self.quota = quota_bytes
        self.encoding = encoding

    def _existing(self, name, kind):
        path = self.box.resolve(name)
        if kind == "dir" and not path.is_dir():
            raise FMError(f"папка «{name}» не найдена")
        if kind == "file" and not path.is_file():
            raise FMError(f"файл «{name}» не найден")
        return path

    def _new(self, name):
        path = self.box.resolve(name)
        if path == self.box.root:
            raise FMError("недопустимое имя")
        if path.exists():
            raise FMError(f"«{name}» уже существует")
        if not path.parent.is_dir():
            raise FMError("родительская папка не существует")
        return path

    def _target_in_dir(self, src, dest_dir_name):
        dest_dir = self._existing(dest_dir_name, "dir")
        dest = dest_dir / src.name
        if dest.exists():
            raise FMError(f"в папке «{dest_dir_name}» уже есть «{src.name}»")
        return dest

    def usage(self):
        return sum(p.stat().st_size for p in self.box.root.rglob("*") if p.is_file())

    def _check_quota(self, extra):
        if self.quota and self.usage() + extra > self.quota:
            raise FMError(f"превышена квота: занято {fmt_size(self.usage())} из {fmt_size(self.quota)}")

    def where(self):
        return self.box.show(self.box.cwd)

    def listing(self, name=None):
        path = self._existing(name, "dir") if name else self.box.cwd
        items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        return [(p.name, p.is_dir(), 0 if p.is_dir() else p.stat().st_size) for p in items]

    def make_dir(self, name):
        path = self._new(name)
        path.mkdir()
        return self.box.show(path)

    def remove_dir(self, name):
        path = self._existing(name, "dir")
        if path == self.box.root:
            raise FMError("нельзя удалить корень рабочей папки")
        if path == self.box.cwd or path in self.box.cwd.parents:
            raise FMError("нельзя удалить папку, в которой вы находитесь")
        shutil.rmtree(path)
        return self.box.show(path)

    def enter(self, name):
        return self.box.enter(name)

    def leave(self):
        return self.box.leave()

    def make_file(self, name):
        path = self._new(name)
        path.touch()
        return self.box.show(path)

    def write_file(self, name, text, append=False):
        path = self._existing(name, "file")
        data = text.encode(self.encoding)
        self._check_quota(len(data) - (0 if append else path.stat().st_size))
        with open(path, "ab" if append else "wb") as f:
            f.write(data)
        return len(data)

    def read_file(self, name):
        path = self._existing(name, "file")
        try:
            return path.read_text(encoding=self.encoding)
        except UnicodeDecodeError:
            raise FMError(f"«{name}» не является текстовым файлом в кодировке {self.encoding}")

    def remove_file(self, name):
        path = self._existing(name, "file")
        path.unlink()
        return self.box.show(path)

    def copy_file(self, name, dest_dir):
        src = self._existing(name, "file")
        dest = self._target_in_dir(src, dest_dir)
        self._check_quota(src.stat().st_size)
        shutil.copy2(src, dest)
        return self.box.show(dest)

    def move_file(self, name, dest_dir):
        src = self._existing(name, "file")
        dest = self._target_in_dir(src, dest_dir)
        shutil.move(str(src), str(dest))
        return self.box.show(dest)

    def rename_file(self, name, new_name):
        src = self._existing(name, "file")
        if "/" in new_name or "\\" in new_name or new_name in ("", ".", ".."):
            raise FMError("новое имя не должно содержать путь")
        dest = src.with_name(new_name)
        if dest.exists():
            raise FMError(f"«{new_name}» уже существует")
        src.rename(dest)
        return self.box.show(dest)

    def pack(self, name, archive_name):
        src = self.box.resolve(name)
        if not src.exists():
            raise FMError(f"«{name}» не найден")
        if not archive_name.endswith(".zip"):
            archive_name += ".zip"
        archive = self._new(archive_name)
        files = [src] if src.is_file() else [p for p in src.rglob("*") if p.is_file()]
        self._check_quota(sum(p.stat().st_size for p in files))
        base = src.parent
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            if src.is_dir():
                zf.write(src, src.relative_to(base).as_posix() + "/")
            for p in files:
                zf.write(p, p.relative_to(base).as_posix())
        return self.box.show(archive), len(files)

    def unpack(self, archive_name, dest_dir=None):
        archive = self._existing(archive_name, "file")
        dest = self._existing(dest_dir, "dir") if dest_dir else self.box.cwd
        try:
            zf = zipfile.ZipFile(archive)
        except zipfile.BadZipFile:
            raise FMError(f"«{archive_name}» не является zip-архивом")
        with zf:
            total = 0
            for info in zf.infolist():
                target = (dest / info.filename).resolve()
                if target != self.box.root and self.box.root not in target.parents:
                    raise FMError(f"архив содержит опасный путь: {info.filename}")
                if target.exists() and not info.is_dir():
                    raise FMError(f"файл уже существует: {self.box.show(target)}")
                total += info.file_size
            self._check_quota(total)
            zf.extractall(dest)
            return self.box.show(dest), len([i for i in zf.infolist() if not i.is_dir()])

    def quota_info(self):
        used = self.usage()
        return used, self.quota


def fmt_size(size):
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if size < 1024 or unit == "ГБ":
            return f"{size:.0f} {unit}" if unit == "Б" else f"{size:.1f} {unit}"
        size /= 1024
