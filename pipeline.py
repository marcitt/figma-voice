import json
import threading
import subprocess
import atexit
import requests
import pyautogui
from dotenv import load_dotenv
from openai import OpenAI
import time

import websocket

FAST_MODEL = "gpt-5-nano"
REASONING_MODEL = "gpt-5-mini"
# REASONING_MODEL = "gpt-4o-mini"

load_dotenv()
client = OpenAI()

history = []
MAX_HISTORY = 10
canvas_state = {}

with open("system_prompt_fast.txt") as f:
    SYSTEM_PROMPT_FAST = f.read()

with open("system_prompt_reasoning.txt") as f:
    SYSTEM_PROMPT_REASONING = f.read()

# global
ws = None


def on_ws_message(ws_app, raw):
    global canvas_state
    data = json.loads(raw)

    # updates canvas state when new data is sent from the blugin
    if "nodes" in data:
        canvas_state = data


#  creates a WebSocketApp - persistent connection to the backend - listens for incoming messages
def ws_receive_thread():
    global ws
    ws = websocket.WebSocketApp(
        "ws://localhost:8000/ws",
        on_message=on_ws_message,
        on_open=lambda ws: print("pipeline connected to backend"),
    )
    ws.run_forever()


# sends commands to the backend - the backend broadcasts it to all other connected clients
def send_command(json_data):
    if (
        ws and ws.sock and ws.sock.connected
    ):  # guard (please look into this in a bit more detail)
        ws.send(json.dumps({"command": json_data}))
    else:
        print("ws not connected, command dropped")


def handle_fixed_grammar(text):
    text_lower = text.lower()

    if "show overlay" in text_lower or "open overlay" in text_lower:
        return {"level": "system", "type": "overlay", "action": "show"}

    if "hide overlay" in text_lower or "close overlay" in text_lower:
        return {"level": "system", "type": "overlay", "action": "hide"}

    if "toggle overlay" in text_lower:
        return {"level": "system", "type": "overlay", "action": "toggle"}


def llm_process_command(
    text, model, include_canvas=False, effort="low", system_prompt=SYSTEM_PROMPT_FAST
):
    global history

    layer_names = [n["name"] for n in canvas_state.get("nodes", [])]

    if include_canvas:
        content = f"Canvas state: {canvas_state}\n\nCommand: {text}. Respond in JSON"
    else:
        content = f"Layer names: {layer_names}\n\nCommand: {text}. Respond in JSON"

    history.append({"role": "user", "content": content})
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    response = client.responses.create(
        model=model,
        instructions=system_prompt,
        reasoning={"effort": effort},
        input=history,
        text={"format": {"type": "json_object"}},
    )

    reply = response.output_text.strip()
    history.append({"role": "assistant", "content": reply})
    print(f"\ncommand: {reply}\n")
    return reply


def parse_output(text_out):
    try:
        json_data = json.loads(text_out)
    except json.JSONDecodeError:
        print(f"invalid json, skipping: {text_out}")
        return None

    if "REASONING" in json_data:
        print(f"\nreasoning: {json_data['REASONING']}\n")

    if "COMMAND" in json_data:
        json_data = json_data["COMMAND"]

    return json_data


def command_thread(text):
    fixed = handle_fixed_grammar(text)
    if fixed:
        send_command(fixed)
        return

    # ROUTING:
    # text_out = llm_process_command(text, model=FAST_MODEL, include_canvas=False)

    # json_data = parse_output(text_out)
    # if json_data is None:
    #     return

    # effort = json_data.pop("effort", "low")

    # if json_data.get("route") == "complex":
    #     print(f"routing to complex (effort: {effort})...")
    #     text_out = llm_process_command(
    #         text,
    #         model=REASONING_MODEL,
    #         include_canvas=True,
    #         effort=effort,
    #         system_prompt=SYSTEM_PROMPT_REASONING,
    #     )
    #     json_data = parse_output(text_out)
    #     if json_data is None:
    #         return

    # WITHOUT ROUTING:
    text_out = llm_process_command(
        text,
        model=REASONING_MODEL,
        include_canvas=True,
        system_prompt=SYSTEM_PROMPT_REASONING,
    )
    json_data = parse_output(text_out)
    if json_data is None:
        return

    send_command(json_data)


ws_thread = threading.Thread(target=ws_receive_thread, daemon=True)
ws_thread.start()
time.sleep(0.5)

try:
    while True:
        text = input(">> ")
        if text.strip():
            t = threading.Thread(target=command_thread, args=(text.strip(),))
            t.start()

except KeyboardInterrupt:
    print("stopped.")
