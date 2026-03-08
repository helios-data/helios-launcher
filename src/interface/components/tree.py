from utils import TreeNode
from imgui_bundle import imgui

TABLE_FLAGS = (imgui.TableFlags_.row_bg | 
                imgui.TableFlags_.no_borders_in_body | 
                imgui.TableFlags_.scroll_y)

class TreeComponent:

  def __init__(self, initial_data: TreeNode) -> None:
    self.data = initial_data

    self.edit_node = None # Track which node is being edited for showing the input field

  """
  Main render function for the tree component, sets up the table and calls the recursive rendering function.
  """
  def render(self, height: float = 300):
    if imgui.begin_child("TreeRegion", (0, height)):
      if imgui.begin_table("TreeTable", 2, TABLE_FLAGS):
        imgui.table_setup_column("Name", imgui.TableColumnFlags_.width_stretch)
        imgui.table_setup_column("Actions", imgui.TableColumnFlags_.width_fixed, 100.0)
        self.render_tree_recursive(self.data)
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
    if not node.children:
      flags |= imgui.TreeNodeFlags_.leaf
    
    opened = imgui.tree_node_ex(f"{node.name}##{node.id}", flags)
    
    imgui.table_next_column()
    imgui.push_id(node.id)
    
    if imgui.small_button("Edit"):
      self.edit_node = node

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
