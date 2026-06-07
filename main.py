from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# track connected clients
clients = []

latest_state = None


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global latest_state

    await websocket.accept()
    clients.append(websocket)
    print(f"Client connected — {len(clients)} total")

    # send latest state to new client immediately
    if latest_state:
        await websocket.send_json(latest_state)

    try:
        while True:
            data = await websocket.receive_json()
            if "nodes" in data:
                latest_state = data
            print(f"Received data, broadcasting to {len(clients) - 1} other clients")
            for client in clients:
                if client != websocket:
                    await client.send_json(data)
    except WebSocketDisconnect:
        clients.remove(websocket)
        print(f"Client disconnected — {len(clients)} total")
