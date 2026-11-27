"""Live machine readings through psutil. The disk reading is for the
directory the app runs in, which inside the container is the volume the
image lives on."""

import os
import platform
import socket
from datetime import UTC
from datetime import datetime
from pathlib import Path

import psutil

from src.platform.ports.outbound.system_readings import HostReading


class PsutilHostReader:
    def __init__(self, disk_path: str = ".") -> None:
        self._disk_path = str(Path(disk_path).resolve())
        # The first cpu_percent(interval=None) call returns 0.0; priming it
        # here makes the first reading of the admin area a real one.
        psutil.cpu_percent(interval=None)

    def read(self) -> HostReading:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(self._disk_path)
        try:
            load: tuple[float, float, float] | None = os.getloadavg()
        except (AttributeError, OSError):
            load = None
        return HostReading(
            hostname=socket.gethostname(),
            platform=platform.platform(),
            python_version=platform.python_version(),
            boot_time=datetime.fromtimestamp(psutil.boot_time(), tz=UTC),
            process_start_time=datetime.fromtimestamp(
                psutil.Process(os.getpid()).create_time(), tz=UTC
            ),
            cpu_count=psutil.cpu_count(logical=True) or 1,
            cpu_percent=float(psutil.cpu_percent(interval=None)),
            load_average=load,
            memory_total_bytes=int(memory.total),
            memory_used_bytes=int(memory.total - memory.available),
            memory_percent=float(memory.percent),
            disk_path=self._disk_path,
            disk_total_bytes=int(disk.total),
            disk_used_bytes=int(disk.used),
            disk_percent=float(disk.percent),
        )
