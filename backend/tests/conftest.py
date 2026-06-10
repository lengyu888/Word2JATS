import getpass
import re
from pathlib import Path


def pytest_configure(config):
    """Keep pytest temp directories separate across Windows user accounts."""
    username = re.sub(r"[^A-Za-z0-9_.-]+", "-", getpass.getuser()) or "user"
    config.option.basetemp = str(Path(__file__).resolve().parents[2] / f".pytest-tmp-{username}")
