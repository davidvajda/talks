import eventlet
import socketio
from q import Queue

socket = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(socket, static_files={
    '/': {'content_type': 'text/html', 'filename': 'index.html'}
})

clients = set()
talkees = Queue()
listeners = Queue()
connections = {}

def check_clients():
    print(f"clients -> {clients}")
    print(f"listeners -> ", end="")
    listeners.print_queue()
    print(f"talkees -> ", end="")
    talkees.print_queue()
    print(f"connections -> {connections}")

@socket.event
def connect(sid, environ):
    print("[CONNECTED]", sid)
    clients.add(sid)

@socket.event
def disconnect(sid):
    print("[DISCONNECTED]", sid)
    clients.remove(sid)

    # send information to still connected client that other client has disconnected
    other_client = connections.pop(sid, None)

    if other_client:
        other_client_sid = other_client["sid"]
        # remove the other client from connections
        connections.pop(other_client_sid, None)
        socket.emit("client_disconnected", room=other_client_sid)

@socket.event
def message(sid, data):
    target_sid = connections[sid]["sid"]
    print(f"[MESSAGE RECEIVED]", data)

    socket.emit("message", data, room=target_sid)

@socket.event
def talkee_join(sid, data):
    data["sid"] = sid

    # check if can be paired with listener and add them to connection if so
    if not listeners.is_empty():

        listener = listeners.dequeue()
        connect(data, listener)
        socket.emit("chat_connected", room=sid)
        socket.emit("chat_connected", room=listener["sid"])

    # if listener queue is empty add talkee to queue
    else:
        talkees.enqueue(data)
        socket.emit("enqueued", room=sid)
    check_clients()

@socket.event
def listener_join(sid, data):
    data["sid"] = sid
    print("[LISTENER]", data)

    # check if can be paired with talkee and add them to connection if so
    if not talkees.is_empty():

        talkee = talkees.dequeue()
        connect(talkee, data)

        socket.emit("chat_connected", room=sid)
        socket.emit("chat_connected", room=talkee["sid"])

    # if listener queue is empty add listener to queue
    else:
        listeners.enqueue(data)
        socket.emit("enqueued", room=sid)

    check_clients()

def connect(conn1, conn2):
    connections[conn1["sid"]] = conn2
    connections[conn2["sid"]] = conn1

if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('localhost', 5000)), app)