import base64
import hashlib
import json
import socketserver
import struct
from contextlib import contextmanager
from threading import Thread

from app.telemetry import read_mqtt, read_websocket

PAYLOAD = b'{"readings":[]}'


@contextmanager
def local_server(handler):
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server.server_address[1]
        finally:
            server.shutdown()
            thread.join(2)


def test_websocket_feed_reads_frame_from_provider(monkeypatch):
    class Server(socketserver.StreamRequestHandler):
        def handle(self):
            self.rfile.readline()
            headers = {}
            while line := self.rfile.readline().strip():
                k, v = line.decode().split(":", 1)
                headers[k.lower()] = v.strip()
            key = headers["sec-websocket-key"]
            result = base64.b64encode(
                hashlib.sha1(
                    (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode(), usedforsecurity=False
                ).digest()
            )
            self.wfile.write(
                b"HTTP/1.1 101 Switching Protocols\r\n"
                b"Upgrade: websocket\r\nConnection: Upgrade\r\n"
                b"Sec-WebSocket-Accept: " + result + b"\r\n\r\n"
            )
            self.wfile.write(bytes([0x81, len(PAYLOAD)]) + PAYLOAD + b"\x88\x00")

    with local_server(Server) as port:
        target = f"ws://127.0.0.1:{port}"
        monkeypatch.setenv("TELEMETRY_ORIGINS", target)
        assert json.loads(read_websocket(target + "/telemetry", "")) == {"readings": []}


def test_mqtt_feed_subscribes_to_exact_topic(monkeypatch):
    class Broker(socketserver.StreamRequestHandler):
        def packet(self):
            header = self.rfile.read(1)[0]
            length, multiplier = 0, 1
            for _ in range(4):
                byte = self.rfile.read(1)[0]
                length += (byte & 0x7F) * multiplier
                if byte < 128:
                    return header, self.rfile.read(length)
                multiplier *= 128
            raise ValueError("Invalid length")

        def handle(self):
            header, _ = self.packet()
            assert header == 0x10
            self.wfile.write(b"\x20\x02\x00\x00")
            header, request = self.packet()
            assert header == 0x82 and b"city/mock" in request
            self.wfile.write(b"\x90\x03" + request[:2] + b"\x00")
            topic = b"city/mock"
            body = struct.pack("!H", len(topic)) + topic + PAYLOAD
            self.wfile.write(bytes([0x30, len(body)]) + body)

    with local_server(Broker) as port:
        origin = f"mqtt://127.0.0.1:{port}"
        monkeypatch.setenv("TELEMETRY_ORIGINS", origin)
        assert read_mqtt(origin, "city/mock", "", "") == PAYLOAD
