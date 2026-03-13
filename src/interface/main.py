"""
User Interface for Project Helios using ImGui.
"""

import os
from imgui_bundle import imgui, immapp, hello_imgui
from utils import TreeNode, TreeUtils
from .components import TreeComponent, EditorComponent, QuickActions
import serial.tools.list_ports

WINDOW_NAME = "Project Helios Launcher"
DEFAULT_WINDOW_SIZE = (1000, 600)

LEFT_SIDE_WIDTH_RATIO = 0.30 # % of total width for the left sidebar
LEFT_FOOTER_HEIGHT = 300.0 # pixels
LOGO_WIDTH_RATIO = 0.7 # % of available width in the right sidebar for the logo

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
    self.data = initial_data

    self.tree_utils = TreeUtils()

    self.tree_component = TreeComponent(self)
    self.editor_component = EditorComponent()
    self.quick_actions = QuickActions(self)

    immapp.run(self.gui, window_title=WINDOW_NAME, window_size=DEFAULT_WINDOW_SIZE)

  """
  Renders the main user interface.
  """
  def gui(self):
    # Get the main viewport size for responsive layout
    viewport = imgui.get_main_viewport()
    view_width = viewport.work_size.x
    view_height = viewport.work_size.y
    sidebar_width = view_width * LEFT_SIDE_WIDTH_RATIO

    # Styling for the right sidebar
    imgui.push_style_color(imgui.Col_.window_bg, (0.96, 0.96, 0.97, 1.0)) # Off-white
    imgui.push_style_color(imgui.Col_.text, (0.1, 0.1, 0.1, 1.0)) # Dark text for white bg
    imgui.set_next_window_pos((sidebar_width, 0), imgui.Cond_.always)
    imgui.set_next_window_size((view_width - sidebar_width, view_height), imgui.Cond_.always)
  
    imgui.begin("Right Sidebar", flags=SECTION_FLAGS)
    
    avail_x = imgui.get_content_region_avail().x
    logo_w = avail_x * LOGO_WIDTH_RATIO
    imgui.set_cursor_pos_x((avail_x - logo_w) * 0.5)
    hello_imgui.image_from_asset("helios.png", (logo_w, 0))

    imgui.spacing(); imgui.spacing()
    imgui.separator()
    imgui.spacing()

    self.quick_actions.render()

    imgui.set_cursor_pos_y(imgui.get_window_height() - 60)
    launch = imgui.button("Launch Helios", (avail_x, 40))
    if launch:
      self.launch_helios()

    imgui.end()
    imgui.pop_style_color(2)

    # Styling for left sidebar
    imgui.set_next_window_pos((0, 0), imgui.Cond_.always)
    imgui.set_next_window_size((sidebar_width, view_height), imgui.Cond_.always)
    imgui.begin("Hierarchy", flags=SECTION_FLAGS)
    
    # Determine Footer State
    editing_node = self.tree_component.edit_node
    footer_height = LEFT_FOOTER_HEIGHT if editing_node else 0.0 # Only reserve space if editing
    
    imgui.text_disabled("PROJECT OVERVIEW")
    imgui.separator()

    imgui.same_line()
    imgui.text_wrapped("Helios Launcher v1.0\nStatus: Active\nNodes: 12")
    
    imgui.spacing()
    
    imgui.text_disabled("HIERARCHY TREE")
    imgui.separator()
    imgui.spacing()
    self.tree_component.render(-footer_height)

    if editing_node:
      self.editor_component.render(editing_node, height=footer_height, on_close_callback=self.close_editting_node, ports=self.get_ports_list())

    imgui.end()

  def close_editting_node(self):
    self.tree_component.clear_editting_mode()

  def get_ports_list(self):
    ports = serial.tools.list_ports.comports()
    return [f"{p.device} - {p.description}" for p in ports]

  def launch_helios(self):

    #TODO Check if eack node has a docker image built first
    # Check whenever the thing is updated, and update an icon
    

    print("Generating component tree from protobufs and configuration...")
    path = self.tree_utils.generate_component_tree(self.data)
    print(f"Component tree generated at: {path}")