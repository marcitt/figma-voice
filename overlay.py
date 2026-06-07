"""
Overlay for rendering Figma node labels.
"""

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

from config import CANVAS_TOP_LEFT_X, CANVAS_TOP_LEFT_Y, CANVAS_W, CANVAS_H

# latest canvas state from plugin, updated by WebSocket listener
latest_data = None


def setup_quit_handler(app):
    NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
        NSKeyDownMask,
        lambda event: (
            app.terminate_(None) if event.charactersIgnoringModifiers() == "q" else None
        ),
    )


class OverlayView(NSView):
    def drawRect_(self, rect):
        w = self.frame().size.width
        h = self.frame().size.height

        data = latest_data
        if not data:
            return

        self.draw_node_labels(w, h, data)

    def draw_node_labels(self, w, h, data):
        nodes = data.get("nodes", [])
        vp = data.get("viewport", {})
        if not vp:
            return

        zoom = vp.get("zoom", 1)
        vp_x = vp.get("x", 0)
        vp_y = vp.get("y", 0)

        node_attrs = NSDictionary.dictionaryWithObjects_forKeys_(
            [NSColor.whiteColor(), NSFont.boldSystemFontOfSize_(10)],
            [NSForegroundColorAttributeName, NSFontAttributeName],
        )

        for node in nodes:
            try:
                screen_x = (node["x"] - vp_x) * zoom
                screen_y = CANVAS_H - ((node["y"] - vp_y) * zoom)

                label_text = f"{node['name']}  ({node['id']})"
                label_w = len(label_text) * 6

                NSColor.colorWithRed_green_blue_alpha_(0.5, 0.5, 0.5, 0.8).setFill()
                NSBezierPath.fillRect_(CGRectMake(screen_x, screen_y, label_w, 17))

                label = NSString.stringWithString_(label_text)
                label.drawAtPoint_withAttributes_(
                    (screen_x + 4, screen_y + 3), node_attrs
                )
            except Exception as e:
                print(f"error drawing node {node.get('name', '?')}: {e}")


def ws_listener(view):
    async def listen():
        global latest_data
        async with websockets.connect("ws://localhost:8000/ws") as ws:
            print("Overlay connected to backend")
            while True:
                data = json.loads(await ws.recv())
                print(f"Received data: {len(data.get('nodes', []))} nodes")  # add this
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
