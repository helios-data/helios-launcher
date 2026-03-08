from utils import TreeNode
from imgui_bundle import imgui

class EditorComponent:

  def __init__(self) -> None:
    pass

  def render(self, editing_node: TreeNode | None, height: float = 0):
    if not editing_node:
      return
    
    imgui.set_cursor_pos_y(imgui.get_window_height() - height) # Pin to bottom

    imgui.begin_child("EditPanel", (0, height))
    
    imgui.text_colored((0.3, 0.7, 1.0, 1.0), f"EDITING: {editing_node.name}")
    imgui.spacing()
    imgui.separator()
    imgui.spacing()

    # Input fields for TreeNode attributes
    # Note: imgui.input_text returns (modified, new_value)
    changed, new_name = imgui.input_text("Name", editing_node.name, 128)
    if changed:
      editing_node.name = new_name
        
    changed_id, new_id = imgui.input_text("ID", editing_node.id, 64)
    if changed_id:
      editing_node.id = new_id

    if imgui.button("Save", (-1, 0)):
      editing_node = None
      # TODO: Callback function
        
    imgui.end_child()