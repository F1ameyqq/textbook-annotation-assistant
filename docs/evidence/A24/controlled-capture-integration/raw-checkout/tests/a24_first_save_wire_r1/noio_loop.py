"""Pure-memory asyncio loop for synthetic callbacks; no Windows socketpair."""
import asyncio
import selectors


class MemorySelector(selectors.BaseSelector):
    def register(self, *args, **kwargs):
        raise AssertionError("TEST_LOOP_FD_FORBIDDEN")
    def unregister(self, *args, **kwargs):
        raise AssertionError("TEST_LOOP_FD_FORBIDDEN")
    def select(self, timeout=None):
        return []
    def get_map(self):
        return {}
    def close(self):
        pass


class MemoryLoop(asyncio.SelectorEventLoop):
    def __init__(self):
        super().__init__(selector=MemorySelector())
    def _make_self_pipe(self):
        self._ssock = self._csock = None
    def _close_self_pipe(self):
        pass
    def _write_to_self(self):
        pass


class MemoryPolicy(asyncio.DefaultEventLoopPolicy):
    _loop_factory = MemoryLoop
