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

class Case:

    def __init__(self, name: str, attributes: dict | None) -> object:
        # always: name (part/s, harmony, dynamic)
        self.name = name
        self.attributes = (
            attributes  # sometimes: instrument, keys, clefs, tempos, meters
        )
        self.trace = []

    def add_events(self, events: list[dict]) -> None:
        self.trace.extend(events)