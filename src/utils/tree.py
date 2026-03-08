from google.protobuf import json_format
import generated.config.component_pb2 as component

class TreeUtils:
  def generate_component_tree(self) -> tuple[component.ComponentTree, Path]:
  # Example of generating a component tree using protobuf
  tree_location = Path("./component_tree.json")

  leaf_component = component.BaseComponent()
  leaf_component.name = "RocketDecoder"
  leaf = component.Component()
  leaf.path = "/components/rocketdecoder"
  leaf.tag = "rocketdecoder:v1.0.0"
  leaf.id = "RD1"
  leaf_component.leaf.CopyFrom(leaf)

  branch_component = component.ComponentGroup()
  branch_component.children.extend([leaf_component])

  root = component.BaseComponent()
  root.name = "FALCON"
  root.branch.CopyFrom(branch_component)

  component_tree = component.ComponentTree()
  component_tree.root.CopyFrom(root)
  component_tree.version = "1.0.0"

  with open(tree_location, "w") as f:
    f.write(json_format.MessageToJson(component_tree))

  return component_tree, tree_location