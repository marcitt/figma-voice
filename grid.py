from dataclasses import dataclass, field
from typing import List, Optional
import math

from config import CANVAS_W, CANVAS_H, GRID_ALIGNMENT_SUBDIVISIONS, GRID_MAX_CELLS_FOR_LABELS


@dataclass
class GridData:
    x_lines: List[float]        # all vertical grid lines in canvas coordinates
    y_lines: List[float]        # all horizontal grid lines in canvas coordinates
    grid_type: str
    cell_size: Optional[float] = None
    major_x_lines: Optional[List[float]] = None  # alignment-level lines (drawn thick)
    major_y_lines: Optional[List[float]] = None  # alignment-level lines (drawn thick)

    def cells(self):
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

    def visible_cells(self, zoom, min_w=20, min_h=20, min_area=40):
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
    # uniform grid fixed to canvas coordinates

    def __init__(self, cell_size: float = 100):
        self.cell_size = cell_size

    def compute(self, canvas_state: dict):
        vp = canvas_state.get("viewport")
        if not vp:
            raise ValueError("canvas_state must contain a viewport")

        zoom = vp.get("zoom", 1)
        vp_x = vp.get("x", 0)
        vp_y = vp.get("y", 0)

        x1 = vp_x + CANVAS_W / zoom
        y1 = vp_y + CANVAS_H / zoom

        ox = math.floor(vp_x / self.cell_size) * self.cell_size
        oy = math.floor(vp_y / self.cell_size) * self.cell_size

        x_lines = []
        x = ox
        while x <= x1:
            x_lines.append(x)
            x += self.cell_size

        y_lines = []
        y = oy
        while y <= y1:
            y_lines.append(y)
            y += self.cell_size

        return GridData(x_lines=x_lines, y_lines=y_lines, grid_type="fixed", cell_size=self.cell_size)


def _cell_has_nodes(cell_x0, cell_x1, cell_y0, cell_y1, nodes):
    for node in nodes:
        if (
            node["x"] < cell_x1
            and node["x"] + node["width"] > cell_x0
            and node["y"] < cell_y1
            and node["y"] + node["height"] > cell_y0
        ):
            return True
    return False


class NodeEdgeGrid:
    # grid derived from node edges with no subdivision — used as the base for HybridGrid

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

        x_coords.add(vp_x)
        x_coords.add(vp_x + CANVAS_W / zoom)
        y_coords.add(vp_y)
        y_coords.add(vp_y + CANVAS_H / zoom)

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


class HybridGrid:
    # alignment grid at base level, with uniform NxN fixed subcells within each alignment cell
    # at subdivisions=1 behaves identically to NodeEdgeGrid
    # at subdivisions=2+, each alignment cell is divided into NxN uniform subcells

    def __init__(self, subdivisions: int = 2):
        self.subdivisions = subdivisions

    def compute(self, canvas_state: dict):
        # step 1 — compute base alignment grid
        base = NodeEdgeGrid().compute(canvas_state)
        major_x = base.x_lines
        major_y = base.y_lines

        if self.subdivisions <= 1:
            return GridData(
                x_lines=major_x,
                y_lines=major_y,
                grid_type="hybrid",
                major_x_lines=list(major_x),
                major_y_lines=list(major_y),
            )

        # step 2 — add uniform subcell lines within each alignment cell
        extra_x = set()
        extra_y = set()

        for i in range(len(major_x) - 1):
            x0, x1 = major_x[i], major_x[i + 1]
            for d in range(1, self.subdivisions):
                extra_x.add(x0 + (x1 - x0) * d / self.subdivisions)

        for j in range(len(major_y) - 1):
            y0, y1 = major_y[j], major_y[j + 1]
            for d in range(1, self.subdivisions):
                extra_y.add(y0 + (y1 - y0) * d / self.subdivisions)

        all_x = sorted(set(major_x) | extra_x)
        all_y = sorted(set(major_y) | extra_y)

        return GridData(
            x_lines=all_x,
            y_lines=all_y,
            grid_type="hybrid",
            major_x_lines=list(major_x),
            major_y_lines=list(major_y),
        )


def get_grid(mode="alignment", subdivisions=GRID_ALIGNMENT_SUBDIVISIONS, precision_cell_size=100):
    if mode == "precision":
        return FixedGrid(cell_size=precision_cell_size)
    return HybridGrid(subdivisions=subdivisions)