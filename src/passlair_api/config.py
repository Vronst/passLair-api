import os
from pathlib import Path


config_mapping = {
    "SECRET_KEY": os.environ["SECRET_KEY"],
    "SQLITE_PATH": Path(__file__).resolve().parent
    / "app.db",  # Could be changed to some safer file (docker override)
}
