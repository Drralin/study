import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SETTINGS = Path(__file__).resolve().parent.parent / "settings.json"


@dataclass
class Settings:
    workspace: Path
    users_file: Path
    quota_bytes: int
    encoding: str


def load_settings(path=DEFAULT_SETTINGS):
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    workspace = Path(raw["workspace"]).expanduser()
    if not workspace.is_absolute():
        workspace = path.parent / workspace
    users_file = Path(raw.get("users_file", "users.json")).expanduser()
    if not users_file.is_absolute():
        users_file = workspace / users_file
    quota_mb = float(raw.get("quota_mb", 0))
    return Settings(
        workspace=workspace.resolve(),
        users_file=users_file,
        quota_bytes=int(quota_mb * 1024 * 1024),
        encoding=raw.get("encoding", "utf-8"),
    )
