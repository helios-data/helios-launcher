import os
from utils import TreeNode
from interface import UserInterface
from config.settings import *

# Mock data
root_data = TreeNode("Helios", "root", [
    TreeNode("HeliosCore", "3", location="https://github.com/helios-data/helios-core", type=Node_Type['GITHUB']),
    TreeNode("FALCON", "1", [
        TreeNode("Telemetry", "2", location="https://github.com/UBC-Rocket/ground-station", type=Node_Type['GITHUB']),
    ]),
    TreeNode("Services", "6", [
      TreeNode("Livestreaming", "7", location="https://github.com/helios-data/helios-livestreaming", type=Node_Type['GITHUB'])
    ]),
])

# Prune leftover stopped containers from build step
os.environ["DOCKER_BUILDKIT"] = "1"

os.makedirs(ROOT / TEMP_FOLDER, exist_ok=True)

if __name__ == "__main__":
  UserInterface(root_data)