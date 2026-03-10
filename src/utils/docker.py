import docker

REMOVE_BUILD_INTERMEDIATES = True # Set to False for debugging build issues, True for production use to save space

class DockerUtils:

  def __init__(self):
    self.client = docker.from_env()

    if not self.is_docker_running():
      raise RuntimeError("Docker is not running. Please start Docker and try again.")

  def check_image_exists(self) -> None:
    pass

  def build_image(self, repo_url: str) -> None:
    # Save the repo link, has, and has type into the lables dict
    self.client.images.build(path=repo_url, tag=repo_url.split('/')[-1].replace('.git', ''), rm=REMOVE_BUILD_INTERMEDIATES)
    pass

  def start_container(self) -> None:
    pass

  def is_docker_running(self) -> bool:
    try:
      return self.client.ping()
    except Exception:
      return False

# Generalize the process to docker functions here to be called in the imgui process