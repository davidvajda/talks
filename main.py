import os
import time

import eventlet
import socketio

from q import Queue
from person import Person

# SERVER SET UP
socket = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(socket)

# GLOBAL VARIABLES
clients = {}
reconnects = {}
talkees = Queue()
listeners = Queue()

# DEBUG FUNCTION
@socket.event
def check_clients(sid):
    print(f"clients -> {clients}")
    print(f"reconnects -> {reconnects}")
    print(f"listeners -> ", end="")
    listeners.print_queue()
    print(f"talkees -> ", end="")
    talkees.print_queue()

@socket.event
def connect(sid, environ):
    # connected clients are stored in dictionary {clients}
    print("[CONNECTED]", sid)
    
    clients[sid] = Person(sid)
    clients[sid].set_environ(environ)
    
    socket.emit("connected", sid)

@socket.event
def disconnect(sid):
    if sid not in clients:
        return

    disconnected_client = clients.pop(sid)
    other_client_sid = disconnected_client.other_client_sid

    print("[DISCONNECTED]", disconnected_client.jsonify())

    # IF THE OTHER CLIENT IS STILL CONNECTED
    if other_client_sid in clients:
        # store disconnected client in {reconnects} for possible reconnection
        reconnects[sid] = disconnected_client

        # send information to other client
        send_message(
            message = f"{disconnected_client.name} has disconnected...",
            type = "alert",
            to=other_client_sid,
        )

    # IF CLIENT IS NO LONGER CONNECTED
    elif other_client_sid in reconnects:
        reconnects.pop(other_client_sid)

@socket.event
def message(sid, data):
    # forward the message to other client
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
    # get person instance out of reconnects
    if not reconnects.get(prev_sid):
        return
    reconnected_client = reconnects.pop(prev_sid)

    # restore the information from original person instance
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

# TODO: refactor/merge talke_join and listener_join
@socket.event
def talkee_join(sid, data):
    talkee = clients.get(sid)

    if not talkee:
        print(f"[ERROR] Talkee {sid} not found in clients!")
        return

    # in case of multiple event calls enqueue client only once
    talkee_in_front = talkees.peek()
    if talkee_in_front and sid == talkee_in_front.sid:
        print(f"[WARNING] Talkee {sid} already enqueued!")
        return

    talkee.set_name(data["name"], "talkee")

    # get available listener from queue
    while not listeners.is_empty():
        listener = listeners.dequeue()

        if listener.sid in clients:
            break

    else:
        # if break didn't happen - listener queue is empty, this code gets executed
        talkees.enqueue(talkee)
        socket.emit("enqueued", room=sid) 
        return

    # if break did happen
    talkee.connect_to(listener)

    # send information to both clients
    socket.emit("chat_connected", listener.jsonify(), room=sid)
    socket.emit("chat_connected", talkee.jsonify(), room=listener.sid)

@socket.event
def listener_join(sid, data):
    listener = clients.get(sid)

    if not listener:
        print(f"[ERROR] Listener {sid} not found in clients!")
        return

    # in case of multiple event calls enqueue client only once
    listener_in_front = listeners.peek()
    if listener_in_front and sid == listener_in_front.sid:
        print(f"[WARNING] Listener {sid} already enqueued!")
        return

    listener.set_name(data["name"], "listener")

    # get available talkee from queue
    while not talkees.is_empty():

        talkee = talkees.dequeue()

        if talkee.sid in clients:
            break

    else:
        # if break didn't happen - talkee queue is empty, this code gets executed
        listeners.enqueue(listener)
        socket.emit("enqueued", room=sid)
        return

    # if break did happen
    listener.connect_to(talkee)

    # send information to both clients
    socket.emit("chat_connected", talkee.jsonify(), room=sid)
    socket.emit("chat_connected", listener.jsonify(), room=talkee.sid)

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
