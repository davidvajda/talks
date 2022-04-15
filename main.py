import eventlet
import socketio
import time
from q import Queue
from person import Person

# SERVER SET UP
socket = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(socket, static_files={
    '/': {'content_type': 'text/html', 'filename': 'index.html'}
})

# GLOBAL DATA STRUCTURES
clients = {}
reconnects = {}
talkees = Queue()
listeners = Queue()

# DEBUG FUNCTION, MIGHT DELETE LATER
def check_clients():
    print(f"clients -> {clients}")
    print(f"reconnects -> {reconnects}")
    print(f"listeners -> ", end="")
    listeners.print_queue()
    print(f"talkees -> ", end="")
    talkees.print_queue()

@socket.event
def connect(sid, environ):
    print("[CONNECTED]", sid)
    clients[sid] = Person(sid)
    socket.emit("connected", sid)

@socket.event
def disconnect(sid):
    print("[DISCONNECTED]", sid)

    disconnected_person = clients.pop(sid)
    other_client_sid = disconnected_person.other_client_sid

    # IF THE OTHER CLIENT IS STILL CONNECTED
    if other_client_sid in clients:
        # send information to other client
        # add disconnected client to set for possible connection restoration
        reconnects[sid] = disconnected_person

        response = {
            "message": f"{disconnected_person.name} has disconnected...",
            "type": "alert",
            "time": "1111", # TODO: send epoch time
            "from": disconnected_person.name,
        }
        socket.emit("message", response,
                    room=other_client_sid
                    )
        print(f"[LOG] adding {disconnected_person.sid}/{disconnected_person.name} to reconnects")

    # IF CLIENT IS NO LONGER CONNECTED
    elif other_client_sid in reconnects:
        print(f"[LOG] cancelling connection between {other_client_sid}/{reconnects[other_client_sid]} and {disconnected_person.sid}/{disconnected_person.name}")
        reconnects.pop(other_client_sid)

    check_clients()

@socket.event
def message(sid, data):
    response = {
        "message": data["message"],
        "type": "message",
        "time": data["time"],
        "from": clients[sid].name,
    }
    socket.emit("message", response,
                room=clients[sid].other_client_sid
                )

@socket.event
def reconnect(sid, prev_sid):
    # GET PERSON FROM RECONNECTS AND REMOVE HIM FROM THE DICT
    reconnected_client = reconnects.get(prev_sid)
    if not reconnected_client:
        print(f"[FAILED] {prev_sid} not found in reconnects, current sid {sid}")
        return
    reconnects.pop(prev_sid)

    # restore the information from old client instance
    other_client_sid = reconnected_client.other_client_sid
    clients[sid].set_name(reconnected_client.name, reconnected_client.role)

    # check if the other client is still connected
    if other_client_sid not in clients:
        return

    # restoring connection
    clients[sid].connect_to(clients[other_client_sid])
    print(f"[RECONNECTED] {clients[sid].name} and {clients[other_client_sid].name}")

    # sending informatin to both clients
    response = {
        "message": f"{reconnected_client.name} has reconnected...",
        "type": "alert",
        "time": "1234",
        "from": reconnected_client.name,
    }
    socket.emit("message", response, room=other_client_sid)
    socket.emit("chat_connected", clients[other_client_sid].jsonify(), room=sid)

    response["message"] = "You have been reconnected..."
    socket.emit("message", response, room=other_client_sid)

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
    # eventlet.wsgi.server(eventlet.listen(('localhost', 5000)), app, debug=True)
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)