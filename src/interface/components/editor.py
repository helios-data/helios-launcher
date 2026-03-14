from utils import TreeNode
from imgui_bundle import imgui, portable_file_dialogs as pfd
from config import *

class EditorComponent:
  def __init__(self) -> None:
    #self.current_node = None
    pass

  def render(self, node: TreeNode | None, height: float = 0, on_close_callback=None, ports: list = ["None"]) -> None:
    if not node:
      self.current_node = None
      return
    
    # if self.current_node == None:
    #   new_node = False
    # else:
    #   new_node = True if node.id != self.current_node else False
    
    # self.current_node = node

    imgui.set_cursor_pos_y(imgui.get_window_height() - height) # Pin to bottom

    # Use ImGuiWindowFlags_.always_vertical_scrollbar if you expect many settings
    imgui.begin_child("EditPanel", (0, height))
    
    imgui.text_colored((0.3, 0.7, 1.0, 1.0), f"EDITING: {node.name}")
    imgui.spacing()
    imgui.separator()
    imgui.spacing()

    # --- Standard Attributes ---
    changed, new_name = imgui.input_text("Name", node.name, 128)
    if changed:
      self.node_changed(node)
      node.name = new_name

    if node.children == []:    
      changed_type, new_type = imgui.combo("Node Type", node.type.value, [node.name for node in Node_Type])
      if changed_type:
        self.node_changed(node)
        node.type = Node_Type(new_type)

      changed_location, new_location = imgui.input_text("Location", node.location, 128)
      if changed_location:
        self.node_changed(node)
        node.location = new_location

      changed_hash, new_hash = imgui.input_text("Hash", node.hash, 128)
      if changed_hash:
        self.node_changed(node)
        node.hash = new_hash

      imgui.spacing()

      # --- Advanced Settings Section ---
      # CollapsingHeader returns True if the section is expanded
      # if new_node:
      #   imgui.set_next_item_open(False)
      if imgui.collapsing_header("Advanced Settings"):
        #TODO: Close header when moving to a new node
        imgui.indent()  # Visual offset for nested items
        
        # --- PORTS SECTION (List with Dropdown) ---
        imgui.text("Port Bindings")
        for i, port in enumerate(node.ports):
          # Use unique IDs for each combo in a loop
          imgui.set_next_item_width(imgui.get_content_region_avail().x - 125)
          changed, new_port = imgui.combo(f"Port ##{i}", ports.index(port) if port in ports else 0, ports)
          if changed:
            node.ports[i] = ports[new_port]
            
          imgui.same_line()
          if imgui.button(f"Remove##p{i}"):
            node.ports.pop(i)

        if imgui.button("+ Add Port"):
          node.ports.append(ports[0])

        imgui.spacing()
        imgui.separator()

        # --- VOLUMES SECTION (List with Folder Picker) ---
        imgui.text("Volume Mounts")
        for i, vol in enumerate(node.volumes):
          imgui.set_next_item_width(imgui.get_content_region_avail().x - 160)
          changed, new_vol = imgui.input_text(f"##vol{i}", vol, 256)
          if changed:
            node.volumes[i] = new_vol
          
          imgui.same_line()
          if imgui.button(f"Browse##{i}"):
            dialog = pfd.open_file("Select a file", ".")
            if dialog.result():
              node.volumes[i] = dialog.result()[0]
          
          imgui.same_line()
          if imgui.button(f"Remove##v{i}"):
            node.volumes.pop(i)

        if imgui.button("+ Add Volume"):
          node.volumes.append("")

        imgui.unindent()

    imgui.spacing()
    imgui.separator()
    imgui.spacing()

    # --- Footer ---
    if imgui.button("Close", (-1, 0)):
      if on_close_callback:
        on_close_callback()
        
    imgui.end_child()

  def node_changed(self, node: TreeNode):
    """ If any of the basic node information is changed, we need to recheck if the image exists """
    node.image_exists = None