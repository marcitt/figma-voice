import json
import queue
import threading
import time

import websocket
from dotenv import load_dotenv
from openai import OpenAI

import random

from config import (
    MAX_HISTORY, MODEL, VOICE_LABELS, TRANSCRIBER, LISTENING_ON_STARTUP,
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

history = []
canvas_state = {}
text_queue = queue.Queue()  # input sources put text here - thread safe

grid_mode = GRID_MODE
grid_subdivisions = GRID_ALIGNMENT_SUBDIVISIONS
grid_precision_index = GRID_PRECISION_DEFAULT_INDEX

sleeping = True  # start asleep

WAKE_WORDS = ("hey figma", "wake up figma")  # trailing comma or multiple items makes it a tuple
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

# WEBSOCKETS


def on_ws_message(ws_app, raw):
    global canvas_state, labelled
    data = json.loads(raw)

    # updates canvas state when new data is sent from the plugin
    if "nodes" in data:
        canvas_state = data
        print(
            f"canvas updated: {len(data['nodes'])} nodes, viewport x={data['viewport']['x']:.1f} y={data['viewport']['y']:.1f}"
        )

        if not labelled and canvas_state.get("nodes"):
            label_nodes()
            labelled = True


#  creates a WebSocketApp - persistent connection to the backend - listens for incoming messages
def ws_worker():
    global ws
    ws = websocket.WebSocketApp(
        "ws://localhost:8000/ws",
        on_message=on_ws_message,
        on_open=lambda ws: print("pipeline connected to backend"),
    )
    ws.run_forever(ping_interval=20, ping_timeout=10)


# sends commands to the backend - the backend broadcasts it to all other connected clients
def send_command(json_data):
    if (
        ws and ws.sock and ws.sock.connected
    ):  # guard (please look into this in a bit more detail)
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

    # send a rename command for each node
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


def llm_command_processing(text, canvas_state, history, model, system_prompt):
    layer_names = [n["name"] for n in canvas_state.get("nodes", [])]
    content = f"Layer names: {layer_names}\n\nCommand: {text}. Respond in JSON"

    history.append({"role": "user", "content": content})

    response = client.responses.create(
        model=model,
        instructions=system_prompt,
        input=history,
        temperature=0,
        text={"format": {"type": "json_object"}},
    )

    reply = response.output_text.strip()
    history.append({"role": "assistant", "content": reply})
    print(f"\nllm: {reply}\n")
    return reply

def handle_grid_command(cmd, text):
    global grid_mode, grid_subdivisions, grid_precision_index
    action = cmd.get("action")

    if action == "mode_alignment":
        grid_mode = "alignment"
        send_command({"level": "system", "type": "grid", "action": "mode", "mode": "alignment", "subdivisions": grid_subdivisions})
        send_hud(transcription=text, action="switched to alignment grid")

    elif action == "mode_precision":
        grid_mode = "precision"
        cell_size = GRID_PRECISION_CELL_SIZES[grid_precision_index]
        send_command({"level": "system", "type": "grid", "action": "mode", "mode": "precision", "cell_size": cell_size})
        send_hud(transcription=text, action="switched to precision grid")

    elif action == "detail_increase":
        if grid_mode == "alignment":
            grid_subdivisions = min(grid_subdivisions + 1, GRID_ALIGNMENT_SUBDIVISIONS_MAX)
            send_command({"level": "system", "type": "grid", "action": "mode", "mode": "alignment", "subdivisions": grid_subdivisions})
            send_hud(transcription=text, action=f"alignment grid detail {grid_subdivisions}")
        else:
            grid_precision_index = min(grid_precision_index + 1, len(GRID_PRECISION_CELL_SIZES) - 1)
            cell_size = GRID_PRECISION_CELL_SIZES[grid_precision_index]
            send_command({"level": "system", "type": "grid", "action": "mode", "mode": "precision", "cell_size": cell_size})
            send_hud(transcription=text, action=f"precision grid cell size {cell_size}")

    elif action == "detail_decrease":
        if grid_mode == "alignment":
            grid_subdivisions = max(grid_subdivisions - 1, GRID_ALIGNMENT_SUBDIVISIONS_MIN)
            send_command({"level": "system", "type": "grid", "action": "mode", "mode": "alignment", "subdivisions": grid_subdivisions})
            send_hud(transcription=text, action=f"alignment grid detail {grid_subdivisions}")
        else:
            grid_precision_index = max(grid_precision_index - 1, 0)
            cell_size = GRID_PRECISION_CELL_SIZES[grid_precision_index]
            send_command({"level": "system", "type": "grid", "action": "mode", "mode": "precision", "cell_size": cell_size})
            send_hud(transcription=text, action=f"precision grid cell size {cell_size}")

    else:
        # show/hide/toggle pass straight through
        send_command(cmd)
        send_hud(transcription=text, action=describe(cmd))


def command_worker(text):
    global sleeping, history, grid_mode, grid_subdivisions, grid_precision_index
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

    if fixed:
        if fixed.get("error"):
            send_hud(transcription=text, action=fixed["error"])
            return
        send_command(fixed)
        send_hud(transcription=text, action=describe(fixed))
        history.append({"role": "user", "content": f"Command: {text}. Respond in JSON"})
        history.append({"role": "assistant", "content": json.dumps(fixed)})
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]
        return

    # step 2 - LLM
    send_hud(transcription=text, reasoning="reasoning...")
    text_out = llm_command_processing(
        text, canvas_state, history, model=MODEL, system_prompt=SYSTEM_PROMPT
    )
    cmd = parse_output(text_out)

    if cmd is None:
        send_hud(transcription=text, action="could not parse response")
        return

    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    # step 3 - route by level
    level = cmd.get("level")

    if level == "python":
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
            send_hud(transcription=text, action="not recognised")
        else:
            send_command(cmd)
            send_hud(transcription=text, action=describe(cmd))

    elif level == "system":
        if cmd.get("type") == "grid":
            handle_grid_command(cmd, text)
        else:
            send_command(cmd)
            send_hud(transcription=text, action=describe(cmd))

    else:
        send_hud(transcription=text, action="not recognised")


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

# pyautogui.moveTo(100, 150)
# pyautogui.click()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("stopped.")