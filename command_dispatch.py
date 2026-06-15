from spatial_commands import (
    move_to_cell,
    move_to_cell_edge,
    move_edge_to_cell,
    resize_edge_to_cell,
    move_edge_by_pixels,
    move_by_pixels,
)
from config import GRID_ALIGNMENT_SUBDIVISIONS


def dispatch_structured_command(cmd, canvas_state, grid_mode="alignment", grid_subdivisions=GRID_ALIGNMENT_SUBDIVISIONS, grid_precision_cell_size=100):
    t = cmd.get("type")
    name = cmd.get("node_name", "").lower()

    if t == "move_to_cell":
        cell = cmd.get("cell_number")
        if cell is None:
            return {"error": "couldn't understand which cell to move to"}
        return move_to_cell(canvas_state, name, cell, grid_mode, grid_subdivisions, grid_precision_cell_size)

    elif t == "move_to_cell_edge":
        cell = cmd.get("cell_number")
        edge = cmd.get("cell_edge")
        if cell is None:
            return {"error": "couldn't understand which cell to move to"}
        if edge is None:
            return {"error": "couldn't understand which edge of the cell"}
        return move_to_cell_edge(canvas_state, name, cell, edge.lower(), grid_mode, grid_subdivisions, grid_precision_cell_size)

    elif t == "move_edge_to_cell":
        node_edge = cmd.get("node_edge")
        cell = cmd.get("cell_number")
        cell_edge = cmd.get("cell_edge")
        if node_edge is None:
            return {"error": "couldn't understand which edge to move"}
        if cell is None:
            return {"error": "couldn't understand which cell to move to"}
        if cell_edge is None:
            return {"error": "couldn't understand which edge of the cell"}
        return move_edge_to_cell(canvas_state, name, node_edge.lower(), cell, cell_edge.lower(), grid_mode, grid_subdivisions, grid_precision_cell_size)

    elif t == "resize_edge_to_cell":
        node_edge = cmd.get("node_edge")
        cell = cmd.get("cell_number")
        cell_edge = cmd.get("cell_edge")
        if node_edge is None:
            return {"error": "couldn't understand which edge to resize"}
        if cell is None:
            return {"error": "couldn't understand which cell to resize to"}
        if cell_edge is None:
            return {"error": "couldn't understand which edge of the cell"}
        return resize_edge_to_cell(canvas_state, name, node_edge.lower(), cell, cell_edge.lower(), grid_mode, grid_subdivisions, grid_precision_cell_size)

    elif t == "move_by_pixels":
        dx = cmd.get("dx")
        dy = cmd.get("dy")
        if dx is None or dy is None:
            return {"error": "couldn't understand how far to move"}
        return move_by_pixels(canvas_state, name, dx, dy)

    elif t == "move_edge_by_pixels":
        node_edge = cmd.get("node_edge")
        amount = cmd.get("amount")
        if node_edge is None:
            return {"error": "couldn't understand which edge to move"}
        if amount is None:
            return {"error": "couldn't understand how far to move"}
        return move_edge_by_pixels(canvas_state, name, node_edge.lower(), amount)

    else:
        return {"error": "didn't recognise that command"}