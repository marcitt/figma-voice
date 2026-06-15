from dataclasses import dataclass
from typing import List, Optional
import math

from config import CANVAS_W, CANVAS_H, GRID_ALIGNMENT_SUBDIVISIONS, GRID_MAX_CELLS_FOR_LABELS


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

    def visible_cells(self, zoom, min_w=20, min_h=20, min_area=40):
        # filters to cells large enough to be usable on screen, assigns contiguous numbers
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

        # only show numbers if few enough cells to be readable
        # if len(result) > GRID_MAX_CELLS_FOR_LABELS:
        #     for c in result:
        #         c["number"] = None

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
    # grid derived from node edges - cells are semantically grounded in canvas content

    def __init__(self, subdivisions=GRID_ALIGNMENT_SUBDIVISIONS):
        self.subdivisions = subdivisions

    def _subdivide_empty_cells(self, x_lines, y_lines, nodes):
        extra_x = set()
        extra_y = set()
        if self.subdivisions <= 1:
            return x_lines, y_lines
        for j in range(len(y_lines) - 1):
            for i in range(len(x_lines) - 1):
                x0, x1 = x_lines[i], x_lines[i + 1]
                y0, y1 = y_lines[j], y_lines[j + 1]
                if not _cell_has_nodes(x0, x1, y0, y1, nodes):
                    for d in range(1, self.subdivisions):
                        extra_x.add(x0 + (x1 - x0) * d / self.subdivisions)
                        extra_y.add(y0 + (y1 - y0) * d / self.subdivisions)
        return sorted(set(x_lines) | extra_x), sorted(set(y_lines) | extra_y)

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

        x_lines, y_lines = self._subdivide_empty_cells(
            sorted(x_coords), sorted(y_coords), nodes
        )

        return GridData(x_lines=x_lines, y_lines=y_lines, grid_type="node_edge")


def get_grid(mode="alignment", subdivisions=GRID_ALIGNMENT_SUBDIVISIONS, precision_cell_size=100):
    if mode == "precision":
        return FixedGrid(cell_size=precision_cell_size)
    return NodeEdgeGrid(subdivisions=subdivisions)