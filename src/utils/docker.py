import docker
from docker.errors import DockerException
import threading
from .github import GithubUtils
from .tree import TreeNode
from config import *
import re
import json

REMOVE_BUILD_INTERMEDIATES = True 

class DockerUtils:

  def __init__(self):
    self.client = self._get_docker_client()
    self.github_utils = GithubUtils()

    self.build_logs: dict[str, list[str]] = {}   # node.id → list of log lines
    self.build_status: dict[str, str] = {}        # node.id → "building" | "done" | "error"
    self.build_step: dict[str, str] = {}  # ← node.id → "5/15"

  def check_image_exists(self, node: TreeNode) -> tuple[bool, dict]:
    filters = {
      "label": [
        f"location={node.location}",
        f"type={node.type.value}",
        f"hash={node.hash}"
      ]
    }

    images = self.client.images.list(name=node.name.lower(), filters=filters)
    
    if not images:
      return False, {"ports": [], "volumes": []}

    found_labels = images[0].labels
    
    ports_raw = found_labels.get("ports", "[]")
    volumes_raw = found_labels.get("volumes", "[]")

    ports = json.loads(ports_raw)
    volumes = json.loads(volumes_raw)

    if not ports == [] or not volumes == []:
      node.warning = True

    return True, {
      "ports": ports,
      "volumes": volumes
    }

  def build_image(self, node: TreeNode) -> None:
    """ Starts a background thread to build the image, streaming logs into self.build_logs """
    self.build_logs[node.name] = []
    self.build_status[node.name] = "building"
    thread = threading.Thread(target=self._build_worker, args=(node,), daemon=True)
    thread.start()

  def _build_worker(self, node: TreeNode) -> None:
    try:
      if node.type == Node_Type['GITHUB']:
        path = ROOT / TEMP_FOLDER / node.name
        hash = self.github_utils.clone_repo(
            target_dir=path,
            repo_url=node.location,
            hash=node.hash
        )
      else:
        path = Path(node.location)
        hash = None

      self.build_logs[node.name].append(f"Building docker image for {node.name}...\n")

      # Get the required configuration ports/volumes
      with open(path / 'config.json', 'r') as file:
        data = json.load(file)

        node.ports = {port: None for port in data.get('ports', [])}
        node.volumes = data.get('volumes', [])

        if not node.ports == [] or not node.volumes == []:
          node.warning = True

      # Build the docker image
      build_stream = self.client.api.build(
        path=str(path),
        tag=node.name.lower(),
        labels={
          "type": str(node.type.value),
          "location": node.location,
          "hash": str(hash),
          "ports": json.dumps(list(node.ports.keys())), # convert the dict_keys to str
          "volumes": json.dumps(list(node.volumes)),
        },
        rm=REMOVE_BUILD_INTERMEDIATES,
        decode=True  # ← auto-decodes each chunk from JSON
      )

      STEP_RE = re.compile(r"Step (\d+/\d+)")

      # Parse the build logs and save into the logs dict
      for chunk in build_stream:
        if "stream" in chunk:
          match = STEP_RE.search(chunk["stream"])
          if match:
            self.build_step[node.name] = match.group(1)
          else:
            line = chunk["stream"].strip()
            if line:
                self.build_logs[node.name].append(line + "\n")
        elif "errorDetail" in chunk:
          detail = chunk["errorDetail"].get("message", "")
          self.build_logs[node.name].append(f"ERROR: {detail}\n")
          raise Exception(detail)
        elif "error" in chunk:
          raise Exception(chunk["error"])
        elif "status" in chunk:
          self.build_logs[node.name].append(chunk["status"] + "\n")
        elif "aux" in chunk:
          self.build_logs[node.name].append(f"Image ID: {chunk['aux'].get('ID', '?')}\n")

      self.build_logs[node.name].append(f"Finished building {node.name}.\n")
      self.build_status[node.name] = "done"

    except Exception as e:
      self.build_logs[node.name].append(f"ERROR: {e}\n")
      self.build_status[node.name] = "error"
      print(e)

  def is_build_running(self, node: TreeNode) -> bool:
    return self.build_status.get(node.name) == "building"

  def get_logs(self, node: TreeNode) -> list[str]:
    return self.build_logs.get(node.name, [])

  def start_container(self) -> None:
    pass

  def _get_docker_client(self) -> docker.DockerClient:
    try:
      client = docker.from_env()
      client.ping()
      return client
    except DockerException:
      raise RuntimeError("Docker is not running. Please start Docker and try again.")