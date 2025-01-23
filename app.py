from flask import Flask, render_template, request, session, redirect
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app)

# Store active users and their rooms
active_users = {}
chat_history = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat')
def chat():
    username = request.args.get('username')
    room = request.args.get('room')
    if username and room:
        session['username'] = username
        session['room'] = room
        return render_template('chat.html', username=username, room=room)
    return redirect('/')

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    active_users[username] = room
    
    # Initialize chat history for new rooms
    if room not in chat_history:
        chat_history[room] = []
    
    # Send join notification
    message = {
        'user': 'System',
        'message': f'{username} has joined the room.',
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }
    chat_history[room].append(message)
    emit('message', message, room=room)
    
    # Send active users list
    room_users = [user for user, user_room in active_users.items() if user_room == room]
    emit('user_list', {'users': room_users}, room=room)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    if username in active_users:
        del active_users[username]
    
    message = {
        'user': 'System',
        'message': f'{username} has left the room.',
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }
    chat_history[room].append(message)
    emit('message', message, room=room)
    
    # Update active users list
    room_users = [user for user, user_room in active_users.items() if user_room == room]
    emit('user_list', {'users': room_users}, room=room)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    message = {
        'user': data['username'],
        'message': data['message'],
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }
    chat_history[room].append(message)
    emit('message', message, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)
