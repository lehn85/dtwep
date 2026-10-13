from __future__ import annotations
import os
import sys
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set
from fastapi import WebSocket

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from calibration_framework import (
    CalibrationConfig,
    CalibrationEngine,
    EnergyPlusRunner,
    load_osm,
    translate_model_to_idf,
)


class ModuleRunner:
    """
    Manages asynchronous module execution, subprocess streaming,
    and interactive GA calibration workflows.
    """

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or WORKSPACE_ROOT
        self.active_processes: Dict[str, asyncio.subprocess.Process] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}

    async def run_module_process(
        self,
        script_path: str,
        config_path: Optional[str] = None,
        force_model_a: bool = False,
        extra_args: Optional[list[str]] = None,
        on_log: Optional[Callable[[str, str], Any]] = None,
    ) -> int:
        """
        Executes a Python module script in a subprocess using `uv run python`,
        streaming stdout and stderr lines via `on_log(line, stream_type)`.
        """
        full_script = self.root_dir / script_path
        if not full_script.exists():
            if on_log:
                on_log(f"Error: Script file not found: {script_path}", "stderr")
            return 1

        cmd = ["uv", "run", "python", str(full_script)]
        if config_path:
            cmd.extend(["--config", str(self.root_dir / config_path)])
        if force_model_a:
            cmd.append("--force-model-a")
        if extra_args:
            cmd.extend(extra_args)

        if on_log:
            on_log(f"Executing: {' '.join(cmd)}", "system")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.root_dir),
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )

        task_id = f"mod_{Path(script_path).stem}_{os.urandom(3).hex()}"
        self.active_processes[task_id] = process

        async def read_stream(stream, stream_type):
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip()
                if on_log and decoded:
                    on_log(decoded, stream_type)

        try:
            await asyncio.gather(
                read_stream(process.stdout, "stdout"),
                read_stream(process.stderr, "stderr"),
            )
            return_code = await process.wait()
            return return_code
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            if on_log:
                on_log("Execution cancelled by user.", "system")
            return -1
        finally:
            self.active_processes.pop(task_id, None)

    # Alias for compatibility
    run_experiment_process = run_module_process

    def cancel_all(self):
        """Cancels all active processes and tasks."""
        for p in self.active_processes.values():
            try:
                p.terminate()
            except Exception:
                pass
        self.active_processes.clear()


# Global runner instance
global_runner = ModuleRunner()
ExperimentRunner = ModuleRunner
