from fastapi import FastAPI, WebSocket, Request, Form, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Dict, List, Set
import uvicorn

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class ConnectionManager:
    def __init__(self):
        # Store WebSocket connections for each room
        self.active_connections: Dict[str, List[WebSocket]] = {
            "general": [],
            "random": [],
            "tech": [],
            "music": []
        }
        # Store active users in each room
        self.active_users: Dict[str, Set[str]] = {
            "general": set(),
            "random": set(),
            "tech": set(),
            "music": set()
        }
        # Store user-room mapping
        self.users: Dict[str, str] = {}  # username: room

    async def connect(self, websocket: WebSocket, room: str, username: str):
        await websocket.accept()
        self.active_connections[room].append(websocket)
        self.active_users[room].add(username)
        # Broadcast updated user list to all clients in the room
        await self.broadcast_user_list(room)
        # Send system message about new user
        await self.broadcast(f"{username} has joined the chat", room, "System")

    def disconnect(self, websocket: WebSocket, room: str, username: str):
        self.active_connections[room].remove(websocket)
        self.active_users[room].remove(username)
        if username in self.users:
            del self.users[username]

    async def broadcast(self, message: str, room: str, sender: str):
        for connection in self.active_connections[room]:
            await connection.send_text(f"{sender}: {message}")

    async def broadcast_user_list(self, room: str):
        user_list = list(self.active_users[room])
        for connection in self.active_connections[room]:
            await connection.send_json({
                "type": "users_update",
                "users": user_list
            })

    def add_user(self, username: str, room: str):
        if username in self.users.keys():
            return False
        self.users[username] = room
        return True

# Initialize the connection manager
manager = ConnectionManager()

# Route for home page
@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Route for user registration
@app.post("/register")
async def register(username: str = Form(...), room: str = Form(...)):
    if manager.add_user(username, room):
        return RedirectResponse(url=f"/chat/{room}?username={username}", status_code=303)
    return RedirectResponse(url=f"/?error=username_taken", status_code=303)

# Route for chat room
@app.get("/chat/{room}", response_class=HTMLResponse)
async def get_chat(request: Request, room: str):
    username = request.query_params.get("username")
    if username not in manager.users:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "room": room,
        "username": username
    })

# WebSocket endpoint for chat
@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str):
    await manager.connect(websocket, room, username)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data, room, username)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room, username)
        await manager.broadcast(f"{username} has left the chat", room, "System")
        await manager.broadcast_user_list(room)

# Run the application
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
