from utils import TreeNode
from imgui_bundle import imgui, icons_fontawesome_6

TABLE_FLAGS = (imgui.TableFlags_.row_bg | 
                imgui.TableFlags_.no_borders_in_body | 
                imgui.TableFlags_.scroll_y)

# Icon + color constants for docker image status
ICON_BUILT     = "●"   # Filled circle  — image exists
ICON_NOT_BUILT = "●"   # Same shape, different color
COLOR_BUILT     = imgui.ImVec4(0.2, 0.85, 0.4, 1.0)   # Green
COLOR_NOT_BUILT = imgui.ImVec4(0.85, 0.25, 0.25, 1.0)  # Red
COLOR_UNKNOWN   = imgui.ImVec4(0.6, 0.6, 0.6, 1.0)     # Grey

class TreeComponent:

  def __init__(self, interface) -> None:
    self.interface = interface

    self.edit_node = None # Track which node is being edited for showing the input field

  """
  Main render function for the tree component, sets up the table and calls the recursive rendering function.
  """
  def render(self, height: float = 300):
    if imgui.begin_child("TreeRegion", (0, height)):
      if imgui.begin_table("TreeTable", 2, TABLE_FLAGS):
        imgui.table_setup_column("Name", imgui.TableColumnFlags_.width_stretch)
        imgui.table_setup_column("Actions", imgui.TableColumnFlags_.width_fixed, 100.0)
        self.render_tree_recursive(self.interface.data)
        imgui.end_table()
    imgui.end_child()

  """
  Recursively renders the tree structure with lines connecting nodes, and action buttons for each node.
  """
  def render_tree_recursive(self, node: TreeNode, depth=0):
    style = imgui.get_style()
    draw_list = imgui.get_window_draw_list()
    
    imgui.table_next_row()
    imgui.table_next_column()
    
    cursor_pos = imgui.get_cursor_screen_pos()
    line_color = imgui.get_color_u32(imgui.ImVec4(0.4, 0.4, 0.4, 1.0))
    indent_step = style.indent_spacing
    
    line_x = cursor_pos.x - indent_step + 10 
    line_y_mid = cursor_pos.y + imgui.get_text_line_height() * 0.5

    # Draw the L shape
    if depth > 0:
      draw_list.add_line((line_x, line_y_mid), (cursor_pos.x - 2, line_y_mid), line_color, 1.0)
      draw_list.add_line((line_x, cursor_pos.y - style.item_spacing.y), (line_x, line_y_mid), line_color, 1.0)

    flags = imgui.TreeNodeFlags_.span_full_width | imgui.TreeNodeFlags_.open_on_arrow | imgui.TreeNodeFlags_.default_open
    is_leaf = not node.children
    if is_leaf:
      flags |= imgui.TreeNodeFlags_.leaf
    
    opened = imgui.tree_node_ex(f"{node.name}##{node.id}", flags)
    
    imgui.table_next_column()
    imgui.push_id(node.id)
    
    # Docker image status icon — only shown on leaf nodes
    if is_leaf:
      exists = node.image_exists #! self.interface.docker_utils.check_image_exists(node)

      if exists is True:
        icon, color, tooltip = ICON_BUILT, COLOR_BUILT, "Image built"
      elif exists is False:
        icon, color, tooltip = ICON_NOT_BUILT, COLOR_NOT_BUILT, "Image not found"
      else:
        icon, color, tooltip = ICON_NOT_BUILT, COLOR_UNKNOWN, "Image status unknown"

      imgui.text_colored(color, icon)
      if imgui.is_item_hovered():
        imgui.set_tooltip(tooltip)
      imgui.same_line()

    else:
      # Invisible spacer to line up edit buttons
      icon_width = imgui.calc_text_size("●").x
      imgui.dummy((icon_width, imgui.get_text_line_height()))

    imgui.same_line(spacing=4.0)
    if imgui.small_button("Edit"):
      self.edit_node = node

    imgui.same_line()
    if node.warning:
      imgui.text_colored((1.0, 0.2, 0.2, 1.0), "⚠")
      imgui.same_line()

      if imgui.is_item_hovered():
        imgui.set_tooltip("Required ports/volumes not selected")

    imgui.pop_id()
    
    if opened:
      trunk_start_y = imgui.get_cursor_screen_pos().y
      
      for child in node.children:
        self.render_tree_recursive(child, depth + 1)
      
      # Draw Vertical Trunk connecting all children
      if node.children:
        trunk_end_y = imgui.get_cursor_screen_pos().y - imgui.get_text_line_height() * 0.5
        child_line_x = cursor_pos.x + 10 
        draw_list.add_line(
          (child_line_x, trunk_start_y - style.item_spacing.y),
          (child_line_x, trunk_end_y),
          line_color, 1.0
        )
            
      imgui.tree_pop()

  def clear_editting_mode(self):
    self.edit_node = None

  def delete_node(self, node_to_delete: TreeNode):
    """ Deletes the specified node from the tree. If the node is not found, does nothing. """
    def recursive_delete(current_node: TreeNode, target_node: TreeNode) -> bool:
      if target_node in current_node.children:
        current_node.children.remove(target_node)
        return True
      for child in current_node.children:
        if recursive_delete(child, target_node):
          return True
      return False
    
    recursive_delete(self.interface.data, node_to_delete)