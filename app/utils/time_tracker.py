import time

class TimeTracker(dict):
    def __init__(self):
        super().__init__()
        self["start"] = time.time()
        self["events"] = []

    def mark(self, label):
        now = time.time()
        elapsed_ms = int((now - self["start"]) * 1000)
        self["events"].append((label, elapsed_ms))

    def report(self):
        return self["events"]
