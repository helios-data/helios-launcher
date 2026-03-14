from imgui_bundle import imgui

class QuickActions:
  def __init__(self, interface):
    self.interface = interface # User interface class

  def render(self):
    imgui.text_disabled("QUICK ACTIONS")
    if imgui.begin_table("Actions", 2):
      imgui.table_next_row()
      imgui.table_next_column()
      if imgui.button("Add Component", (-1, 40)): pass
      imgui.table_next_column()
      if imgui.button("Global Settings", (-1, 40)): pass
      imgui.table_next_row()
      imgui.table_next_column()
      if imgui.button("Scan Existing Docker Images", (-1, 40)): pass
        self.interface.scan_docker_images()
      imgui.table_next_column()
      if imgui.button("Build Missing Docker Images", (-1, 40)): pass
        self.interface.build_missing_docker_images()
      imgui.table_next_row()
      imgui.table_next_column()
      if imgui.button("Save Configuration", (-1, 40)): 
        print("Saving configuration...")
        self.interface.tree_utils.save_tree_as_dict(self.interface.data)
        print("Configuration saved.")
      imgui.table_next_column()
      if imgui.button("Load Configuration", (-1, 40)): 
        print("Loading saved configuration...")
        self.interface.data = self.interface.tree_utils.load_tree_from_dict()
        print(f"Configuration loaded.")
      imgui.end_table()