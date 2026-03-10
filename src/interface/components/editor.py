from utils import TreeNode
from imgui_bundle import imgui

from utils.tree import NODE_TYPES

class EditorComponent:

  def __init__(self) -> None:
    pass

  def render(self, editing_node: TreeNode | None, height: float = 0, on_close_callback=None) -> None:
    if not editing_node:
      return
    
    imgui.set_cursor_pos_y(imgui.get_window_height() - height) # Pin to bottom

    imgui.begin_child("EditPanel", (0, height))
    
    imgui.text_colored((0.3, 0.7, 1.0, 1.0), f"EDITING: {editing_node.name}")
    imgui.spacing()
    imgui.separator()
    imgui.spacing()

    #   def __init__(self, name, node_id, children=None, location=None, hash=None, type=None):
    # self.name = name
    # self.id = node_id
    # self.children = children or []
    # self.location = location
    # self.hash = hash
    # self.type = type # github vs. local
    # self.image_exists = None # None, False, True


    # Input fields for TreeNode attributes
    # Note: imgui.input_text returns (modified, new_value)
    changed, new_name = imgui.input_text("Name", editing_node.name, 128)
    if changed:
      editing_node.name = new_name
        
    changed_type, new_type = imgui.combo("Node Type", editing_node.type, NODE_TYPES)
    if changed_type:
      editing_node.type = new_type

    changed_location, new_location = imgui.input_text("Location", editing_node.location, 128)
    if changed_location:
      editing_node.location = new_location

    changed_hash, new_hash = imgui.input_text("Hash", editing_node.hash, 128)
    if changed_hash:
      editing_node.hash = new_hash


    if imgui.button("Close", (-1, 0)):
      if on_close_callback:
        on_close_callback()
        
    imgui.end_child()