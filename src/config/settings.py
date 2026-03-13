from pathlib import Path
from enum import Enum

ROOT = Path(__file__).parent.parent # src/ directory
TEMP_FOLDER = "tmp"

class Node_Type(Enum):
  NONE = 0
  GITHUB = 1
  LOCAL = 2