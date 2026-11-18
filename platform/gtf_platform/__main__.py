"""Start the loopback API. A second process exits without reading a session secret."""

from __future__ import annotations

import socket
import sys
from pathlib import Path

from gtf_platform.app import create_app
from gtf_platform.config import load_settings, with_port
from gtf_platform.instance import AlreadyRunning, InstanceLock


def web_dist() -> Path | None:
    dist = Path(__file__).resolve().parents[1] / "web" / "dist"
    if (dist / "index.html").is_file():
        return dist
    return None


def main() -> int:
    try:
        settings = load_settings()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    lock = InstanceLock(settings.data_dir)
    try:
        lock.acquire()
    except AlreadyRunning as exc:
        if exc.port:
            print(
                "already running at http://%s:%s" % (settings.bind_host, exc.port),
                file=sys.stderr,
            )
        else:
            print("already running", file=sys.stderr)
        return 0
    family = socket.AF_INET6 if settings.bind_host == "::1" else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((settings.bind_host, settings.bind_port))
        sock.listen(2048)
        port = int(sock.getsockname()[1])
        lock.write_port(port)
        bound = with_port(settings, port)
        application = create_app(bound, web_dist=web_dist())
        print("GTF Trading Intelligence at http://%s:%s" % (bound.bind_host, port), file=sys.stderr)
        import uvicorn

        config = uvicorn.Config(
            application,
            fd=sock.fileno(),
            access_log=False,
            log_level="info",
        )
        server = uvicorn.Server(config)
        server.run()
    finally:
        lock.release()
        sock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
