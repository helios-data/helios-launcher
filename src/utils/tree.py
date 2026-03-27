from pathlib import Path
from google.protobuf import json_format
import generated.config.component_pb2 as component
import json

from config.settings import *

TREE_FILE_NAME = "component_tree.json"

class TreeNode:
  def __init__(self, name, node_id, children=None, location: str = "", hash: str = "", type: Node_Type = Node_Type['NONE'], volumes: dict = {}, ports: dict = {}):
    self.name: str = name
    self.id: str = node_id
    self.children: list = children or []
    self.location: str = location
    self.hash: str = hash
    self.type: Node_Type = type
    self.image_exists: bool | None = None # None, False, True
    self.volumes: dict = volumes
    self.ports: dict = ports
    self.warning: bool = False

  def to_dict(self):
    return {
      "name": self.name,
      "id": self.id,
      "location": self.location,
      "hash": self.hash,
      "type": self.type.value,
      "image_exists": self.image_exists,
      "volumes": self.volumes,
      "ports": self.ports,
      "children": [child.to_dict() for child in self.children]
    }

class TreeUtils:
  def __init__(self):
    pass

  def generate_component_tree(self, root_node: TreeNode) -> Path:
    tree_location = self.get_tree_path()

    def build_proto_node(node: TreeNode) -> component.BaseComponent | None:
      base = component.BaseComponent()
      base.name = node.name

      if not node.children: # Leaf

        # We don't want to pass HeliosCore to Helios, since it shouldn't build itself
        if node.name == HELIOS_CORE_CONTAINER: return None

        leaf = component.Component()
        leaf.path = node.location or ""
        leaf.tag = node.hash or "latest"
        leaf.id = node.id

        leaf.location = node.location or ""
        leaf.hash = node.hash or ""
        leaf.type = node.type.name  # or .value if you want the int as a string

        for vol in node.volumes:  # list of dicts — iterate directly
            v = component.Volume()
            v.source = vol.get("source", "")
            v.target = vol.get("target", "")
            v.mode = vol.get("mode", "")
            leaf.volumes.append(v)

        for port in node.ports.keys():  # dict — use .values()
            p = component.Port()
            p.target = port
            p.source = node.ports[port]
            # p.type = port.get("type", "")
            # p.source = port.get("source", "")
            # p.target = port.get("target", "")
            # p.read_only = port.get("read_only", "")
            leaf.ports.append(p)

        base.leaf.CopyFrom(leaf)
      else: # Branch
        branch = component.ComponentGroup()
        for child in node.children:
          # Recursively build child BaseComponents
          proto_child = build_proto_node(child)
          if not proto_child == None:
            branch.children.append(proto_child)
        base.branch.CopyFrom(branch)
      
      return base

    root_proto_node = build_proto_node(root_node)

    component_tree = component.ComponentTree()
    component_tree.root.CopyFrom(root_proto_node)
    component_tree.version = "1.0.0"

    with open(tree_location, "w") as f:
      json_string = json_format.MessageToJson(component_tree, indent=2)
      f.write(json_string)

    return tree_location

  def save_tree_as_dict(self, root: TreeNode, file_name: str = "configuration.json"):
    with open(ROOT / TEMP_FOLDER / file_name, "w") as f:
      data = root.to_dict()
      json.dump(data, f, indent=2)
    
    pass

  def load_tree_from_dict(self, file_name: str = "configuration.json") -> TreeNode:
    file_path = Path(ROOT) / TEMP_FOLDER / file_name
        
    if not file_path.exists():
      raise FileNotFoundError(f"No tree configuration found at {file_path}")

    with open(file_path, "r") as f:
      data = json.load(f)
    
    return self._dict_to_node(data)

  def _dict_to_node(self, data: dict) -> TreeNode:
    """Recursively converts a dictionary back into a TreeNode object."""
    children_data = data.pop("children", [])
    
    image_exists = data.pop("image_exists", None)

    node = TreeNode(
      name=data.get("name"),
      node_id=data.get("id"),
      location=data.get("location", ""),
      hash=data.get("hash", ""),
      type=Node_Type(data.get("type", 0)),
      volumes=data.pop("volumes", {}),
      ports=data.pop("ports", {})
    )

    node.image_exists = image_exists

    for child_dict in children_data:
      node.children.append(self._dict_to_node(child_dict))

    return node
  
  def get_tree_path(self) -> Path:
    return Path(ROOT) / TEMP_FOLDER / TREE_FILE_NAME