import threading


class ThreadSafeCounter:
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self._value += 1
            return self._value

    def get_value(self):
        with self._lock:
            return self._value

    def reset(self):
        with self._lock:
            self._value = 0


def chunk_list(lst: list[str], n) -> list[list[str]]:
    """将列表分割为n个近似相等的块"""
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n)]
