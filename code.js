figma.showUI(__html__, { width: 100, height: 70 });

/**
 * Command Message Types
 *
 * select        { type: "select",        query: string[] }
 * focus_object  { type: "focus_object",  query: string | string[] }
 * zoom          { type: "zoom",          zoom_delta: number }
 * pan           { type: "pan",           dx: number, dy: number }
 * move          { type: "move",          query: string, dx: number, dy: number }
 * move_absolute { type: "move_absolute", query: string, x: number, y: number }
 * resize_scale  { type: "resize_scale",  query: string, factor: number }
 * resize_delta  { type: "resize_delta",  query: string, dw: number, dh: number }
 * create_rect   { type: "create_rect",   x: number, y: number, width?: number, height?: number }
 * create_text   { type: "create_text",   x: number, y: number, content?: string }
 * zoom_fit      { type: "zoom_fit" }
* group         { type: "group",         query: string[] }
 * ungroup       { type: "ungroup",       query: string }
 * bring_forward { type: "bring_forward", query: string }
 * send_backward { type: "send_backward", query: string }
 */

/**
 * Example Commands
 *
 * select        { "type": "select",        "query": ["Rectangle 1"] }
 * focus_object  { "type": "focus_object",  "query": "Rectangle 1" } or { "type": "focus_object", "query": ["Rectangle 1", "Rectangle 2"] }
 * zoom          { "type": "zoom",          "zoom_delta": 0.5 }
 * pan           { "type": "pan",           "dx": 100, "dy": 0 }
 * move          { "type": "move",          "query": "Rectangle 1", "dx": 200, "dy": 0 }
 * move_absolute { "type": "move_absolute", "query": "Rectangle 1", "x": 100, "y": 200 }
 * resize_scale  { "type": "resize_scale",  "query": "Rectangle 1", "factor": 2 }
 * resize_delta  { "type": "resize_delta",  "query": "Rectangle 1", "dw": 50, "dh": 0 }
 * create_rect   { "type": "create_rect",   "x": 0, "y": 0, "width": 200, "height": 100 }
 * create_text   { "type": "create_text",   "x": 0, "y": 0, "content": "Hello" }
 * zoom_fit      { "type": "zoom_fit" }
 * group         { "type": "group",         "query": ["Rectangle 1", "Rectangle 2"] }
 * ungroup       { "type": "ungroup",       "query": "Group 1" }
 * bring_forward { "type": "bring_forward", "query": "Rectangle 1" }
 * send_backward { "type": "send_backward", "query": "Rectangle 1" }
 */


// listens for messages from ui.html -> these get passed to handleCommand
figma.ui.onmessage = async (msg) => {
    await handleCommand(msg);
};

async function handleCommand(msg) {

    // switch gives simpler implementation than list of if/else statements
    switch (msg.type) {

        case "select": {
            const nodes = msg.query
                // maps over the array
                .map(q => figma.currentPage.findOne(n => n.name === q))
                .filter(Boolean);
            figma.currentPage.selection = nodes;
            break;
        }

        case "focus_object": {
            if (Array.isArray(msg.query)) {
                const nodes = msg.query
                    .map(q => figma.currentPage.findOne(n => n.name === q))
                    .filter(Boolean);
                if (nodes.length > 0) figma.viewport.scrollAndZoomIntoView(nodes);
                break;
            }
            const node = figma.currentPage.findOne(n => n.name === msg.query);
            if (node && node.absoluteBoundingBox) {
                const { x, y, width, height } = node.absoluteBoundingBox;
                // viewport.bounds is in viewport pixels, absoluteBoundingBox in canvas units
                // multiply by current zoom to account for the mismatch
                const zoom = Math.min(
                    (figma.viewport.bounds.width / width) * figma.viewport.zoom,
                    (figma.viewport.bounds.height / height) * figma.viewport.zoom
                );
                // reduce by 50% to add padding - scrollAndZoomIntoView was unreliable
                // as it accounts for Figma UI panels making objects appear smaller
                figma.viewport.zoom = zoom - (zoom * 0.5);
                figma.viewport.center = { x: x + width / 2, y: y + height / 2 };
            }
            break;
        }

        case "zoom":
            figma.viewport.zoom = figma.viewport.zoom + msg.zoom_delta;
            break;

        case "pan": {
            const center = figma.viewport.center;
            figma.viewport.center = { x: center.x + msg.dx, y: center.y + msg.dy };
            break;
        }

        case "move": {
            // searches the current page for a node matching the condition
            const node = figma.currentPage.findOne(n => n.name === msg.query);
            if (node) { node.x += msg.dx; node.y += msg.dy; }
            break;
        }

        case "move_absolute": {
            const node = figma.currentPage.findOne(n => n.name === msg.query);
            if (node) { node.x = msg.x; node.y = msg.y; }
            break;
        }

        case "resize_scale": {
            const node = figma.currentPage.findOne(n => n.name === msg.query);
            if (node) node.resize(node.width * msg.factor, node.height * msg.factor);
            break;
        }

        case "resize_delta": {
            const node = figma.currentPage.findOne(n => n.name === msg.query);
            if (node) node.resize(node.width + msg.dw, node.height + msg.dh);
            break;
        }

        case "resize_absolute": {
            const node = figma.currentPage.findOne(n => n.name === msg.query);
            if (node) { node.x = msg.x; node.y = msg.y; node.resize(msg.width, msg.height); }
            break;
        }

        case "create_rect": {
            const rect = figma.createRectangle();
            rect.x = msg.x; rect.y = msg.y;
            rect.resize(msg.width || 100, msg.height || 100);
            figma.currentPage.appendChild(rect);
            break;
        }

        case "create_text": {
            await figma.loadFontAsync({ family: "Inter", style: "Regular" });
            const text = figma.createText();
            text.x = msg.x; text.y = msg.y;
            text.characters = msg.content || "Text";
            figma.currentPage.appendChild(text);
            break;
        }

        case "zoom_fit": {
            const nodes = figma.currentPage.findAll();
            if (nodes.length > 0) figma.viewport.scrollAndZoomIntoView(nodes);
            break;
        }

        case "set_viewport":
            figma.viewport.center = { x: msg.x, y: msg.y };
            figma.viewport.zoom = msg.zoom;
            break;

        case "rename": {
            const node = figma.currentPage.findOne(n => n.name === msg.query);
            if (node) node.name = msg.name;
            break;
        }

        case "group": {
            const nodes = msg.query
                .map(q => figma.currentPage.findOne(n => n.name === q))
                .filter(Boolean);
            if (nodes.length > 0) figma.group(nodes, figma.currentPage);
            break;
        }

        case "ungroup": {
            const node = figma.currentPage.findOne(n => n.name === msg.query);
            if (node && node.type === "GROUP") figma.ungroup(node);
            break;
        }

        case "bring_forward": {
            const node = figma.currentPage.findOne(n => n.name === msg.query);
            if (node) node.parent.insertChild(node.parent.children.indexOf(node) + 1, node);
            break;
        }

        case "send_backward": {
            const node = figma.currentPage.findOne(n => n.name === msg.query);
            if (node) node.parent.insertChild(node.parent.children.indexOf(node) - 1, node);
            break;
        }

        case "undo": {
            const steps = msg.steps || 1;
            for (let i = 0; i < steps; i++) figma.triggerUndo();
            break;
        }

        default:
            console.warn("Unknown command type:", msg.type);
    }
}

function sendData() {
    const vp = figma.viewport.bounds;
    const nodes = figma.currentPage.findAll(n => {
        if (!n.visible || n.locked) return false;
        const bbox = n.absoluteBoundingBox;
        if (!bbox) return false;
        return (
            bbox.x < vp.x + vp.width &&
            bbox.x + bbox.width > vp.x &&
            bbox.y < vp.y + vp.height &&
            bbox.y + bbox.height > vp.y
        );
    });
    const payload = {
        nodes: nodes.map(n => {
            const bbox = n.absoluteBoundingBox;
            return { id: n.id, name: n.name, type: n.type, x: bbox.x, y: bbox.y, width: bbox.width, height: bbox.height };
        }),
        viewport: { x: vp.x, y: vp.y, width: vp.width, height: vp.height, zoom: figma.viewport.zoom }
    };
    figma.ui.postMessage(payload);
}

let sendTimeout = null;
function debouncedSendData() {
    clearTimeout(sendTimeout);
    sendTimeout = setTimeout(sendData, 100);
}

figma.on("documentchange", debouncedSendData);
figma.on("selectionchange", sendData);
figma.on("currentpagechange", sendData);

// poll every 500ms - no native viewport change event in Figma API
let lastViewport = null;
setInterval(() => {
    const vp = figma.viewport;
    const current = `${vp.center.x},${vp.center.y},${vp.zoom}`;
    if (current !== lastViewport) { lastViewport = current; sendData(); }
}, 500);

sendData();