from utils import TreeNode
from imgui_bundle import imgui

TABLE_FLAGS = (imgui.TableFlags_.row_bg | 
                imgui.TableFlags_.no_borders_in_body | 
                imgui.TableFlags_.scroll_y)

class TreeComponent:

  def __init__(self, initial_data: TreeNode) -> None:
      self.data = initial_data

  def render(self):
    # This method can be called from the main GUI loop to render the tree
    if imgui.begin_child("TreeRegion", (0, 300)):
        if imgui.begin_table("TreeTable", 2, TABLE_FLAGS):
            imgui.table_setup_column("Name", imgui.TableColumnFlags_.width_stretch)
            imgui.table_setup_column("Actions", imgui.TableColumnFlags_.width_fixed, 100.0)
            self.render_tree_recursive(self.data)
            imgui.end_table()
    imgui.end_child()
    pass

  """
  Recursively renders the tree structure with lines connecting nodes, and action buttons for each node.
  """
  def render_tree_recursive(self, node: TreeNode, depth=0):
    style = imgui.get_style()
    draw_list = imgui.get_window_draw_list()
    
    imgui.table_next_row()
    imgui.table_next_column()
    
    # --- 1. COORDINATE TRACKING FOR LINES ---
    cursor_pos = imgui.get_cursor_screen_pos()
    line_color = imgui.get_color_u32(imgui.ImVec4(0.4, 0.4, 0.4, 1.0))
    indent_step = style.indent_spacing
    
    # The X position for the vertical line (the 'track')
    # We go back by one indent step and nudge forward to center under the arrow
    line_x = cursor_pos.x - indent_step + 10 
    line_y_mid = cursor_pos.y + imgui.get_text_line_height() * 0.5

    if depth > 0:
        # Draw Horizontal L-part
        draw_list.add_line((line_x, line_y_mid), (cursor_pos.x - 2, line_y_mid), line_color, 1.0)
        # Draw Vertical connector to parent
        draw_list.add_line((line_x, cursor_pos.y - style.item_spacing.y), (line_x, line_y_mid), line_color, 1.0)

    # --- 2. RENDER NODE ---
    flags = imgui.TreeNodeFlags_.span_full_width | imgui.TreeNodeFlags_.open_on_arrow
    if not node.children:
        flags |= imgui.TreeNodeFlags_.leaf
    
    opened = imgui.tree_node_ex(f"{node.name}##{node.id}", flags)
    
    # --- 3. ACTUAL BUTTONS (Column 2) ---
    imgui.table_next_column()
    
    # Using PushID so buttons in different rows don't conflict
    imgui.push_id(node.id)
    
    # Edit Button (Using a pencil-like emoji or text)
    if imgui.small_button("Edit"):
        print(f"Clicked Edit on: {node.name}")
        
    imgui.same_line()
    
    # Add Button
    if imgui.small_button("+"):
        print(f"Clicked Add on: {node.name}")
        
    imgui.pop_id()
    
    # --- 4. RECURSION & TRUNK LINES ---
    if opened:
        # Note where the children start
        trunk_start_y = imgui.get_cursor_screen_pos().y
        
        for child in node.children:
            self.render_tree_recursive(child, depth + 1)
        
        # Draw Vertical Trunk connecting all children
        if node.children:
            trunk_end_y = imgui.get_cursor_screen_pos().y - imgui.get_text_line_height() * 0.5
            # We draw this at the child's line_x position
            child_line_x = cursor_pos.x + 10 
            draw_list.add_line(
                (child_line_x, trunk_start_y - style.item_spacing.y),
                (child_line_x, trunk_end_y),
                line_color, 1.0
            )
            
        imgui.tree_pop()
