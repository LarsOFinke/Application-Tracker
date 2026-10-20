"""Locate the wheel matching the version in pyproject.toml."""

import tomllib
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    with (root / "pyproject.toml").open("rb") as project_file:
        version = tomllib.load(project_file)["project"]["version"]
    wheels = list((root / "dist" / "wheels").glob(f"application_tracker-{version}-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Expected one application-tracker {version} wheel; found {wheels}")
    print(wheels[0])


if __name__ == "__main__":
    main()
