import datetime as dt


class EventIdHandler:

    def __init__(self):
        self.start = 0
        self.current = 0

    def get_id(self) -> int:
        self.current += 1
        return self.current

    def reset(self):
        self.current = 0
        return
