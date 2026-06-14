import json
import logging
import queue
import threading
import time

import websocket
from dotenv import load_dotenv
from openai import OpenAI

import random

from transcribers import DeepgramStreamingTranscriber
from config import MAX_HISTORY, MODEL, VOICE_LABELS

from command_processing import regex_command_processing
from command_descriptions import describe
from command_dispatch import dispatch_structured_command

from spatial_commands import (
    move_to_cell,
    move_to_cell_edge,
    move_edge_to_cell,
    resize_edge_to_cell,
    move_edge_by_pixels,
    move_by_pixels,
)

load_dotenv()
client = OpenAI()

with open("system_prompt.txt") as f:
    SYSTEM_PROMPT = f.read()

history = []
canvas_state = {}
text_queue = queue.Queue()  # input sources put text here - thread safe
transcriber = DeepgramStreamingTranscriber()

ws = None
labelled = False

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
        text={"format": {"type": "json_object"}},
    )

    reply = response.output_text.strip()
    history.append({"role": "assistant", "content": reply})
    print(f"\nllm: {reply}\n")
    return reply


def command_worker(text):
    global history

    send_hud(transcription=text)

    # step 1 - regex
    fixed = regex_command_processing(text, canvas_state)

    if fixed == "LABEL_NODES":
        label_nodes()
        return

    if fixed:
        if fixed.get("error"):
            send_hud(transcription=text, action=fixed["error"])
            return
        send_command(fixed)
        send_hud(transcription=text, action=text)
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
        result = dispatch_structured_command(cmd, canvas_state)
        if result and not result.get("error"):
            send_command(result)
            send_hud(transcription=text, action=describe(cmd))
        else:
            err = result.get("error") if result else "command failed"
            send_hud(transcription=text, action=err)

    elif level == "figma":
        if cmd.get("type") == "unknown":
            print(f"not understood: '{text}'")
            send_hud(transcription=text, action="not recognised")
        else:
            send_command(cmd)
            send_hud(transcription=text, action=describe(cmd))

    elif level == "system":
        send_command(cmd)
        send_hud(transcription=text, action=describe(cmd))

    else:
        print(f"unrecognised level: {level}")
        send_hud(transcription=text, action=f"unrecognised level: {level}")


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
