import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from fastapi.testclient import TestClient

from src.main import create_app
from src.shared.config.settings import Settings


class BinaryHandler(BaseHTTPRequestHandler):
    payload = b"authorized-video-content"

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/video.mp4":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


@pytest.fixture
def source_server() -> tuple[ThreadingHTTPServer, Thread]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), BinaryHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, thread
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


def _wait_for_terminal_status(
    client: TestClient,
    download_id: str,
    timeout_seconds: float = 3.0,
) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = client.get(f"/api/v1/downloads/{download_id}")
        assert response.status_code == 200
        body = response.json()
        if body["queue_status"] in ("completed", "failed", "canceled"):
            return body
        time.sleep(0.05)
    raise AssertionError("job nao atingiu status terminal no tempo esperado")


def test_downloads_authorized_direct_url_to_local_storage(
    tmp_path: Path,
    source_server: tuple[ThreadingHTTPServer, Thread],
) -> None:
    server, _thread = source_server
    port = server.server_address[1]

    settings = Settings(
        download_output_dir=str(tmp_path),
        allowed_source_hosts="127.0.0.1",
    )

    with TestClient(create_app(settings)) as client:
        create_response = client.post(
            "/api/v1/downloads",
            json={
                "provider": "panda_video",
                "video_reference": f"http://127.0.0.1:{port}/video.mp4",
                "requester_id": "user-real-download-001",
                "download_id": "dl-real-download-001",
                "authorization": {
                    "session_proof": "abcdefgh",
                    "entitlement_proof": "ijklmnop",
                },
                "prefer_cached_authorization": True,
            },
        )
        assert create_response.status_code == 200

        terminal_status = _wait_for_terminal_status(client, "dl-real-download-001")
        assert terminal_status["queue_status"] == "completed"
        assert terminal_status["success"] is True
        assert terminal_status["artifact_location"] is not None

        local_file = Path(terminal_status["artifact_location"])
        assert local_file.exists()
        assert local_file.read_bytes() == BinaryHandler.payload


def test_rejects_source_host_outside_allowlist(
    tmp_path: Path,
    source_server: tuple[ThreadingHTTPServer, Thread],
) -> None:
    server, _thread = source_server
    port = server.server_address[1]

    settings = Settings(
        download_output_dir=str(tmp_path),
        allowed_source_hosts="example.com",
    )

    with TestClient(create_app(settings)) as client:
        create_response = client.post(
            "/api/v1/downloads",
            json={
                "provider": "hotmart",
                "video_reference": f"http://127.0.0.1:{port}/video.mp4",
                "requester_id": "user-real-download-002",
                "download_id": "dl-real-download-002",
                "authorization": {
                    "session_proof": "abcdefgh",
                    "entitlement_proof": "ijklmnop",
                },
                "prefer_cached_authorization": True,
            },
        )
        assert create_response.status_code == 200

        terminal_status = _wait_for_terminal_status(client, "dl-real-download-002")
        assert terminal_status["queue_status"] == "failed"
        assert terminal_status["success"] is False
        assert terminal_status["code"] == "SOURCE_NOT_ALLOWED"
        assert terminal_status["message"] == "Nao foi possivel baixar o video."
