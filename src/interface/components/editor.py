from utils import TreeNode
from imgui_bundle import imgui, portable_file_dialogs as pfd

from utils.tree import NODE_TYPES

class EditorComponent:
  def __init__(self) -> None:
    pass

  def render(self, editing_node: TreeNode | None, height: float = 0, on_close_callback=None, ports: list = ["None"]) -> None:
    if not editing_node:
      return
    
    imgui.set_cursor_pos_y(imgui.get_window_height() - height) # Pin to bottom

    # Use ImGuiWindowFlags_.always_vertical_scrollbar if you expect many settings
    imgui.begin_child("EditPanel", (0, height))
    
    imgui.text_colored((0.3, 0.7, 1.0, 1.0), f"EDITING: {editing_node.name}")
    imgui.spacing()
    imgui.separator()
    imgui.spacing()

    # --- Standard Attributes ---
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

    imgui.spacing()

    # --- Advanced Settings Section ---
    # CollapsingHeader returns True if the section is expanded
    if imgui.collapsing_header("Advanced Settings"):
      #TODO: Close header when moving to a new node
      imgui.indent()  # Visual offset for nested items
      
      # --- PORTS SECTION (List with Dropdown) ---
      imgui.text("Port Bindings")
      for i, port in enumerate(editing_node.ports):
        # Use unique IDs for each combo in a loop
        changed, new_port = imgui.combo(f"Port ##{i}", ports.index(port) if port in ports else 0, ports)
        if changed:
          editing_node.ports[i] = ports[new_port]
          
        imgui.same_line()
        if imgui.button(f"Remove##p{i}"):
          editing_node.ports.pop(i)

      if imgui.button("+ Add Port"):
        editing_node.ports.append(ports[0])

      imgui.spacing()
      imgui.separator()

      # --- VOLUMES SECTION (List with Folder Picker) ---
      imgui.text("Volume Mounts")
      for i, vol in enumerate(editing_node.volumes):
        imgui.set_next_item_width(imgui.get_content_region_avail().x - 100)
        changed, new_vol = imgui.input_text(f"##vol{i}", vol, 256)
        if changed:
          editing_node.volumes[i] = new_vol
        
        imgui.same_line()
        if imgui.button(f"Browse##{i}"):
          dialog = pfd.open_file("Select a file", ".")
          if dialog.result():
            editing_node.volumes[i] = dialog.result()[0]
        
        imgui.same_line()
        if imgui.button(f"Remove##v{i}"):
          editing_node.volumes.pop(i)

      if imgui.button("+ Add Volume"):
        editing_node.volumes.append("")

      imgui.unindent()

    imgui.spacing()
    imgui.separator()
    imgui.spacing()

    # --- Footer ---
    if imgui.button("Close", (-1, 0)):
      if on_close_callback:
        on_close_callback()
        
    imgui.end_child()