from pathlib import Path
from enum import Enum
import re

HELIOS_CORE_CONTAINER = "HeliosCore"


def sanitize_image_name(name: str) -> str:
  """Docker image tags can't contain spaces. Lowercase and turn any
  whitespace into underscores (e.g. "Mission Control" -> "mission_control")."""
  return re.sub(r"\s+", "_", name.strip().lower())

def sanitize_node_name(name: str) -> str:
  """Node names can't contain spaces. Turn any whitespace into underscores
  (e.g. "Mission Control" -> "Mission_Control"). Case is preserved so the
  display name stays readable, unlike sanitize_image_name."""
  if name is None:
    return name
  return re.sub(r"\s+", "_", name.strip())

ROOT = Path(__file__).parent.parent # repo root
TEMP_FOLDER = "tmp"
# Per-config runtime selections (device/port/volume/flag bindings) are cached
# here so they survive a launcher restart.
SETTINGS_FOLDER = "tmp/settings"
ROCKET_CONFIG_FOLDER = "config/rockets"

# Per-repo pydantic config files and the last generated last_run.json live
# here, keyed by repo name. Unlike tmp/, this survives tmp cleanup so we always
# have the config that matches each built image.
CONFIG_CACHE_FOLDER = "cache"
# Where the pydantic config lives inside a cloned repo, relative to its root.
REPO_CONFIG_RELPATH = "src/helios_pydantic_config.py"
# File names inside cache/<repo_name>/
CONFIG_PY_NAME = "helios_pydantic_config.py"
LAST_RUN_NAME = "last_run.json"
# Where last_run.json is bind-mounted inside each component's container. The
# component's SDK reads PYDANTIC_CONFIG_PATH to find it.
CONTAINER_CONFIG_PATH = "/app/last_run.json"
PYDANTIC_CONFIG_ENV = "PYDANTIC_CONFIG_PATH"

class Node_Type(Enum):
  NONE = 0
  GITHUB = 1
  LOCAL = 2