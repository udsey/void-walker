import gc
import threading

from src.walker.walker import VoidWalker, _all_threads, _threads_lock


def run_walkers(n: int = 1, parallel: bool = False):
    """
    Run n walkers.
    Sequential by default, parallel with threading if parallel=True."""
    if not parallel:
        for _ in range(n):
            VoidWalker().walk()
        return
    threads = []
    for _ in range(n):
        walker = VoidWalker()
        thread = threading.Thread(target=walker.walk, daemon=True)
        thread.start()
        threads.append(thread)
    for t in threads:
        t.join()
    with _threads_lock:
        friend_threads = list(_all_threads)
    for t in friend_threads:
        t.join()
    gc.collect()
