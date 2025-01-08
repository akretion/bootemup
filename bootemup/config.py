# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import os
import sys
import tomllib
import pathlib

config_file = pathlib.Path(os.getenv("CONFIG_FILE", "config.toml"))

try:
    with config_file.open("rb") as f:
        config = tomllib.load(f)
except Exception as e:
    print(f"Error while loading config file: {e}")
    sys.exit(1)
