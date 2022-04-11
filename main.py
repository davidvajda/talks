import eventlet
import socketio
from q import Queue
from person import Person

# SERVER SET UP
socket = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(socket, static_files={
    '/': {'content_type': 'text/html', 'filename': 'index.html'}
})

# GLOBAL DATA STRUCTURES
clients = {}
talkees = Queue()
listeners = Queue()

# DEBUG FUNCTION, MIGHT DELETE LATER
def check_clients():
    print(f"clients -> {clients}")
    print(f"listeners -> ", end="")
    listeners.print_queue()
    print(f"talkees -> ", end="")
    talkees.print_queue()

@socket.event
def connect(sid, environ):
    print("[CONNECTED]", sid)
    clients[sid] = Person(sid)

@socket.event
def disconnect(sid):
    print("[DISCONNECTED]", sid)
    disconnected_person = clients.pop(sid)

    # send information to still connected client that other client has disconnected
    other_client_sid = disconnected_person.other_client_sid

    if other_client_sid:
        # remove the other client from connections
        clients[other_client_sid].disconnect()
        socket.emit("client_disconnected", room=other_client_sid)

@socket.event
def message(sid, data):
    print("[MESSAGE]", data)
    response = {
        "message": data["message"],
        "time": data["time"],
        "from": clients[sid].name,
    }

    socket.emit("message", response,
                room=clients[sid].other_client_sid
                )

@socket.event
def talkee_join(sid, data):
    talkee = clients[sid]
    talkee.set_name(data["name"], "talkee")

    # check if can be paired with listener and add them to connection if so
    if not listeners.is_empty():

        listener = listeners.dequeue()
        talkee.connect_to(listener)

        # send information to talkee then to listener
        socket.emit("chat_connected", listener.jsonify(), room=sid)
        socket.emit("chat_connected", talkee.jsonify(), room=listener.sid)

    # if listener queue is empty add talkee to queue
    else:
        talkees.enqueue(talkee)
        socket.emit("enqueued", room=sid)

    # DEBUG MESSAGE
    check_clients()

@socket.event
def listener_join(sid, data):
    listener = clients[sid]
    listener.set_name(data["name"], "listener")

    # check if can be paired with talkee and add them to connection if so
    if not talkees.is_empty():

        talkee = talkees.dequeue()
        listener.connect_to(talkee)

        # send information to listener then to talkee
        socket.emit("chat_connected", talkee.jsonify(), room=sid)
        socket.emit("chat_connected", listener.jsonify(), room=talkee.sid)

    # if listener queue is empty add listener to queue
    else:
        listeners.enqueue(listener)
        socket.emit("enqueued", room=sid)

    check_clients()

if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('localhost', 5000)), app)
    # eventlet.wsgi.server(eventlet.listen(('', 5000)), app)