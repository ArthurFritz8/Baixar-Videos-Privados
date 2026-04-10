from __future__ import annotations

import argparse
import secrets
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.shared.config.settings import Settings

TERMINAL_STATUSES = {"completed", "failed", "canceled"}
PROVIDER_HOSTS: dict[str, tuple[str, ...]] = {
    "youtube": ("youtube.com", "youtu.be"),
    "instagram": ("instagram.com",),
    "tiktok": ("tiktok.com",),
    "facebook": ("facebook.com", "fb.watch"),
    "x": ("x.com", "twitter.com"),
    "vimeo": ("vimeo.com", "player.vimeo.com"),
}


def infer_provider(video_url: str) -> str:
    host = (urlparse(video_url).hostname or "").lower()
    for provider, domains in PROVIDER_HOSTS.items():
        for domain in domains:
            if host == domain or host.endswith(f".{domain}"):
                return provider
    return "panda_video"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Envia um link para a API, aguarda processamento e baixa o arquivo final.",
    )
    parser.add_argument("--url", required=True, help="URL do video/link autorizado")
    parser.add_argument(
        "--provider",
        choices=["panda_video", "hotmart", "youtube", "instagram", "tiktok", "facebook", "x", "vimeo"],
        help="Provider explicito. Se omitido, o script tenta inferir pelo dominio.",
    )
    parser.add_argument(
        "--api-base",
        default="http://127.0.0.1:8000",
        help="Base URL da API",
    )
    parser.add_argument(
        "--requester-id",
        default="cli-user",
        help="Identificador do solicitante",
    )
    parser.add_argument(
        "--download-id",
        default=None,
        help="ID customizado do download",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Arquivo de saida. Se omitido, usa <download_id>.<ext>",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=1.0,
        help="Intervalo de polling para status",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=float,
        default=300.0,
        help="Tempo maximo para aguardar conclusao",
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=60.0,
        help="Timeout das chamadas HTTP",
    )
    return parser


def build_headers(settings: Settings) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.api_key:
        headers[settings.api_key_header_name] = settings.api_key
    return headers


def resolve_output_path(
    download_id: str,
    output_arg: str | None,
    artifact_location: str | None,
) -> Path:
    if output_arg:
        return Path(output_arg).expanduser().resolve()

    suffix = ".bin"
    if artifact_location:
        artifact_suffix = Path(artifact_location).suffix
        if artifact_suffix:
            suffix = artifact_suffix

    return Path.cwd() / f"{download_id}{suffix}"


def main() -> int:
    args = build_parser().parse_args()
    settings = Settings()
    headers = build_headers(settings)

    provider = args.provider or infer_provider(args.url)
    session_proof = f"sess-{secrets.token_hex(8)}"
    entitlement_proof = f"ent-{secrets.token_hex(8)}"
    if session_proof == entitlement_proof:
        entitlement_proof = f"ent-{secrets.token_hex(8)}"

    payload: dict[str, object] = {
        "provider": provider,
        "video_reference": args.url,
        "requester_id": args.requester_id,
        "authorization": {
            "session_proof": session_proof,
            "entitlement_proof": entitlement_proof,
        },
        "prefer_cached_authorization": True,
    }
    if args.download_id:
        payload["download_id"] = args.download_id

    api_base = args.api_base.rstrip("/")
    api_prefix = settings.api_prefix
    timeout = httpx.Timeout(args.request_timeout_seconds)

    with httpx.Client(timeout=timeout) as client:
        create_response = client.post(
            f"{api_base}{api_prefix}/downloads",
            json=payload,
            headers=headers,
        )
        if create_response.status_code != 200:
            print(f"[ERRO] Falha ao criar download: status={create_response.status_code}")
            try:
                print(create_response.json())
            except ValueError:
                print(create_response.text)
            return 1

        create_body = create_response.json()
        download_id = str(create_body["download_id"])
        print(f"[OK] Download aceito. download_id={download_id} provider={provider}")

        deadline = time.time() + args.max_wait_seconds
        last_status: str | None = None
        status_body: dict[str, object] | None = None

        while True:
            status_response = client.get(
                f"{api_base}{api_prefix}/downloads/{download_id}",
                headers=headers,
            )
            if status_response.status_code != 200:
                print(f"[ERRO] Falha ao consultar status: status={status_response.status_code}")
                try:
                    print(status_response.json())
                except ValueError:
                    print(status_response.text)
                return 1

            status_body = status_response.json()
            queue_status = str(status_body.get("queue_status", "unknown"))
            if queue_status != last_status:
                print(f"[INFO] queue_status={queue_status}")
                last_status = queue_status

            if queue_status in TERMINAL_STATUSES:
                break

            if time.time() >= deadline:
                print("[ERRO] Timeout aguardando conclusao do download.")
                return 2

            time.sleep(args.poll_interval_seconds)

        if status_body is None:
            print("[ERRO] Nao foi possivel obter status final.")
            return 1

        final_status = str(status_body.get("queue_status", "unknown"))
        if final_status != "completed":
            print("[ERRO] Download nao concluiu com sucesso.")
            print(
                {
                    "status": final_status,
                    "code": status_body.get("code"),
                    "message": status_body.get("message"),
                }
            )
            return 3

        token_response = client.post(
            f"{api_base}{api_prefix}/downloads/{download_id}/file-token",
            headers=headers,
        )
        if token_response.status_code != 200:
            print(f"[ERRO] Falha ao gerar token de arquivo: status={token_response.status_code}")
            try:
                print(token_response.json())
            except ValueError:
                print(token_response.text)
            return 1

        token = str(token_response.json()["token"])
        output_path = resolve_output_path(
            download_id=download_id,
            output_arg=args.output,
            artifact_location=status_body.get("artifact_location"),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with client.stream(
            "GET",
            f"{api_base}{api_prefix}/downloads/{download_id}/file",
            params={"token": token},
            headers=headers,
        ) as file_response:
            if file_response.status_code != 200:
                print(f"[ERRO] Falha ao baixar arquivo: status={file_response.status_code}")
                try:
                    print(file_response.json())
                except ValueError:
                    print(file_response.text)
                return 1

            with output_path.open("wb") as output_file:
                for chunk in file_response.iter_bytes():
                    output_file.write(chunk)

    print(f"[OK] Arquivo salvo em: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())