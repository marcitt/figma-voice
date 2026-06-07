import json
import threading
import subprocess
import atexit
import requests
import pyautogui
from dotenv import load_dotenv
from openai import OpenAI
from system_prompt import get_system_prompt
import time

import websocket

load_dotenv()
client = OpenAI()

history = []
MAX_HISTORY = 10
canvas_state = {}

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


def llm_process_command(text):
    global history

    history.append({"role": "user", "content": text})
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[{"role": "system", "content": "hello"}, *history],
    )

    reply = response.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})
    print(f"\ncommand: {reply}\n")
    return reply


def command_thread(text):

    # check if the transcribed text matches the fixed gramamr
    fixed_command = handle_fixed_grammar(text)

    if fixed_command:
        send_command(fixed_command)
        return

    # if the trasncribed text doesn't match the fixed grammar - process it with an LLM
    text_out = llm_process_command(text)

    try:
        json_data = json.loads(text_out)
    except json.JSONDecodeError:
        print(f"invalid json, skipping: {text_out}")
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
