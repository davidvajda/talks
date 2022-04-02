class Node:
    def __init__(self, data):
        self.data = data
        self.next = None

class Queue:
    def __init__(self):
        self.front = None
        self.rear = None

    def enqueue(self, data):
        node = Node(data)
        if not self.front:
            self.front = node
            self.rear = node

        else:
            self.rear.next = node
            self.rear = node

    def dequeue(self):
        if self.is_empty():
            return None

        node = self.front
        self.front = self.front.next
        return node.data

    def is_empty(self):
        if not self.front:
            return True
        return False

    def print_queue(self):
        node = self.front
        while node:
            print(node.data, end=" -> ")
            node = node.next
        print("")

if __name__ == "__main__":
    q = Queue()
    for item in [5, 3]:
        q.enqueue(item)

    q.print_queue()
    print(q.dequeue())
    q.print_queue()


