import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest


def _utf8_env() -> dict[str, str]:
    """
    构造强制 UTF-8 的子进程环境。

    CLI 输出包含中文与 emoji，在 Windows 中文环境（GBK 控制台）下按默认区域编码
    解码会得到乱码甚至 `UnicodeDecodeError`，导致输出契约断言失败。
    这里同时固定子进程的 IO 编码与父进程的解码编码，使断言结果与平台无关。
    """
    return {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}


@pytest.fixture
def backend_dir() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.fixture
def run_cli_command(backend_dir: Path) -> Callable[..., subprocess.CompletedProcess[str]]:
    def _run_cli_command(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, '-m', 'cli.main', *args],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False,
            env=_utf8_env(),
        )

    return _run_cli_command


@pytest.fixture
def run_text_cli_command(
    run_cli_command: Callable[..., subprocess.CompletedProcess[str]],
) -> Callable[..., subprocess.CompletedProcess[str]]:
    def _run_text_cli_command(*args: str) -> subprocess.CompletedProcess[str]:
        return run_cli_command('--color=never', '--icon=none', *args)

    return _run_text_cli_command


@pytest.fixture
def run_cli_completion_command(
    backend_dir: Path,
) -> Callable[..., subprocess.CompletedProcess[str]]:
    def _run_cli_completion_command(
        *,
        comp_words: str,
        comp_cword: int | str,
        instruction: str = 'bash_complete',
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, '-m', 'cli.main'],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False,
            env={
                **_utf8_env(),
                'COMP_WORDS': comp_words,
                'COMP_CWORD': str(comp_cword),
                '_RUOYI_COMPLETE': instruction,
            },
        )

    return _run_cli_completion_command


@pytest.fixture
def parse_json_stdout() -> Callable[[subprocess.CompletedProcess[str]], dict[str, Any]]:
    def _parse_json_stdout(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        return json.loads(completed.stdout)

    return _parse_json_stdout


@pytest.fixture
def assert_check_payload_contract() -> Callable[[dict[str, Any], bool], None]:
    def _assert_check_payload_contract(payload: dict[str, Any], allow_exit_code: bool) -> None:
        assert isinstance(payload, dict)
        assert isinstance(payload.get('ok'), bool)
        assert isinstance(payload.get('message'), str)

        if payload['ok']:
            if 'error' in payload:
                assert isinstance(payload['error'], str)
            if 'exit_code' in payload:
                assert isinstance(payload['exit_code'], int)
        else:
            assert isinstance(payload.get('error'), str)
            if allow_exit_code:
                assert isinstance(payload.get('exit_code'), int)

    return _assert_check_payload_contract
