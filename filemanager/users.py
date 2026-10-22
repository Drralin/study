import hashlib
import hmac
import json
import re
import secrets
from pathlib import Path

from .errors import FMError

NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁё0-9_]{3,20}$")
ITERATIONS = 200_000


class UserStore:
    def __init__(self, path, workspace):
        self.path = Path(path)
        self.homes = Path(workspace) / "home"
        self.users = {}
        if self.path.exists():
            self.users = json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.users, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _hash(password, salt):
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), ITERATIONS).hex()

    def home(self, name):
        return self.homes / name

    def register(self, name, password):
        if not NAME_RE.match(name):
            raise FMError("имя: 3-20 символов, буквы, цифры и _")
        if name in self.users:
            raise FMError(f"пользователь «{name}» уже существует")
        if len(password) < 4:
            raise FMError("пароль должен быть не короче 4 символов")
        salt = secrets.token_hex(16)
        self.users[name] = {"salt": salt, "hash": self._hash(password, salt)}
        self._save()
        self.home(name).mkdir(parents=True, exist_ok=True)
        return self.home(name)

    def login(self, name, password):
        user = self.users.get(name)
        if not user or not hmac.compare_digest(user["hash"], self._hash(password, user["salt"])):
            raise FMError("неверное имя пользователя или пароль")
        self.home(name).mkdir(parents=True, exist_ok=True)
        return self.home(name)
