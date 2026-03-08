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

    # 2. Push the 'window_bg' style color
    imgui.push_style_color(imgui.Col_.window_bg, WHITE_COLOR)
    imgui.set_next_window_pos((view_width * 0.4, 0), imgui.Cond_.always)
    imgui.set_next_window_size((view_width * 0.6, 0), imgui.Cond_.always)
    imgui.begin("Preview", flags=SECTION_FLAGS)
    center_x = (imgui.get_content_region_avail().x - view_width * 0.4) * 0.5
    if center_x > 0:
      imgui.set_cursor_pos_x(center_x)
    hello_imgui.image_from_asset("helios.png", (view_width * 0.4, 0))
    imgui.end()
    imgui.pop_style_color() 

    imgui.set_next_window_pos((0, 0), imgui.Cond_.always)
    imgui.set_next_window_size((view_width * 0.4, view_height), imgui.Cond_.always)
    imgui.begin("Hierarchy", flags=SECTION_FLAGS)
    
    imgui.text_disabled("PROJECT OVERVIEW")
    imgui.separator()

    imgui.same_line()
    imgui.text_wrapped("Helios Launcher v1.0\nStatus: Active\nNodes: 12")
    
    imgui.spacing()
    imgui.separator()
    imgui.spacing()
    
    imgui.text("Hierarchy Tree:")
    self.tree_component.render()

    imgui.spacing()
    imgui.separator()
    if imgui.collapsing_header("Node Properties"):
        imgui.indent()
        imgui.text("Selection: None")
        imgui.color_edit4("Theme Color", (0.2, 0.5, 0.8, 1.0))
        imgui.unindent()

    imgui.end()