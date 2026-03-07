import docker
import docker.errors
import os
import sys
import time
import threading
from pathlib import Path

from google.protobuf import json_format
import generated.config.component_pb2 as component

# Prune leftover stopped containers from build step
os.environ["DOCKER_BUILDKIT"] = "1"

LOCAL = os.path.dirname(sys.executable)

class DockerUtils:

  def check_image_exists(self) -> None:
    pass

  def build_image(self, repo_url: str) -> None:
    pass

  def start_container(self) -> None:
    pass

# Generalize the process to docker functions here to be called in the imgui process
