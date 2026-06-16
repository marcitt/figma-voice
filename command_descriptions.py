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
 
    # --- SPATIAL ---
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
 
    # --- FIGMA OBJECT ---
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
    if t == "pan":
        dx, dy = cmd.get("dx", 0), cmd.get("dy", 0)
        return f"pan dx={dx} dy={dy}"
    if t == "rename":
        name, new_name = cmd.get("query") or "?", cmd.get("name") or "?"
        return f"rename {name} to {new_name}"
    if t == "delete":
        return f"delete {cmd.get('query') or '?'}"
    if t == "copy":
        return f"copy {cmd.get('query') or '?'}"
    if t == "cut":
        return f"cut {cmd.get('query') or '?'}"
    if t == "paste":
        return "paste"
    if t == "group":
        q = cmd.get("query", [])
        return f"group {', '.join(q)}" if q else "group"
    if t == "ungroup":
        return f"ungroup {cmd.get('query') or '?'}"
    if t == "bring_forward":
        return f"bring {cmd.get('query') or '?'} forward"
    if t == "send_backward":
        return f"send {cmd.get('query') or '?'} backward"
    if t == "move_absolute":
        x, y = cmd.get("x"), cmd.get("y")
        return f"move to x={round(x, 1)}, y={round(y, 1)}" if x is not None and y is not None else "move to position"
    if t == "resize_absolute":
        w, h = cmd.get("width"), cmd.get("height")
        return f"resize to w={round(w, 1)}, h={round(h, 1)}" if w is not None and h is not None else "resize"
 
    # --- GRID ---
    if t == "grid":
        action = cmd.get("action") or "?"
        if action == "show": return "show grid"
        if action == "hide": return "hide grid"
        if action == "toggle": return "toggle grid"
        if action == "mode_alignment": return "alignment grid"
        if action == "mode_precision": return "precision grid"
        if action == "detail_increase":
            val = cmd.get("value")
            return f"grid detail {val}" if val is not None else "more detail"
        if action == "detail_decrease":
            val = cmd.get("value")
            return f"grid detail {val}" if val is not None else "less detail"
        return f"{action} grid"
 
    # --- LABELS / OVERLAY ---
    if t == "labels":
        return f"{cmd.get('action') or '?'} labels"
    if t == "overlay":
        return f"{cmd.get('action') or '?'} overlay"
 
    # --- UNDO ---
    if t == "undo":
        kind = cmd.get("kind")
        target = cmd.get("target", "")
        if kind == "node": return f"undo {target}"
        if kind == "viewport": return "undo viewport"
        if kind == "selection": return "undo selection"
        if kind == "overlay": return "undo grid"
        return "nothing to undo"
 
    # --- SYSTEM ---
    if t == "not_recognised": return "not recognised"
    if t == "hud": return ""
 
    return "not recognised"