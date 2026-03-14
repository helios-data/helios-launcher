import docker
from .github import GithubUtils
from .tree import TreeNode
from config import *

# Set to False for debugging build issues, True for production use to save space
REMOVE_BUILD_INTERMEDIATES = True 

class DockerUtils:

  def __init__(self):
    self.client = docker.from_env()
    self.github_utils = GithubUtils()

    if not self.is_docker_running():
      raise RuntimeError("Docker is not running. Please start Docker and try again.")

  def check_image_exists(self, node: TreeNode) -> bool:
    list = self.client.images.list(filters={
      "reference": node.name,
      #"tag":"Helios"
      })
    
    # Always build the image if the hash = "latest" or anything else
    expected = {"location": node.location, "type": node.type, "hash": node.hash}

    for image in list:
      match = all(
        image.labels.get(k) == str(v)
        for k, v in expected.items()
      )

      if match:
        return True
      
    return False

  def build_image(self, node: TreeNode) -> None:

    # Clone the repo first if it is of type Github
    if node.type == Node_Type['GITHUB']:
      path = ROOT / TEMP_FOLDER / node.name
      hash = self.github_utils.clone_repo(
        target_dir=ROOT / TEMP_FOLDER / node.name, 
        repo_url=node.location, 
        hash=node.hash
      )
    else:
      path = node.location
      hash = None

    self.client.images.build(
      path=path, 
      tag="helios",
      labels={
        "type": node.type,
        "location": node.location,
        "hash": hash,
      },
      rm=REMOVE_BUILD_INTERMEDIATES
    )
    pass

  def start_container(self) -> None:
    pass

  def is_docker_running(self) -> bool:
    try:
      return self.client.ping()
    except Exception:
      return False

# Generalize the process to docker functions here to be called in the imgui process