import json
import asyncio
import threading
import websockets
from AppKit import (
    NSApplication,
    NSPanel,
    NSColor,
    NSView,
    NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSScreen,
    NSBezierPath,
    NSEvent,
    NSKeyDownMask,
    NSFont,
    NSString,
    NSForegroundColorAttributeName,
    NSFontAttributeName,
    NSDictionary,
)
from Quartz import CGRectMake, kCGScreenSaverWindowLevel

from grid import NodeEdgeGrid
from config import CANVAS_TOP_LEFT_X, CANVAS_TOP_LEFT_Y, CANVAS_W, CANVAS_H, GRID_ON_STARTUP

from styles import (
    GRID_LINE_WIDTH, GRID_LINE_COLOR, GRID_FONT_SIZE, GRID_NUMBER_COLOR,
    NODE_LABEL_FONT_SIZE, NODE_LABEL_BG_COLOR, NODE_LABEL_TEXT_COLOR,
    HUD_BG_COLOR, HUD_LABEL_COLOR, HUD_VALUE_COLOR,
    HUD_LABEL_FONT_SIZE, HUD_VALUE_FONT_SIZE, HUD_WIDTH,
    HUD_PADDING, HUD_LINE_HEIGHT, HUD_LABEL_GAP, HUD_SECTION_GAP,
)

latest_data = None
show_grid = GRID_ON_STARTUP

hud_state = {"transcription": None, "reasoning": None, "action": None}

def setup_quit_handler(app):
    NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
        NSKeyDownMask,
        lambda event: (
            app.terminate_(None) if event.charactersIgnoringModifiers() == "q" else None
        ),
    )
    
class OverlayView(NSView):
    def drawRect_(self, rect):
        data = latest_data
        if not data:
            return
        
        if show_grid:
            self.draw_grid(data)
            
        self.draw_node_labels(data)
        self.draw_hud()
        
    def draw_grid(self, data):
        
        vp = data.get("viewport", {})
        
        if not vp:
            return

        zoom = vp.get("zoom", 1)
        vp_x = vp.get("x", 0)
        vp_y = vp.get("y", 0)

        grid_data = NodeEdgeGrid().compute(data)

        number_attrs = NSDictionary.dictionaryWithObjects_forKeys_(
            [NSColor.redColor(), NSFont.boldSystemFontOfSize_(GRID_FONT_SIZE)],
            [NSForegroundColorAttributeName, NSFontAttributeName],
        )

        NSColor.colorWithRed_green_blue_alpha_(*GRID_LINE_COLOR).setStroke()

        for cx in grid_data.x_lines:
            sx = (cx - vp_x) * zoom
            path = NSBezierPath.bezierPath()
            path.setLineWidth_(GRID_LINE_WIDTH)
            path.moveToPoint_((sx, 0))
            path.lineToPoint_((sx, CANVAS_H))
            path.stroke()

        for cy in grid_data.y_lines:
            sy = CANVAS_H - ((cy - vp_y) * zoom)
            path = NSBezierPath.bezierPath()
            path.setLineWidth_(GRID_LINE_WIDTH)
            path.moveToPoint_((0, sy))
            path.lineToPoint_((CANVAS_W, sy))
            path.stroke()

        for cell in grid_data.visible_cells(zoom):
            sx = (cell["cx"] - vp_x) * zoom - 4
            sy = CANVAS_H - ((cell["cy"] - vp_y) * zoom) - 1
            NSString.stringWithString_(str(cell["number"])).drawAtPoint_withAttributes_(
                (sx, sy), number_attrs
            )
            
    def draw_node_labels(self, data):
        
        nodes = data.get("nodes", [])
        vp = data.get("viewport", {})
        if not vp:
            return

        zoom = vp.get("zoom", 1)
        vp_x = vp.get("x", 0)
        vp_y = vp.get("y", 0)

        node_attrs = NSDictionary.dictionaryWithObjects_forKeys_(
            [NSColor.whiteColor(), NSFont.boldSystemFontOfSize_(NODE_LABEL_FONT_SIZE)],
            [NSForegroundColorAttributeName, NSFontAttributeName],
        )

        for node in nodes:
            try:
                screen_x = (node["x"] - vp_x) * zoom
                screen_y = CANVAS_H - ((node["y"] - vp_y) * zoom)

                # label_text = f"{node['name']}  ({node['id']})"
                label_text = f"{node['name']}"
                label_w = len(label_text) * 8

                NSColor.colorWithRed_green_blue_alpha_(*NODE_LABEL_BG_COLOR).setFill()
                NSBezierPath.fillRect_(CGRectMake(screen_x, screen_y, label_w, 17))

                label = NSString.stringWithString_(label_text)
                label.drawAtPoint_withAttributes_(
                    (screen_x + 4, screen_y + 3), node_attrs
                )
            except Exception as e:
                print(f"error drawing node {node.get('name', '?')}: {e}")
                
    def draw_hud(self):

        rows = []
        if hud_state["transcription"]:
            rows.append(("heard", hud_state["transcription"]))
        if hud_state["reasoning"]:
            rows.append(("thinking", hud_state["reasoning"]))
        if hud_state["action"]:
            rows.append(("did", hud_state["action"]))

        if not rows:
            return

        row_h = HUD_LINE_HEIGHT * 2 + HUD_LABEL_GAP + HUD_SECTION_GAP
        box_h = HUD_PADDING * 2 + len(rows) * row_h - HUD_SECTION_GAP
 
        NSColor.colorWithRed_green_blue_alpha_(*HUD_BG_COLOR).setFill()
        NSBezierPath.fillRect_(CGRectMake(HUD_PADDING, HUD_PADDING, HUD_WIDTH, box_h))

        label_attrs = NSDictionary.dictionaryWithObjects_forKeys_(
            [
                NSColor.colorWithRed_green_blue_alpha_(*HUD_LABEL_COLOR),
                NSFont.monospacedSystemFontOfSize_weight_(HUD_LABEL_FONT_SIZE, 0),
            ],
            [NSForegroundColorAttributeName, NSFontAttributeName],
        )
        value_attrs = NSDictionary.dictionaryWithObjects_forKeys_(
            [
                NSColor.colorWithRed_green_blue_alpha_(*HUD_VALUE_COLOR),
                NSFont.monospacedSystemFontOfSize_weight_(HUD_VALUE_FONT_SIZE, 0),
            ],
            [NSForegroundColorAttributeName, NSFontAttributeName],
        )

        cursor_y = HUD_PADDING + box_h - HUD_PADDING - HUD_LINE_HEIGHT
        for label, value in rows:
            NSString.stringWithString_(label.upper()).drawAtPoint_withAttributes_(
                (HUD_PADDING * 2, cursor_y), label_attrs
            )
            cursor_y -= HUD_LINE_HEIGHT + HUD_LABEL_GAP
            display_value = value if len(value) < 80 else value[:78] + "..."
            NSString.stringWithString_(display_value).drawAtPoint_withAttributes_(
                (HUD_PADDING * 2, cursor_y), value_attrs
            )
            cursor_y -= HUD_LINE_HEIGHT + HUD_SECTION_GAP
            
            
            
def ws_listener(view):
    async def listen():
        global latest_data, show_grid, grid_density
        async with websockets.connect(
            "ws://localhost:8000/ws", ping_interval=20, ping_timeout=10
            # pings are used to keep the overlay alive
        ) as ws:

            print("Overlay connected to backend")
            while True:
                data = json.loads(await ws.recv())

                # User Data 
                if "command" in data:
                    cmd = data["command"]
                    
                    # Grid commands
                    if cmd.get("type") == "grid":
                        if cmd.get("action") == "show":
                            show_grid = True
                        elif cmd.get("action") == "hide":
                            show_grid = False
                        view.performSelectorOnMainThread_withObject_waitUntilDone_(
                            "setNeedsDisplay:", True, False
                        )
                        
                    # HUD commands
                    if cmd.get("type") == "hud":
                        hud_state["transcription"] = cmd.get("transcription")
                        hud_state["reasoning"] = cmd.get("reasoning")
                        hud_state["action"] = cmd.get("action")

                        view.performSelectorOnMainThread_withObject_waitUntilDone_(
                            "setNeedsDisplay:", True, False
                        )
                        
                # Plugin data 
                if "nodes" in data:
                    latest_data = data
                    view.performSelectorOnMainThread_withObject_waitUntilDone_(
                        "setNeedsDisplay:", True, False
                    )

    asyncio.run(listen())
    
if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(0)

    screen = NSScreen.screens()[0].frame()
    w = screen.size.width
    h = screen.size.height

    print(f"screen: {w} x {h}")

    window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
        CGRectMake(
            CANVAS_TOP_LEFT_X,
            h - CANVAS_TOP_LEFT_Y - CANVAS_H,
            CANVAS_W,
            CANVAS_H,
        ),
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered,
        False,
    )
    window.setLevel_(kCGScreenSaverWindowLevel)
    window.setBackgroundColor_(NSColor.colorWithRed_green_blue_alpha_(0, 0, 0, 0))
    window.setOpaque_(False)
    window.setIgnoresMouseEvents_(True)
    window.setHidesOnDeactivate_(False)

    view = OverlayView.alloc().initWithFrame_(CGRectMake(0, 0, w, h))
    window.setContentView_(view)
    window.orderFrontRegardless()

    # start WebSocket listener in background thread
    listener = threading.Thread(target=ws_listener, args=(view,), daemon=True)
    listener.start()

    setup_quit_handler(app)
    print("overlay running - press q to quit")
    app.run()