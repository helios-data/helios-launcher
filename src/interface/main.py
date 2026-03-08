"""
User Interface for Project Helios using ImGui.
"""

import os
from imgui_bundle import imgui, immapp, hello_imgui
from utils import TreeNode
from .components import TreeComponent

WINDOW_NAME = "Project Helios Launcher"
DEFAULT_WINDOW_SIZE = (1000, 600)

# Set assets folder for hello_imgui to load images
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(CURRENT_DIR, "assets")
hello_imgui.set_assets_folder(ASSETS_DIR)

# Default flags for the main sections to create a dashboard-like layout
SECTION_FLAGS = (imgui.WindowFlags_.no_scrollbar | 
                 imgui.WindowFlags_.no_move | 
                 imgui.WindowFlags_.no_resize | 
                 imgui.WindowFlags_.no_collapse |
                 imgui.WindowFlags_.no_title_bar)

WHITE_COLOR = (1.0, 1.0, 1.0, 1.0)

class UserInterface:
  """
  ImGui-based UI for displaying a hierarchical tree structure configuration.
  """
  def __init__(self, initial_data: TreeNode):
    self.initial_data = initial_data
    self.tree_component = TreeComponent(self.initial_data)

    immapp.run(self.gui, window_title=WINDOW_NAME, window_size=DEFAULT_WINDOW_SIZE)

  """
  Renders the main user interface.
  """
  def gui(self):
    # Get the main viewport size for responsive layout
    viewport = imgui.get_main_viewport()
    view_width = viewport.work_size.x
    view_height = viewport.work_size.y
    sidebar_width = view_width * 0.35

    imgui.push_style_color(imgui.Col_.window_bg, (0.96, 0.96, 0.97, 1.0)) # Off-white
    imgui.push_style_color(imgui.Col_.text, (0.1, 0.1, 0.1, 1.0)) # Dark text for white bg
    
    imgui.set_next_window_pos((sidebar_width, 0), imgui.Cond_.always)
    imgui.set_next_window_size((view_width - sidebar_width, view_height), imgui.Cond_.always)
  
    imgui.begin("Right Sidebar", flags=SECTION_FLAGS)
    
    avail_x = imgui.get_content_region_avail().x
    logo_w = avail_x * 0.7
    imgui.set_cursor_pos_x((avail_x - logo_w) * 0.5)
    hello_imgui.image_from_asset("helios.png", (logo_w, 0))

    imgui.spacing(); imgui.spacing()
    imgui.separator()
    imgui.spacing()

    # Action Grid
    imgui.text_disabled("QUICK ACTIONS")
    if imgui.begin_table("Actions", 2):
      imgui.table_next_row()
      imgui.table_next_column()
      if imgui.button("Add Component", (-1, 40)): pass
      imgui.table_next_column()
      if imgui.button("Configurations", (-1, 40)): pass
      imgui.table_next_row()
      imgui.table_next_column()
      if imgui.button("Global Settings", (-1, 40)): pass
      imgui.table_next_column()
      if imgui.button("Launch System", (-1, 40)): pass
      imgui.end_table()

    imgui.end()
    imgui.pop_style_color(2)

    imgui.set_next_window_pos((0, 0), imgui.Cond_.always)
    imgui.set_next_window_size((sidebar_width, view_height), imgui.Cond_.always)
    imgui.begin("Hierarchy", flags=SECTION_FLAGS)
    
    imgui.text_disabled("PROJECT OVERVIEW")
    imgui.separator()

    imgui.same_line()
    imgui.text_wrapped("Helios Launcher v1.0\nStatus: Active\nNodes: 12")
    
    imgui.spacing()
    
    imgui.text_disabled("HIERARCHY TREE")
    imgui.separator()
    imgui.spacing()
    self.tree_component.render()

    imgui.end()