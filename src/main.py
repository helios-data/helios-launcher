import os
from utils import TreeNode
from interface import UserInterface
from config.settings import *

# Mock data
root_data = TreeNode("Helios", "root", [
    TreeNode(HELIOS_CORE_CONTAINER, "main", location="https://github.com/helios-data/helios-core", type=Node_Type['GITHUB'], hash="9bbb69055a106216eb26b84d7ee7d70e26828d64"),
    TreeNode("FALCON", "1", [
        TreeNode("Telemetry", "2", location="https://github.com/UBC-Rocket/helios-cots-telemetry", type=Node_Type['GITHUB'], hash="25c6d05ea62b5d301a8dbdf31cdd60b21e42b9d3"),
    ]),
    TreeNode("Services", "6", [
      TreeNode("Livestreaming", "7", location="https://github.com/helios-data/helios-livestreaming", type=Node_Type['GITHUB'], hash="46daf4ebebc70dea5e4560999428f99b271f2659")
    ]),
])

# Prune leftover stopped containers from build step
os.environ["DOCKER_BUILDKIT"] = "1"

os.makedirs(ROOT / TEMP_FOLDER, exist_ok=True)

if __name__ == "__main__":
  UserInterface(root_data)