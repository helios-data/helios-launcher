import docker
import os
import sys

# Prune leftover stopped containers from build step
os.environ["DOCKER_BUILDKIT"] = "1"

LOCAL = os.path.dirname(sys.executable)
REMOVE_BUILD_INTERMEDIATES = True # Set to False for debugging build issues, True for production use to save space

class DockerUtils:

  def __init__(self):
    self.client = docker.from_env()

  def check_image_exists(self) -> None:
    pass

  def build_image(self, repo_url: str) -> None:
    # Save the repo link, has, and has type into the lables dict
    self.client.images.build(path=repo_url, tag=repo_url.split('/')[-1].replace('.git', ''), rm=REMOVE_BUILD_INTERMEDIATES)
    pass

  def start_container(self) -> None:
    pass

# Generalize the process to docker functions here to be called in the imgui process