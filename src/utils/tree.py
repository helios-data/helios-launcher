import os
import sys
from pathlib import Path
from google.protobuf import json_format
import generated.config.component_pb2 as component

ROOT = os.path.dirname(sys.executable)
TREE_FILE_NAME = "component_tree.json"

class TreeNode:
  def __init__(self, name, node_id, children=None):
    self.name = name
    self.id = node_id
    self.children = children or []
    self.is_visible = True
    self.location = None
    self.hash = None
    self.type = None # github vs. local
    self.image_exists = None # None, False, True

class TreeUtils:
  def __init__(self):
    pass

  def generate_component_tree(self, root_node: TreeNode) -> Path:
    tree_location = Path(ROOT) / TREE_FILE_NAME

    def build_proto_node(node: TreeNode) -> component.BaseComponent:
      base = component.BaseComponent()
      base.name = node.name

      if not node.children: # Leaf
        leaf = component.Component()
        leaf.path = node.location or ""
        leaf.tag = node.hash or "latest"
        leaf.id = node.id
        base.leaf.CopyFrom(leaf)
      else: # Branch
        branch = component.ComponentGroup()
        for child in node.children:
          # Recursively build child BaseComponents
          proto_child = build_proto_node(child)
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