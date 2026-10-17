"""The small persistent UI scale preference."""

from configparser import ConfigParser, Error
from pathlib import Path

SCALES = (1.0, 1.25, 1.5, 1.75, 2.0)


def load_scale(path: Path) -> float:
    config = ConfigParser()
    try:
        config.read(path, encoding="utf-8")
        value = config.getfloat("ui", "scale")
    except (OSError, Error, ValueError):
        return 1.0
    return value if value in SCALES else 1.0


def save_scale(path: Path, value: float) -> None:
    if value not in SCALES:
        raise ValueError("Unsupported UI scale")
    path.parent.mkdir(parents=True, exist_ok=True)
    config = ConfigParser()
    config["ui"] = {"scale": str(value)}
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            config.write(handle)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
