"""Voice announcer — optional pyttsx3 wrapper, background-threaded, gracefully degrades."""

import queue
import threading
from typing import Optional


class Announcer:
    def __init__(self, settings):
        self.settings = settings
        self._engine = None
        self._queue: "queue.Queue[Optional[str]]" = queue.Queue(maxsize=8)
        self._thread: Optional[threading.Thread] = None
        self._enabled = False
        self._init()

    def _init(self):
        try:
            import pyttsx3  # type: ignore
            self._engine = pyttsx3.init()
            try:
                self._engine.setProperty("rate", 180)
                self._engine.setProperty("volume", 0.9)
            except Exception:
                pass
            self._enabled = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        except Exception:
            # pyttsx3 not installed or no audio backend — announcer is a no-op
            self._enabled = False

    @property
    def available(self) -> bool:
        return self._enabled

    def say(self, text: str):
        if not self._enabled or not self.settings.voice_announcer:
            return
        try:
            self._queue.put_nowait(text)
        except queue.Full:
            pass  # drop — we don't want a long queue of catch-ups

    def shutdown(self):
        if not self._enabled:
            return
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        try:
            if self._thread is not None:
                self._thread.join(timeout=1.0)
        except Exception:
            pass

    def _loop(self):
        while True:
            try:
                msg = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if msg is None:
                return
            try:
                self._engine.say(msg)
                self._engine.runAndWait()
            except Exception:
                # Engine may be invalidated on Windows — just keep silent
                continue
