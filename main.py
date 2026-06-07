from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# browsers have same-origin policy rule
# a webpage can only make requests to the same domain it is served from
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow requests from any domain
    allow_methods=["*"],  # allow any HTTP method (GET, POST etc)
    allow_headers=["*"],  # allow any headers
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Plugin connected")
    while True:
        data = await websocket.receive_json()
        print(len(data))
        print("end of data")
