import os
from utils import TreeNode
from interface import UserInterface
from config.settings import *

# Mock data
root_data = TreeNode("Helios", "root", [
    TreeNode("Assets", "1", [
        TreeNode("Textures", "2"),
        TreeNode("Models", "3", [TreeNode("Player.fbx", "4"), TreeNode("Enemy.fbx", "5")]),
    ]),
    TreeNode("Scripts", "6", [TreeNode("Main.py", "7")]),
])

# Prune leftover stopped containers from build step
os.environ["DOCKER_BUILDKIT"] = "1"

os.makedirs(ROOT / TEMP_FOLDER, exist_ok=True)

if __name__ == "__main__":
  UserInterface(root_data)