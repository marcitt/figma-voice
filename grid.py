"""
Reference: Claude Sonnet 4.6
Code formatter: Black
"""

from dataclasses import dataclass
from typing import List, Optional

import math


from config import CANVAS_W, CANVAS_H

# why do we use typing and List?

# the overlay will transform the grid into screen coordinates later

# viewport has no data structure so we may be unsure what it contains


@dataclass
class GridData:
    x_lines: List[float]  # list of x values where vertical lines should be drawn
    y_lines: List[float]  # list of y values where horizontal lines should be drawn
    grid_type: str
    cell_size: Optional[float] = None

    def cells(self):
        # returns all cells with no numbering - numbers are assigned by visible_cells
        result = []
        for j in range(len(self.y_lines) - 1):
            for i in range(len(self.x_lines) - 1):
                x0 = self.x_lines[i]
                x1 = self.x_lines[i + 1]
                y0 = self.y_lines[j]
                y1 = self.y_lines[j + 1]
                result.append(
                    {
                        "number": None,
                        "cx": (x0 + x1) / 2,
                        "cy": (y0 + y1) / 2,
                        "canvas_w": x1 - x0,
                        "canvas_h": y1 - y0,
                        "north": y0,
                        "south": y1,
                        "west": x0,
                        "east": x1,
                    }
                )
        return result

    def visible_cells(self, zoom, min_w=10, min_h=10, min_area=40):
        # filters to cells large enough to be usable on screen, then assigns numbers
        result = []
        n = 1
        for c in self.cells():
            screen_w = c["canvas_w"] * zoom
            screen_h = c["canvas_h"] * zoom
            screen_area = screen_w * screen_h
            if screen_w >= min_w and screen_h >= min_h and screen_area >= min_area:
                c["number"] = n
                result.append(c)
                n += 1
        return result


class FixedGrid:
    # grid remains fixed on canvas - moves relative to the screen

    def __init__(self, cell_size: float = 100):
        self.cell_size = cell_size
        return

    # find visible canvas area
    def compute(self, canvas_state: dict):

        vp = canvas_state.get("viewport")

        if not vp:
            raise ValueError("canvas_state must contain a viewport")

        zoom = vp.get("zoom", 1)

        # finds the current canvas viewport x and y
        vp_x = vp.get("x", 0)
        vp_y = vp.get("y", 0)

        x0 = vp_x
        y0 = vp_y
        x1 = vp_x + CANVAS_W / zoom
        y1 = vp_y + CANVAS_H / zoom

        # find the nearest multiple of cell_size to find first grid line
        ox = math.floor(x0 / self.cell_size) * self.cell_size
        oy = math.floor(y0 / self.cell_size) * self.cell_size

        x_lines = []
        x = ox
        while x <= x1:  # stop when the right edge of the viewport is passed
            x_lines.append(x)
            x += self.cell_size  # step by cell size each time

        y_lines = []
        y = oy
        while y <= y1:  # stop when the bottom of the viewport is passed
            y_lines.append(y)
            y += self.cell_size  # step by cell size each time

        return GridData(
            x_lines=x_lines,
            y_lines=y_lines,
            grid_type="fixed",
            cell_size=self.cell_size,
        )


class NodeEdgeGrid:
    def __init__(self):
        pass

    def compute(self, canvas_state):
        vp = canvas_state.get("viewport")
        if not vp:
            raise ValueError("canvas_state must contain a viewport")

        nodes = canvas_state.get("nodes", [])

        x_coords = set()
        y_coords = set()

        # viewport boundary lines

        zoom = vp.get("zoom", 1)
        vp_x = vp.get("x", 0)
        vp_y = vp.get("y", 0)

        vp_x = vp.get("x", 0)
        vp_y = vp.get("y", 0)

        vp_w = CANVAS_W / zoom
        vp_h = CANVAS_H / zoom

        x_coords.add(vp_x)
        x_coords.add(vp_x + vp_w)
        y_coords.add(vp_y)
        y_coords.add(vp_y + vp_h)

        # node lines
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
