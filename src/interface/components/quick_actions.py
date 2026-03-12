from imgui_bundle import imgui

class QuickActions:
  def __init__(self):
    pass

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
      if imgui.button("Save Configuration", (-1, 40)): pass
      imgui.table_next_column()
      if imgui.button("Load Configuration", (-1, 40)): pass
      imgui.end_table()