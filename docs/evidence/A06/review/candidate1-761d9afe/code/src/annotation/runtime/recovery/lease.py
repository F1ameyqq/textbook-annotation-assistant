"""Bounded owner lease renewal; process liveness alone never grants authority."""
import threading

from annotation.runtime.storage.common import fail


class LeaseKeeper:
    def __init__(self, store, target_key, owner_id, generation):
        self.store, self.target_key = store, target_key
        self.owner_id, self.generation = owner_id, generation
        self.stopped = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self._run, name="a03-lease-renewal", daemon=False)

    def _run(self):
        while not self.stopped.wait(2):
            try:
                self.store.renew(self.target_key, owner_id=self.owner_id, generation=self.generation)
            except Exception as error:
                self.error = error
                return

    def start(self):
        self.thread.start()
        return self

    def check(self):
        if self.error is not None:
            raise self.error

    def stop(self):
        self.stopped.set()
        self.thread.join(timeout=7)
        if self.thread.is_alive():
            fail("LEASE_RENEWAL_SHUTDOWN_TIMEOUT", "owned renewal thread did not stop", 6)
