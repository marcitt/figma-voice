import re

from spatial_commands import (
    move_to_cell,
    move_to_cell_edge,
    move_edge_to_cell,
    resize_edge_to_cell,
    move_edge_by_pixels,
    move_by_pixels,
)

from config import GRID_ALIGNMENT_SUBDIVISIONS


def regex_command_processing(text, canvas_state, grid_mode="alignment", grid_subdivisions=GRID_ALIGNMENT_SUBDIVISIONS, grid_precision_cell_size=100):
    text_lower = text.lower()
    
    
    
    if len(text_lower.split()) > 8 or len(text_lower) > 60:
        return None  # fall through to LLM or not_recognised
    
     # --- UNDO ---
    if "undo" in text_lower:
        return {"level": "system", "type": "undo"}

    # --- LABEL NODES ---
    if "label nodes" in text_lower:
        return "LABEL_NODES"

    # --- SELECT ---
    match = re.match(r"select (.+(?:,\s*.+)+)$", text_lower)
    if match:
        names = [n.strip() for n in match.group(1).split(",")]
        return {"level": "figma", "type": "select", "query": names}

    node_names = [n["name"].lower() for n in canvas_state.get("nodes", [])]
    words = text_lower.replace("select ", "").replace(" and", "").split()
    matched = [w for w in words if w in node_names]
    if len(matched) > 1:
        return {"level": "figma", "type": "select", "query": matched}

    if "deselect everything" in text_lower:
        return {"level": "figma", "type": "select", "query": []}

    # --- ZOOM ---
    # this needs to come before "zoom to " to prevent it getting caught
    
    if re.search(r"zoom in$", text_lower):
        return {"level": "figma", "type": "zoom", "zoom_delta": 0.5}
    if re.search(r"zoom out$", text_lower):
        return {"level": "figma", "type": "zoom", "zoom_delta": -0.5}
    
    if any(p in text_lower for p in ("zoom to show everything", "zoom to fit", "zoom to context", "focus context")):
        print(f"[DEBUG] text_lower: {repr(text_lower)}")
        return {"level": "figma", "type": "zoom_fit"}
    
    # --- FOCUS ---
    
    for prefix in ("zoom to focus ", "zoom to object ", "zoom to ", "focus "):
        if text_lower.startswith(prefix):
            remainder = text_lower[len(prefix):].strip()
            if not remainder.isdigit():
                return {"level": "figma", "type": "focus_object", "query": remainder}

    # --- PAN ---
    match = re.match(r"move (left|right|up|down)(?: (\d+))?$", text_lower)
    if match:
        direction, amount = match.group(1), int(match.group(2) or 200)
        dx = {"right": amount, "left": -amount}.get(direction, 0)
        dy = {"down": amount, "up": -amount}.get(direction, 0)
        return {"level": "figma", "type": "pan", "dx": dx, "dy": dy}

    match = re.match(r"pan (left|right|up|down)(?: (\d+))?$", text_lower)
    if match:
        direction, amount = match.group(1), int(match.group(2) or 200)
        dx = {"right": amount, "left": -amount}.get(direction, 0)
        dy = {"down": amount, "up": -amount}.get(direction, 0)
        return {"level": "figma", "type": "pan", "dx": dx, "dy": dy}
    
    # --- GRID ---
    if "show grid" in text_lower:
        return {"level": "system", "type": "grid", "action": "show"}
    if "hide grid" in text_lower or "hybrid" in text_lower or "hydrate" in text_lower:
        return {"level": "system", "type": "grid", "action": "hide"}

    # --- GRID MODE ---
    if any(p in text_lower for p in ("alignment grid", "snap grid", "object grid")):
        return {"level": "system", "type": "grid", "action": "mode_alignment"}
    # if any(p in text_lower for p in ("precision grid", "fixed grid", "uniform grid")):
    #     return {"level": "system", "type": "grid", "action": "mode_precision"}

    # --- GRID DETAIL ---
    if any(p in text_lower for p in ("more detail", "increase grid", "increase density", "increase grid density", "subdivide")):
        return {"level": "system", "type": "grid", "action": "detail_increase"}
    if any(p in text_lower for p in ("less detail", "decrease grid", "decrease density", "decrease grid density", "coarser grid")):
        return {"level": "system", "type": "grid", "action": "detail_decrease"}

    # --- LABELS ---
    if "show labels" in text_lower:
        return {"level": "system", "type": "labels", "action": "show"}
    if "hide labels" in text_lower:
        return {"level": "system", "type": "labels", "action": "hide"}

    # --- OVERLAY ---
    if "show overlay" in text_lower or "open overlay" in text_lower:
        return {"level": "system", "type": "overlay", "action": "show"}
    if "hide overlay" in text_lower or "close overlay" in text_lower:
        return {"level": "system", "type": "overlay", "action": "hide"}
    # if "toggle overlay" in text_lower:
    #     return {"level": "system", "type": "overlay", "action": "toggle"}

    # --- MOVE TO CELL ---
    match = re.match(r"move (.+) to (?:cell|sell) (\d+)$", text_lower)
    if match:
        return move_to_cell(canvas_state, match.group(1).strip(), int(match.group(2)), grid_mode, grid_subdivisions, grid_precision_cell_size)

    # --- MOVE NODE TO CELL EDGE ---
    match = re.match(r"move (.+) to (?:cell|sell) (\d+) (north|south|east|west)$", text_lower)
    if match:
        return move_to_cell_edge(canvas_state, match.group(1).strip(), int(match.group(2)), match.group(3), grid_mode, grid_subdivisions, grid_precision_cell_size)

    # --- MOVE EDGE TO CELL ---
    match = re.match(r"move (.+?) (north|south|east|west) to (?:cell|sell) (\d+)(?: (north|south|east|west))?$", text_lower)
    if match:
        return move_edge_to_cell(canvas_state, match.group(1).strip(), match.group(2), int(match.group(3)), match.group(4) or "centre", grid_mode, grid_subdivisions, grid_precision_cell_size)

    # --- MOVE BY PIXELS ---
    match = re.match(r"move (.+) (\d+) pixels? (right|left|up|down)$", text_lower)
    if match:
        name, amount, direction = match.group(1).strip(), int(match.group(2)), match.group(3)
        dx = {"right": amount, "left": -amount}.get(direction, 0)
        dy = {"down": amount, "up": -amount}.get(direction, 0)
        return move_by_pixels(canvas_state, name, dx, dy)

    # --- RESIZE EDGE TO CELL ---
    match = re.match(r"resize (.+?) (north|south|east|west) to (?:cell|sell) (\d+)(?: (north|south|east|west))?$", text_lower)
    if match:
        return resize_edge_to_cell(canvas_state, match.group(1).strip(), match.group(2), int(match.group(3)), match.group(4) or "centre", grid_mode, grid_subdivisions, grid_precision_cell_size)

    # --- RESIZE NODE TO CELL EDGE ---
    match = re.match(r"resize (.+) to (?:cell|sell) (\d+) (north|south|east|west)$", text_lower)
    if match:
        edge = match.group(3)
        return resize_edge_to_cell(canvas_state, match.group(1).strip(), edge, int(match.group(2)), edge, grid_mode, grid_subdivisions, grid_precision_cell_size)

    # --- INCREASE/DECREASE EDGE BY PIXELS ---
    match = re.match(r"(increase|decrease) (.+) (north|south|east|west) (\d+) pixels?$", text_lower)
    if match:
        amount = int(match.group(4))
        if match.group(1) == "decrease":
            amount = -amount
        return move_edge_by_pixels(canvas_state, match.group(2).strip(), match.group(3), amount)

    return None