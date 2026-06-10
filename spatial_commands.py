# commands.py

from grid import NodeEdgeGrid


def get_cell(canvas_state, cell_number):
    vp = canvas_state.get("viewport", {})
    zoom = vp.get("zoom", 1)
    grid_data = NodeEdgeGrid().compute(canvas_state)
    return next(
        (c for c in grid_data.visible_cells(zoom) if c["number"] == cell_number), None
    )


def get_node(canvas_state, node_name):
    return next(
        (n for n in canvas_state.get("nodes", []) if n["name"].lower() == node_name),
        None,
    )


def move_to_cell(canvas_state, node_name, cell_number):
    cell = get_cell(canvas_state, cell_number)
    node = get_node(canvas_state, node_name)
    if not cell or not node:
        return None
    return {
        "level": "figma",
        "type": "move_absolute",
        "query": node["name"],
        "x": cell["cx"] - node["width"] / 2,
        "y": cell["cy"] - node["height"] / 2,
    }


def move_edge_to_cell(canvas_state, node_name, node_edge, cell_number, cell_edge):
    cell = get_cell(canvas_state, cell_number)
    node = get_node(canvas_state, node_name)
    if not cell or not node:
        return None

    target = cell[cell_edge]
    x, y = node["x"], node["y"]

    if node_edge == "north":
        y = target
    elif node_edge == "south":
        y = target - node["height"]
    elif node_edge == "west":
        x = target
    elif node_edge == "east":
        x = target - node["width"]

    return {
        "level": "figma",
        "type": "move_absolute",
        "query": node["name"],
        "x": x,
        "y": y,
    }


def resize_edge_to_cell(canvas_state, node_name, node_edge, cell_number, cell_edge):
    cell = get_cell(canvas_state, cell_number)
    node = get_node(canvas_state, node_name)
    if not cell or not node:
        return None

    target = cell[cell_edge]
    x, y, w, h = node["x"], node["y"], node["width"], node["height"]

    if node_edge == "north":
        h = (y + h) - target
        y = target
    elif node_edge == "south":
        h = target - y
    elif node_edge == "west":
        w = (x + w) - target
        x = target
    elif node_edge == "east":
        w = target - x

    return {
        "level": "figma",
        "type": "resize_absolute",
        "query": node["name"],
        "x": x,
        "y": y,
        "width": w,
        "height": h,
    }
