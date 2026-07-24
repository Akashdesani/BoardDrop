import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("Connected To Server")

@sio.event
def disconnect():
    print("Disconnected")

@sio.on("new_file")
def new_file(data):
    print("New File :", data["filename"])

sio.connect("http://127.0.0.1:5000")

sio.wait()