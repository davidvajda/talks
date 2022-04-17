import logging
import os

import eventlet
import socketio
import time
from q import Queue
from person import Person

# SERVER SET UP
socket = socketio.Server(cors_allowed_origins="*", logger=True, engineio_logger=True)
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
    logging.critical(f"[CONNECTED] {sid}")
    # print("[CONNECTED]", sid)
    clients[sid] = Person(sid)
    clients[sid].set_environ(environ)
    socket.emit("connected", sid)

@socket.event
def disconnect(sid):
    if sid not in clients:
        return

    disconnected_person = clients.pop(sid)
    other_client_sid = disconnected_person.other_client_sid

    logging.critical(f"[DISCONNECTED] {disconnected_person.jsonify()}")
    # print("[DISCONNECTED]", disconnected_person.jsonify())

    # IF THE OTHER CLIENT IS STILL CONNECTED
    if other_client_sid in clients:
        # send information to other client
        # add disconnected client to set for possible connection restoration
        reconnects[sid] = disconnected_person

        send_message(
            message = f"{disconnected_person.name} has disconnected...",
            type = "alert",
            to=other_client_sid,
        )

    # IF CLIENT IS NO LONGER CONNECTED
    elif other_client_sid in reconnects:
        reconnects.pop(other_client_sid)

    check_clients()

@socket.event
def message(sid, data):
    client = clients.get(sid)
    if not client:
        return

    send_message(
        message = data["message"],
        time=data["time"],
        to=client.other_client_sid
    )

@socket.event
def reconnect(sid, prev_sid):
    # GET PERSON FROM RECONNECTS AND REMOVE HIM FROM THE DICT
    reconnected_client = reconnects.get(prev_sid)
    if not reconnected_client:
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

    # sending informatin to both clients
    send_message(
        message = f"{reconnected_client.name} has reconnected...",
        type = "alert",
        to=other_client_sid
    )
    socket.emit("chat_connected", clients[other_client_sid].jsonify(), room=sid)

    send_message(
        message = "You have been reconnected...",
        type = "alert",
        to=sid
    )

@socket.event
def talkee_join(sid, data):
    talkee = clients.get(sid)

    if not talkee:
        return

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

@socket.event
def listener_join(sid, data):
    listener = clients.get(sid)

    if not listener:
        return

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

@socket.event
def leave_chat(sid):
    if sid not in clients:
        return

    disconnected_client = clients.get(sid)
    clients[sid].disconnect()
    other_client_sid = disconnected_client.other_client_sid

    # send information to other client
    send_message(
        message=f"{disconnected_client.name} has disconnected...",
        type="alert",
        to=other_client_sid
    )

def epoch():
    return round(time.time() * 1000)

def send_message(message = None, type = "message", time = None, to = None):
    if not time:
        time = epoch()

    response = {
        "message": message,
        "type": type,
        "time": time,
    }
    socket.emit("message", response, room=to)

if __name__ == '__main__':
    port = os.environ.get("PORT", 5000)
    # eventlet.wsgi.server(eventlet.listen(('localhost', 5000)), app, debug=True)
    eventlet.wsgi.server(eventlet.listen(('', int(port))), app)