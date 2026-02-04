import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

CLIENT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,62}$")

_script_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _script_lock
    if _script_lock is None:
        _script_lock = asyncio.Lock()
    return _script_lock


@dataclass
class ScriptResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int


def validate_client_name(name: str) -> bool:
    return bool(CLIENT_NAME_PATTERN.match(name))


async def _run_script(
    script_path: Path, *args: str, timeout: int = 120
) -> ScriptResult:
    cmd = ["bash", str(script_path), *args]
    logger.info("Executing: %s", " ".join(cmd))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as e:
        logger.exception("Failed to start script process")
        return ScriptResult(
            success=False, stdout="", stderr=str(e), return_code=-1
        )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error("Script timed out after %d seconds", timeout)
        proc.kill()
        await proc.wait()
        return ScriptResult(
            success=False,
            stdout="",
            stderr=f"Script timed out after {timeout} seconds",
            return_code=-1,
        )

    result = ScriptResult(
        success=(proc.returncode == 0),
        stdout=stdout_bytes.decode("utf-8", errors="replace"),
        stderr=stderr_bytes.decode("utf-8", errors="replace"),
        return_code=proc.returncode,
    )
    logger.info(
        "Script exited code=%d stdout=%d bytes stderr=%d bytes",
        result.return_code,
        len(result.stdout),
        len(result.stderr),
    )
    return result


async def create_client(
    script_path: Path,
    client_name: str,
    output_dir: Path,
    cert_days: int = 365,
) -> tuple[bool, Path | None, str]:
    if not validate_client_name(client_name):
        return (
            False,
            None,
            "Некорректное имя клиента. Допустимы буквы, цифры, дефис, подчёркивание.",
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    ovpn_path = output_dir / f"{client_name}.ovpn"

    async with _get_lock():
        result = await _run_script(
            script_path,
            "client",
            "add",
            client_name,
            "--cert-days",
            str(cert_days),
            "--output",
            str(ovpn_path),
        )

    if result.success and ovpn_path.exists():
        return True, ovpn_path, f"Клиент '{client_name}' создан."

    error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
    return False, None, f"Ошибка создания клиента: {error_msg}"


async def revoke_client(
    script_path: Path, client_name: str
) -> tuple[bool, str]:
    if not validate_client_name(client_name):
        return False, "Некорректное имя клиента."

    async with _get_lock():
        result = await _run_script(
            script_path, "client", "revoke", client_name
        )

    if result.success:
        return True, f"Клиент '{client_name}' отозван."

    error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
    return False, f"Ошибка отзыва клиента: {error_msg}"


async def list_clients(script_path: Path) -> tuple[bool, str]:
    async with _get_lock():
        result = await _run_script(script_path, "client", "list")

    if result.success:
        clients = result.stdout.strip()
        return True, clients if clients else "Клиенты не найдены."

    error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
    return False, f"Ошибка получения списка: {error_msg}"
