def describe(cmd, result=None):
    
    # result comes from python spatial commands 
    if result:
        t = result.get("type")

        if t == "move_absolute":
            x, y = result.get("x"), result.get("y")
            if x is None or y is None:
                return "move to unknown position"
            return f"move to x={round(x, 1)}, y={round(y, 1)}"

        if t == "resize_absolute":
            x, y, w, h = result.get("x"), result.get("y"), result.get("width"), result.get("height")
            if any(v is None for v in (x, y, w, h)):
                return "resize to unknown position"
            return f"resize to x={round(x, 1)}, y={round(y, 1)}, w={round(w, 1)}, h={round(h, 1)}"
    
    # intent
    t = cmd.get("type")

    if t == "move_to_cell":
        name, cell = cmd.get("node_name") or "?", cmd.get("cell_number") or "?"
        return f"move {name} to cell {cell}"

    if t == "move_to_cell_edge":
        name, cell, edge = cmd.get("node_name") or "?", cmd.get("cell_number") or "?", cmd.get("cell_edge") or "?"
        return f"move {name} to cell {cell} {edge}"

    if t == "move_edge_to_cell":
        name, node_edge, cell, cell_edge = cmd.get("node_name") or "?", cmd.get("node_edge") or "?", cmd.get("cell_number") or "?", cmd.get("cell_edge") or "?"
        return f"move {name} {node_edge} to cell {cell} {cell_edge}"

    if t == "resize_edge_to_cell":
        name, node_edge, cell, cell_edge = cmd.get("node_name") or "?", cmd.get("node_edge") or "?", cmd.get("cell_number") or "?", cmd.get("cell_edge") or "?"
        return f"resize {name} {node_edge} to cell {cell} {cell_edge}"

    if t == "move_by_pixels":
        name, dx, dy = cmd.get("node_name") or "?", cmd.get("dx") or "?", cmd.get("dy") or "?"
        return f"move {name} dx={dx} dy={dy}"

    if t == "move_edge_by_pixels":
        name, edge, amount = cmd.get("node_name") or "?", cmd.get("node_edge") or "?", cmd.get("amount", 0)
        return f"{'expand' if amount > 0 else 'shrink'} {name} {edge} by {abs(amount)}px"

    if t == "select":
        q = cmd.get("query", [])
        return f"select {', '.join(q)}" if q else "deselect everything"

    if t == "focus_object":
        return f"zoom to {cmd.get('query') or '?'}"

    if t == "zoom_fit":
        return "zoom to fit all"

    if t == "zoom":
        d = cmd.get("zoom_delta", 0)
        return f"zoom {'in' if d > 0 else 'out'} by {abs(d)}"

    # if t == "undo":
    #     return f"undo {cmd.get('steps', 1)} step(s)"

    if t == "rename":
        name, new_name = cmd.get("query") or "?", cmd.get("name") or "?"
        return f"rename {name} to {new_name}"

    if t == "grid":
        action = cmd.get("action") or "?"
        if action == "subdivisions":
            return f"subdivisions set to {cmd.get('value', '?')}"
        return f"{action} grid"
    

    if t == "labels":
        return f"{cmd.get('action') or '?'} labels"

    if t == "pan":
        dx, dy = cmd.get("dx", 0), cmd.get("dy", 0)
        return f"pan dx={dx} dy={dy}"

    if t == "delete":
        return f"delete {cmd.get('query') or '?'}"

    if t == "copy":
        return f"copy {cmd.get('query') or '?'}"

    if t == "cut":
        return f"cut {cmd.get('query') or '?'}"

    if t == "paste":
        return "paste"

    return t or "unknown command"