import json
import queue
import threading
import time

import websocket
from dotenv import load_dotenv
from openai import OpenAI

import random

from config import (
    MAX_HISTORY, MODEL, REASONING_MODEL, VOICE_LABELS, TRANSCRIBER, LISTENING_ON_STARTUP,
    GRID_MODE, GRID_ALIGNMENT_SUBDIVISIONS, GRID_ALIGNMENT_SUBDIVISIONS_MAX,
    GRID_ALIGNMENT_SUBDIVISIONS_MIN, GRID_PRECISION_CELL_SIZES, GRID_PRECISION_DEFAULT_INDEX,
)

from command_processing import regex_command_processing
from command_descriptions import describe
from command_dispatch import dispatch_structured_command

load_dotenv()
client = OpenAI()

with open("system_prompt.txt") as f:
    SYSTEM_PROMPT = f.read()

history = []          # lean: layer names + command only — used for normal LLM calls
detailed_history = [] # rich: full canvas state per turn — used for undo LLM fallback
canvas_state = {}
text_queue = queue.Queue()  # input sources put text here - thread safe

grid_mode = GRID_MODE
grid_subdivisions = GRID_ALIGNMENT_SUBDIVISIONS
grid_precision_index = GRID_PRECISION_DEFAULT_INDEX

sleeping = False  # start awake

WAKE_WORDS = ("hey figma", "wake up figma")
SLEEP_WORDS = ("sleep", "goodbye figma", "stop listening")

if TRANSCRIBER == "deepgram":
    from transcribers import DeepgramTranscriber
    transcriber = DeepgramTranscriber()
elif TRANSCRIBER == "deepgram_streaming":
    from transcribers import DeepgramStreamingTranscriber
    transcriber = DeepgramStreamingTranscriber()
else:
    raise ValueError(f"unknown transcriber: {TRANSCRIBER}")

assert transcriber is not None
transcriber.set_listening(LISTENING_ON_STARTUP)

ws = None
labelled = True

# UNDO SNAPSHOTS

previous_viewport = None      # {x, y, zoom}
previous_node = None          # {name, x, y, width, height}
previous_selection = None     # [list of node names]
previous_overlay = None       # {grid_mode, grid_subdivisions, grid_precision_index}
last_snapshot_type = None     # "viewport", "node", "selection", or "overlay"


def push_viewport_snapshot():
    global previous_viewport, last_snapshot_type
    vp = canvas_state.get("viewport")
    if vp:
        # viewport x/y is top-left of bounds — convert to center for set_viewport
        center_x = vp["x"] + vp["width"] / 2
        center_y = vp["y"] + vp["height"] / 2
        previous_viewport = {"x": center_x, "y": center_y, "zoom": vp["zoom"]}
        last_snapshot_type = "viewport"
        print(f"[UNDO] viewport snapshot: center=({center_x:.1f}, {center_y:.1f}) zoom={vp['zoom']:.2f}")
    else:
        print("[UNDO] no viewport in canvas_state")


def push_node_snapshot(name):
    global previous_node, last_snapshot_type
    nodes = canvas_state.get("nodes", [])
    for n in nodes:
        if n["name"].lower() == name.lower():
            previous_node = {"name": n["name"], "x": n["x"], "y": n["y"], "width": n["width"], "height": n["height"]}
            last_snapshot_type = "node"
            return


def push_selection_snapshot(names):
    global previous_selection, last_snapshot_type
    previous_selection = list(names) if names else []
    last_snapshot_type = "selection"


def push_overlay_snapshot():
    global previous_overlay, last_snapshot_type
    previous_overlay = {
        "grid_mode": grid_mode,
        "grid_subdivisions": grid_subdivisions,
        "grid_precision_index": grid_precision_index,
    }
    last_snapshot_type = "overlay"


# WEBSOCKETS


def on_ws_message(ws_app, raw):
    global canvas_state, labelled
    data = json.loads(raw)

    if "nodes" in data:
        canvas_state = data
        print(
            f"canvas updated: {len(data['nodes'])} nodes, viewport x={data['viewport']['x']:.1f} y={data['viewport']['y']:.1f}"
        )

        if not labelled and canvas_state.get("nodes"):
            label_nodes()
            labelled = True


def ws_worker():
    global ws
    ws = websocket.WebSocketApp(
        "ws://localhost:8000/ws",
        on_message=on_ws_message,
        on_open=lambda ws: print("pipeline connected to backend"),
    )
    ws.run_forever(ping_interval=20, ping_timeout=10)


def send_command(json_data):
    if ws and ws.sock and ws.sock.connected:
        ws.send(json.dumps({"command": json_data}))
    else:
        print("ws not connected, command dropped")


# LABELLING


def label_nodes():
    nodes = canvas_state.get("nodes", [])
    if not nodes:
        print("no nodes visible")
        return None

    shuffled = random.sample(VOICE_LABELS, len(nodes))
    mapping = {label: node for label, node in zip(shuffled, nodes)}

    for label, node in mapping.items():
        send_command(
            {
                "level": "figma",
                "type": "rename",
                "query": node["name"],
                "name": label,
            }
        )
    print(f"labelled {len(mapping)} nodes")


# PARSING


def parse_output(text_out):
    try:
        return json.loads(text_out)
    except json.JSONDecodeError:
        print(f"invalid json, skipping: {text_out}")
        return None


# HUD


def send_hud(transcription, reasoning=None, action=None):
    send_command(
        {
            "level": "system",
            "type": "hud",
            "transcription": transcription,
            "reasoning": reasoning,
            "action": action,
        }
    )


# LLM


def llm_command_processing(text):
    layer_names = [n["name"] for n in canvas_state.get("nodes", [])]
    lean_content = f"Layer names: {layer_names}\n\nCommand: {text}. Respond in JSON"
    rich_content = f"Layer names: {layer_names}\nCanvas state: {canvas_state}\n\nCommand: {text}. Respond in JSON"

    history.append({"role": "user", "content": lean_content})
    detailed_history.append({"role": "user", "content": rich_content})

    response = client.responses.create(
        model=MODEL,
        instructions=SYSTEM_PROMPT,
        input=history,
        temperature=0,
        text={"format": {"type": "json_object"}},
    )

    reply = response.output_text.strip()
    history.append({"role": "assistant", "content": reply})
    detailed_history.append({"role": "assistant", "content": reply})

    if len(history) > MAX_HISTORY:
        history[:] = history[-MAX_HISTORY:]
    if len(detailed_history) > MAX_HISTORY:
        detailed_history[:] = detailed_history[-MAX_HISTORY:]

    print(f"\nllm: {reply}\n")
    return reply


# UNDO


VIEWPORT_COMMAND_TYPES = ("focus_object", "zoom_fit", "zoom", "pan")
NODE_COMMAND_TYPES = ("move", "move_absolute", "move_to_cell", "move_to_cell_edge",
                      "move_edge_to_cell", "move_by_pixels", "move_edge_by_pixels",
                      "resize_scale", "resize_delta", "resize_edge_to_cell")
SELECTION_COMMAND_TYPES = ("select",)


def handle_undo(text):
    if last_snapshot_type == "node" and previous_node:
        send_command({"level": "figma", "type": "move_absolute", "query": previous_node["name"], "x": previous_node["x"], "y": previous_node["y"]})
        send_command({"level": "figma", "type": "resize_absolute", "query": previous_node["name"], "width": previous_node["width"], "height": previous_node["height"]})
        send_hud(transcription=text, action=describe({"type": "undo", "kind": "node", "target": previous_node["name"]}))

    elif last_snapshot_type == "viewport" and previous_viewport:
        send_command({"level": "figma", "type": "set_viewport", "x": previous_viewport["x"], "y": previous_viewport["y"], "zoom": previous_viewport["zoom"]})
        send_hud(transcription=text, action=describe({"type": "undo", "kind": "viewport"}))

    elif last_snapshot_type == "selection" and previous_selection is not None:
        send_command({"level": "figma", "type": "select", "query": previous_selection})
        send_hud(transcription=text, action=describe({"type": "undo", "kind": "selection"}))

    elif last_snapshot_type == "overlay" and previous_overlay:
        global grid_mode, grid_subdivisions, grid_precision_index
        grid_mode = previous_overlay["grid_mode"]
        grid_subdivisions = previous_overlay["grid_subdivisions"]
        grid_precision_index = previous_overlay["grid_precision_index"]
        cell_size = GRID_PRECISION_CELL_SIZES[grid_precision_index]
        if grid_mode == "alignment":
            send_command({"level": "system", "type": "grid", "action": "mode", "mode": "alignment", "subdivisions": grid_subdivisions})
        else:
            send_command({"level": "system", "type": "grid", "action": "mode", "mode": "precision", "cell_size": cell_size})
        send_hud(transcription=text, action=describe({"type": "undo", "kind": "overlay"}))

    else:
        send_hud(transcription=text, action=describe({"type": "undo"}))


# GRID


def handle_grid_command(cmd, text):
    global grid_mode, grid_subdivisions, grid_precision_index
    action = cmd.get("action")

    push_overlay_snapshot()  # snapshot before any state changes

    if action == "mode_alignment":
        grid_mode = "alignment"
        send_command({"level": "system", "type": "grid", "action": "mode", "mode": "alignment", "subdivisions": grid_subdivisions})
        send_hud(transcription=text, action=describe({"type": "grid", "action": "mode_alignment"}))

    elif action == "mode_precision":
        grid_mode = "precision"
        cell_size = GRID_PRECISION_CELL_SIZES[grid_precision_index]
        send_command({"level": "system", "type": "grid", "action": "mode", "mode": "precision", "cell_size": cell_size})
        send_hud(transcription=text, action=describe({"type": "grid", "action": "mode_precision"}))

    elif action == "detail_increase":
        if grid_mode == "alignment":
            grid_subdivisions = min(grid_subdivisions + 1, GRID_ALIGNMENT_SUBDIVISIONS_MAX)
            send_command({"level": "system", "type": "grid", "action": "mode", "mode": "alignment", "subdivisions": grid_subdivisions})
            send_hud(transcription=text, action=describe({"type": "grid", "action": "detail_increase", "value": grid_subdivisions}))
        else:
            grid_precision_index = min(grid_precision_index + 1, len(GRID_PRECISION_CELL_SIZES) - 1)
            cell_size = GRID_PRECISION_CELL_SIZES[grid_precision_index]
            send_command({"level": "system", "type": "grid", "action": "mode", "mode": "precision", "cell_size": cell_size})
            send_hud(transcription=text, action=describe({"type": "grid", "action": "detail_increase", "value": cell_size}))

    elif action == "detail_decrease":
        if grid_mode == "alignment":
            grid_subdivisions = max(grid_subdivisions - 1, GRID_ALIGNMENT_SUBDIVISIONS_MIN)
            send_command({"level": "system", "type": "grid", "action": "mode", "mode": "alignment", "subdivisions": grid_subdivisions})
            send_hud(transcription=text, action=describe({"type": "grid", "action": "detail_decrease", "value": grid_subdivisions}))
        else:
            grid_precision_index = max(grid_precision_index - 1, 0)
            cell_size = GRID_PRECISION_CELL_SIZES[grid_precision_index]
            send_command({"level": "system", "type": "grid", "action": "mode", "mode": "precision", "cell_size": cell_size})
            send_hud(transcription=text, action=describe({"type": "grid", "action": "detail_decrease", "value": cell_size}))

    else:
        send_command(cmd)
        send_hud(transcription=text, action=describe(cmd))


# COMMAND WORKER


def snapshot_for_command(cmd):
    """Push node or selection snapshot before a command executes."""
    t = cmd.get("type")
    if t in NODE_COMMAND_TYPES:
        name = cmd.get("node_name") or cmd.get("query")
        if name:
            push_node_snapshot(name)
    elif t in SELECTION_COMMAND_TYPES:
        current_selection = [n["name"] for n in canvas_state.get("nodes", []) if n.get("selected")]
        push_selection_snapshot(current_selection)


def command_worker(text):
    global sleeping, history, detailed_history, grid_mode, grid_subdivisions, grid_precision_index
    t = text.lower().strip()

    if any(w in t for w in WAKE_WORDS):
        sleeping = False
        send_hud(transcription=text, action="listening on")
        return
    if any(w in t for w in SLEEP_WORDS):
        sleeping = True
        send_hud(transcription=text, action="listening off")
        return
    if sleeping:
        return  # silently ignore everything else

    send_hud(transcription=text)

    # step 1 - regex
    fixed = regex_command_processing(
        text, canvas_state, grid_mode, grid_subdivisions,
        GRID_PRECISION_CELL_SIZES[grid_precision_index]
    )

    if fixed == "LABEL_NODES":
        label_nodes()
        return

    if isinstance(fixed, dict) and fixed.get("type") == "grid":
        handle_grid_command(fixed, text)
        return

    if isinstance(fixed, dict) and fixed.get("type") == "undo":
        handle_undo(text)
        return

    # snapshot viewport after undo check so "undo" doesn't overwrite the previous state
    push_viewport_snapshot()

    if fixed:
        if fixed.get("error"):
            send_hud(transcription=text, action=fixed["error"])
            return
        snapshot_for_command(fixed)
        send_command(fixed)
        send_hud(transcription=text, action=describe(fixed))
        layer_names = [n["name"] for n in canvas_state.get("nodes", [])]
        reply = json.dumps(fixed)
        history.append({"role": "user", "content": f"Layer names: {layer_names}\n\nCommand: {text}. Respond in JSON"})
        history.append({"role": "assistant", "content": reply})
        detailed_history.append({"role": "user", "content": f"Layer names: {layer_names}\nCanvas state: {canvas_state}\n\nCommand: {text}. Respond in JSON"})
        detailed_history.append({"role": "assistant", "content": reply})
        if len(history) > MAX_HISTORY:
            history[:] = history[-MAX_HISTORY:]
        if len(detailed_history) > MAX_HISTORY:
            detailed_history[:] = detailed_history[-MAX_HISTORY:]
        return

    # step 2 - LLM
    send_hud(transcription=text, reasoning="reasoning...")
    text_out = llm_command_processing(text)
    cmd = parse_output(text_out)

    if cmd is None:
        send_hud(transcription=text, action="could not parse response")
        return

    # step 3 - route by level
    level = cmd.get("level")

    if level == "python":
        snapshot_for_command(cmd)
        result = dispatch_structured_command(
            cmd, canvas_state, grid_mode, grid_subdivisions,
            GRID_PRECISION_CELL_SIZES[grid_precision_index]
        )
        if result and not result.get("error"):
            send_command(result)
            send_hud(transcription=text, action=describe(cmd))
        else:
            err = result.get("error") if result else "command failed"
            send_hud(transcription=text, action=err)

    elif level == "figma":
        if cmd.get("type") == "unknown":
            send_hud(transcription=text, action=describe({"type": "not_recognised"}))
        else:
            snapshot_for_command(cmd)
            send_command(cmd)
            send_hud(transcription=text, action=describe(cmd))

    elif level == "system":
        if cmd.get("type") == "grid":
            handle_grid_command(cmd, text)
        else:
            send_command(cmd)
            send_hud(transcription=text, action=describe(cmd))

    else:
        send_hud(transcription=text, action=describe({"type": "not_recognised"}))


def keyboard_worker():
    while True:
        text = input(">> ")
        if text.strip() == "start listening":
            transcriber.set_listening(True)
            print("listening on")
        elif text.strip() == "stop listening":
            transcriber.set_listening(False)
            print("listening off")
        elif text.strip():
            text_queue.put(text.strip())


def dispatcher_worker():
    while True:
        text = text_queue.get()
        if text:
            command_worker(text)


threading.Thread(target=ws_worker, daemon=True).start()
time.sleep(0.5)  # give ws a moment to connect before other workers start

threading.Thread(target=transcriber.start, args=(text_queue,), daemon=True).start()
threading.Thread(target=keyboard_worker, daemon=True).start()
threading.Thread(target=dispatcher_worker, daemon=True).start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("stopped.")