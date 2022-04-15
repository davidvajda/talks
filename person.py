class Person:
    def __init__(self, sid):
        self.sid = sid
        self.name = None
        self.role = None
        self.other_client_sid = None

    def set_name(self, name, role):
        self.name = name
        self.role = role

    def connect_to(self, other_person):
        self.other_client_sid = other_person.sid
        other_person.other_client_sid = self.sid
        print("[CONNECTING]")
        print(self.jsonify())
        print(other_person.jsonify())

    def disconnect(self):
        self.other_client_sid = None

    def jsonify(self):
        """Returns dictionary representing values of person"""
        return {
            "sid": self.sid,
            "name": self.name,
            "role": self.role,
        }