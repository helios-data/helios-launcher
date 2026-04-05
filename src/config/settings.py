from pathlib import Path
from enum import Enum

HELIOS_CORE_CONTAINER = "HeliosCore"

ROOT = Path(__file__).parent.parent # src/ directory
TEMP_FOLDER = "tmp"
ROCKET_CONFIG_FOLDER = "config/rockets"

class Node_Type(Enum):
  NONE = 0
  GITHUB = 1
  LOCAL = 2