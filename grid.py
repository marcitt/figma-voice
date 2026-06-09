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

    # def cells(self):
    # result = []
    # n = 1
    # for j in range(len(self.y_lines) - 1):
    #     for i in range(len(self.x_lines) - 1):
    #         result.append({
    #             "number": n,
    #             "cx": (self.x_lines[i] + self.x_lines[i+1]) / 2,
    #             "cy": (self.y_lines[j] + self.y_lines[j+1]) / 2,
    #         })
    #         n += 1
    # return result


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
