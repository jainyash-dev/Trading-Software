"""One API process. A second launch exits and does not read a session secret."""

from __future__ import annotations

import os
from pathlib import Path


class AlreadyRunning(Exception):
    def __init__(self, port: int | None) -> None:
        super().__init__("already running")
        self.port = port


class InstanceLock:
    """Exclusive lock plus a port file. The port is not a secret. No token file exists."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._fd: int | None = None

    def acquire(self) -> None:
        self.directory.mkdir(parents=True, mode=0o700, exist_ok=True)
        path = self.directory / "instance.lock"
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise AlreadyRunning(read_port(self.directory)) from None
        self._fd = fd

    def write_port(self, port: int) -> None:
        if port <= 0 or port > 65535:
            raise ValueError("refusing to publish an invalid port")
        target = self.directory / "instance.port"
        temporary = self.directory / "instance.port.tmp"
        temporary.write_text("%s\n" % port, encoding="ascii")
        os.chmod(temporary, 0o600)
        temporary.replace(target)

    def release(self) -> None:
        if self._fd is None:
            return
        import fcntl

        fcntl.flock(self._fd, fcntl.LOCK_UN)
        os.close(self._fd)
        self._fd = None


def read_port(directory: Path) -> int | None:
    """Read only instance.port. Callers must not open any other file in the directory."""
    path = directory / "instance.port"
    try:
        text = path.read_text(encoding="ascii")
    except OSError:
        return None
    text = text.strip()
    if not text.isdigit():
        return None
    port = int(text)
    if port <= 0 or port > 65535:
        return None
    return port
