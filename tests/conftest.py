"""Fake settings for every test. Tests never read the real `.env` or the shell's keys.

This runs before any test module is imported, so even code that reads settings at import
time sees only the fakes below.
"""

import os

from app.config import Settings, get_settings

FAKE_ENV = {
    "SUPABASE_URL": "https://fake-project.supabase.co",
    "SUPABASE_SECRET_KEY": "sb_secret_fake",
    "HOME_ID": "11111111-1111-1111-1111-111111111111",
}

for _name in Settings.model_fields:
    os.environ.pop(_name.upper(), None)
os.environ.update(FAKE_ENV)
Settings.model_config["env_file"] = None
get_settings.cache_clear()
