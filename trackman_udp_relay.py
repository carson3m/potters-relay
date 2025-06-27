import socket
import json
import requests
import time
import threading
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

class TrackmanUDPRelay(threading.Thread):
    def __init__(self, config):
        super().__init__(daemon=True)
        self.port = config.get("udp_port", 20998)
        self.buffer_size = config.get("buffer_size", 16384)
        self.relay_url = config["relay_url"]
        self._running = True
        self.sock = None

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', self.port))
        self.sock.settimeout(1.0)

        print(f"[TrackmanRelay] ✅ Listening on UDP port {self.port}...")

        while self._running:
            try:
                data, addr = self.sock.recvfrom(self.buffer_size)
                print(f"[DEBUG] Got something from {addr}: {data[:100]}...")
                print(f"[TrackmanRelay] 🟢 Received {len(data)} bytes from {addr}")

                try:
                    message = json.loads(data.decode('utf-8'))
                    print("[TrackmanRelay] ✅ Parsed JSON, relaying...")
                    self.relay_to_server(message)
                except json.JSONDecodeError as e:
                    print("[TrackmanRelay] ❌ JSON decode failed:", e)

            except socket.timeout:
                continue
            except Exception as e:
                print(f"[TrackmanRelay] ❌ Error: {e}")

    def relay_to_server(self, message):
        try:
            resp = requests.post(self.relay_url, json=message, timeout=2)
            if resp.status_code == 200:
                print("[Relay] ✅ Sent to server")
            else:
                print(f"[Relay] ❌ Server error {resp.status_code}")
        except Exception as e:
            print(f"[Relay] ❌ Network error: {e}")

    def stop(self):
        self._running = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(b'{}', ('127.0.0.1', self.port))
        except:
            pass
        if self.sock:
            self.sock.close()

if __name__ == "__main__":
    config = load_config()
    relay = TrackmanUDPRelay(config)
    relay.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        relay.stop()
