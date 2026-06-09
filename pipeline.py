import json
import logging
import queue
import threading
import time

import pyautogui
import websocket
from dotenv import load_dotenv
from openai import OpenAI

from transcribers import GoogleTranscriber

from config import REASONING_MODEL, MAX_HISTORY

logging.basicConfig(
    filename="latency.log", level=logging.INFO, format="%(asctime)s %(message)s"
)

load_dotenv()
client = OpenAI()

with open("system_prompt_fast.txt") as f:
    SYSTEM_PROMPT_FAST = f.read()

with open("system_prompt_reasoning.txt") as f:
    SYSTEM_PROMPT_REASONING = f.read()


# STATE

history = []
canvas_state = {}
text_queue = queue.Queue()  # input sources put text here | thread safe

# global
ws = None


def on_ws_message(ws_app, raw):
    global canvas_state
    data = json.loads(raw)

    # updates canvas state when new data is sent from the blugin
    if "nodes" in data:
        canvas_state = data


#  creates a WebSocketApp - persistent connection to the backend - listens for incoming messages
def ws_worker():
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


# COMMANDS THAT MATCH TEMPLATES
def handle_fixed_commands(text):
    text_lower = text.lower()

    if "show overlay" in text_lower or "open overlay" in text_lower:
        return {"level": "system", "type": "overlay", "action": "show"}

    if "hide overlay" in text_lower or "close overlay" in text_lower:
        return {"level": "system", "type": "overlay", "action": "hide"}

    if "toggle overlay" in text_lower:
        return {"level": "system", "type": "overlay", "action": "toggle"}


# FUZZY COMMANDS THAT NEED LLM REASONING
def handle_fuzzy_commands(
    text,
    model,
    system_prompt,
    include_canvas=False,
    effort="low",
):

    global history

    # full context
    if include_canvas:
        content = f"Canvas state: {canvas_state}\n\nCommand: {text}. Respond in JSON"
    else:
        # if less context is included at a minimum the layer names should be supplied
        layer_names = [n["name"] for n in canvas_state.get("nodes", [])]

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


# Mouse control as fallback for UI interactions not possible via Figma API
# These are generally not required - more useful for debugging / testing
# def handle_mouse_command(cmd):
#     action = cmd.get("action")

#     try:
#         if action == "move":
#             x = cmd.get("x")
#             y = cmd.get("y")
#             pyautogui.moveTo(x, y, duration=0.3)

#         elif action == "click":
#             x = cmd.get("x")
#             y = cmd.get("y")
#             pyautogui.click(x, y)

#         elif action == "double_click":
#             x = cmd.get("x")
#             y = cmd.get("y")
#             pyautogui.doubleClick(x, y)

#         elif action == "right_click":
#             x = cmd.get("x")
#             y = cmd.get("y")
#             pyautogui.rightClick(x, y)

#         elif action == "drag":
#             x1 = cmd.get("x1")
#             y1 = cmd.get("y1")
#             x2 = cmd.get("x2")
#             y2 = cmd.get("y2")
#             pyautogui.moveTo(x1, y1)
#             pyautogui.dragTo(x2, y2, duration=0.5)

#         print(f"mouse: {action} at ({cmd.get('x')}, {cmd.get('y')})")

#     except Exception as e:
#         print(f"mouse error: {e}")


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


def command_worker(text):
    fixed = handle_fixed_commands(text)
    if fixed:
        send_command(fixed)
        return

    # ROUTING (removed for now)
    # text_out = handle_fuzzy_commands(text, model=FAST_MODEL, include_canvas=False)

    # json_data = parse_output(text_out)
    # if json_data is None:
    #     return

    # effort = json_data.pop("effort", "low")

    # if json_data.get("route") == "complex":
    #     print(f"routing to complex (effort: {effort})...")
    #     text_out = handle_fuzzy_commands(
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
    text_out = handle_fuzzy_commands(
        text,
        model=REASONING_MODEL,
        include_canvas=True,
        system_prompt=SYSTEM_PROMPT_REASONING,
    )

    json_data = parse_output(text_out)

    if json_data is None:
        return

    send_command(json_data)


# GIL - may be some queries on this


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

            # if you want to spawn a new thread instead
            # threading.Thread(target=command_worker, args=(text,), daemon=True).start()


threading.Thread(target=ws_worker, daemon=True).start()
time.sleep(0.5)  # give ws a moment to connect before other workers start

transcriber = GoogleTranscriber()
# transcriber = FasterWhisperTranscriber()

threading.Thread(target=transcriber.start, args=(text_queue,), daemon=True).start()
threading.Thread(target=keyboard_worker, daemon=True).start()
threading.Thread(target=dispatcher_worker, daemon=True).start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("stopped.")
