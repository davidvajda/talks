<div>
  <h1>Talks - Server</h1>
  <p>The server stores all connected clients in {clients} dictionary, they are removed if disconnect event is called.</p>
  <p>Clients dictionary stores clients in form of Person class, which encapsulates name, role, sid, other clients sid (if connection has been made), origin IP and language.</p>
  <p>After joining a chat as either role, client is connected with the opposite role's front queue or enqueued if opossite role's queue is empty.</p>
  <p>On disconnect (not manual leave with button press), client is added to {reconnects} dictionary.</p>
</div>
