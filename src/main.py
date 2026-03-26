import os
from utils import TreeNode
from interface import UserInterface
from config.settings import *

# Mock data
root_data = TreeNode("Helios", "root", [
    TreeNode("HeliosCore", "3", location="https://github.com/helios-data/helios-core", type=Node_Type['GITHUB'], hash="84e7aad25fccd25d4b0e13a7d559550722f34fb2"),
    # TreeNode("FALCON", "1", [
    #     TreeNode("Telemetry", "2", location="https://github.com/UBC-Rocket/ground-station", type=Node_Type['GITHUB']),
    # ]),
    TreeNode("Services", "6", [
      TreeNode("Livestreaming", "7", location="https://github.com/helios-data/helios-livestreaming", type=Node_Type['GITHUB'], hash="a2202d371479e17ea44c2acb5d7390a145c8528c")
    ]),
])

# Prune leftover stopped containers from build step
os.environ["DOCKER_BUILDKIT"] = "1"

os.makedirs(ROOT / TEMP_FOLDER, exist_ok=True)

if __name__ == "__main__":
  UserInterface(root_data)