from collections import deque


class RetryQueue:
    def __init__(self, max_size=100):
        self.items = deque(maxlen=max_size)

    def push(self, path, payload):
        self.items.append({
            "path": path,
            "payload": payload,
            "attempts": 0,
        })

    def pop(self):
        if not self.items:
            return None
        return self.items.popleft()

    def push_front(self, item):
        self.items.appendleft(item)

    def size(self):
        return len(self.items)
