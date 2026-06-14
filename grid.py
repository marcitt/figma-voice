from dataclasses import dataclass
from typing import List, Optional
import math

from config import CANVAS_W, CANVAS_H


@dataclass
class GridData:
    x_lines: List[float]  # vertical grid lines in canvas coordinates
    y_lines: List[float]  # horizontal grid lines in canvas coordinates
    grid_type: str
    cell_size: Optional[float] = None

    def cells(self):
        # generates all cells from grid lines, numbering assigned later
        result = []
        for j in range(len(self.y_lines) - 1):
            for i in range(len(self.x_lines) - 1):
                x0, x1 = self.x_lines[i], self.x_lines[i + 1]
                y0, y1 = self.y_lines[j], self.y_lines[j + 1]
                result.append({
                    "number": None,
                    "cx": (x0 + x1) / 2,
                    "cy": (y0 + y1) / 2,
                    "canvas_w": x1 - x0,
                    "canvas_h": y1 - y0,
                    "north": y0,
                    "south": y1,
                    "west": x0,
                    "east": x1,
                })
        return result

    def visible_cells(self, zoom, min_w=10, min_h=10, min_area=40):
        # filters to cells large enough to be usable on screen, assigns contiguous numbers
        result = []
        n = 1
        for c in self.cells():
            screen_w = c["canvas_w"] * zoom
            screen_h = c["canvas_h"] * zoom
            if screen_w >= min_w and screen_h >= min_h and screen_w * screen_h >= min_area:
                c["number"] = n
                result.append(c)
                n += 1
        return result

class NodeEdgeGrid:
    # grid derived from node edges 

    def compute(self, canvas_state: dict):
        vp = canvas_state.get("viewport")
        if not vp:
            raise ValueError("canvas_state must contain a viewport")

        nodes = canvas_state.get("nodes", [])
        zoom = vp.get("zoom", 1)
        vp_x = vp.get("x", 0)
        vp_y = vp.get("y", 0)

        x_coords = set()
        y_coords = set()

        # viewport boundaries
        x_coords.add(vp_x)
        x_coords.add(vp_x + CANVAS_W / zoom)
        y_coords.add(vp_y)
        y_coords.add(vp_y + CANVAS_H / zoom)

        # node edges
        for node in nodes:
            x_coords.add(node["x"])
            x_coords.add(node["x"] + node["width"])
            y_coords.add(node["y"])
            y_coords.add(node["y"] + node["height"])

        return GridData(
            x_lines=sorted(x_coords),
            y_lines=sorted(y_coords),
            grid_type="node_edge",
        )