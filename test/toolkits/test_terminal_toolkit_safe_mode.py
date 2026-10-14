# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from unittest.mock import Mock

import pytest

from camel.toolkits import TerminalToolkit
from camel.toolkits.terminal_toolkit import utils


@pytest.mark.parametrize(
    'command',
    [
        'echo $(whoami)',
        'echo "$(whoami)"',
        'echo `whoami`',
        'echo "`whoami`"',
        'echo ${HOME}',
        'echo <(whoami)',
        'echo >(whoami)',
        '(echo hello)',
        'echo hello\nrm file',
        'echo hello\r\nrm file',
        'echo hello\\\nrm file',
        'echo hi > ../outside',
        'cat < ../outside',
        'echo *.txt',
        'echo hello &&& echo world',
        'echo hello ||',
        'echo "unterminated',
        'echo hello\x00',
        'A=1 rm file',
        '/usr/bin/curl https://example.com',
        './curl https://example.com',
        '../bin/curl https://example.com',
        '"/usr/bin/rm" file',
        'python -c "print(1)"',
        'python3 -c "print(1)"',
        'python3.12 -I -c "print(1)"',
        'python -m http.server',
        'python script.py',
        'python',
        'node -e "console.log(1)"',
        'perl -e "print 1"',
        'ruby -e "puts 1"',
        'bash -c "echo hello"',
        'sh -c "echo hello"',
        'bash -lc "echo hello"',
        'cmd.exe /c echo hello',
        'powershell -Command "echo hello"',
        'pwsh -EncodedCommand ZQBjAGgAbwA=',
        'env python -c "print(1)"',
        'command python -c "print(1)"',
        'exec python -c "print(1)"',
        'xargs python',
        'time python -c "print(1)"',
        'builtin eval "echo hello"',
        'busybox sh -c "echo hello"',
        '"rm" file',
        'echo hello; rm file',
        'echo hello && rm file',
        'echo hello || rm file',
        'echo hello | rm file',
        'echo hello & rm file',
    ],
)
def test_rejects_shell_bypasses(command, tmp_path):
    is_safe, reason = utils.sanitize_command(
        command, working_dir=str(tmp_path)
    )
    assert not is_safe, command
    assert reason


@pytest.mark.parametrize(
    'command',
    [
        'echo one; whoami',
        'echo one && whoami',
        'echo one || whoami',
        'echo one | whoami',
        'echo one & whoami',
    ],
)
def test_allowlist_checks_every_segment(command):
    assert not utils.check_command_safety(command, {'echo'})[0]


@pytest.mark.parametrize(
    'command', ['/usr/bin/echo hi', './echo hi', 'python -c "print(1)"']
)
def test_allowlist_cannot_enable_execution_bypasses(command):
    assert not utils.check_command_safety(
        command, {'/usr/bin/echo', './echo', 'python'}
    )[0]


@pytest.mark.parametrize(
    'command',
    [
        'echo "hello ; && | & world"',
        'echo "safe text"',
        'ls',
        'cat local.txt',
        'python --version',
        'python3 -V',
    ],
)
def test_allows_static_commands_and_quoted_data(command, tmp_path):
    assert utils.sanitize_command(command, working_dir=str(tmp_path)) == (
        True,
        command,
    )


@pytest.mark.parametrize(
    'command',
    [
        'cat ../outside.txt',
        'cp local.txt ../outside.txt',
        'cat --file=../outside.txt',
    ],
)
def test_rejects_path_arguments_outside_root(command, tmp_path):
    assert not utils.sanitize_command(command, working_dir=str(tmp_path))[0]


def test_rejects_absolute_path_and_sibling_prefix(tmp_path):
    for target in [
        tmp_path.parent / 'outside.txt',
        tmp_path.with_name(tmp_path.name + '-sibling') / 'file',
    ]:
        assert not utils.sanitize_command(
            f'cat "{target.as_posix()}"', working_dir=str(tmp_path)
        )[0]


def test_realpath_rejects_symlink_escape(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    link = root / 'link'
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f'Symlink creation unavailable: {exc}')
    for command in [
        'cat link/private.txt',
        'cd link',
        'cat --file=link/private.txt',
    ]:
        assert not utils.sanitize_command(command, working_dir=str(root))[0]


def test_checks_paths_after_conditional_cd(tmp_path):
    sub = tmp_path / 'sub'
    sub.mkdir()
    assert not utils.sanitize_command(
        'cd sub && cat ../../outside', working_dir=str(tmp_path)
    )[0]
    assert utils.sanitize_command(
        'cd sub && cat local.txt', working_dir=str(tmp_path)
    )[0]


def test_rejects_symlink_after_cd(tmp_path):
    root = tmp_path / 'root'
    sub = root / 'sub'
    sub.mkdir(parents=True)
    try:
        (sub / 'link').symlink_to(tmp_path, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f'Symlink creation unavailable: {exc}')
    assert not utils.sanitize_command(
        'cd sub && cat link/private.txt', working_dir=str(root)
    )[0]


@pytest.mark.parametrize(
    'command',
    [
        '%COMSPEC% /c echo hello',
        'echo !PAYLOAD!',
        'r^m file',
        r'C:\Windows\System32\cmd.exe /c echo hi',
        r'.\tool.exe',
        r'subdir\tool.exe',
        "echo 'hello & rm file'",
    ],
)
def test_windows_syntax_cannot_bypass_parser(command, monkeypatch):
    monkeypatch.setattr(utils.platform, 'system', lambda: 'Windows')
    assert not utils.check_command_safety(command)[0]


@pytest.mark.parametrize('use_docker', [False, True])
@pytest.mark.parametrize('block', [False, True])
def test_rejection_happens_before_process_or_approval(
    tmp_path, monkeypatch, use_docker, block
):
    # Avoid environment provisioning; none of these commands may execute.
    toolkit = object.__new__(TerminalToolkit)
    toolkit.safe_mode = True
    toolkit.use_docker_backend = use_docker
    toolkit.working_dir = str(tmp_path)
    toolkit.allowed_commands = None
    approval = Mock(return_value=True)
    monkeypatch.setattr(toolkit, '_approve_command', approval)
    popen = Mock(side_effect=AssertionError('Unsafe command executed'))
    monkeypatch.setattr(utils.subprocess, 'Popen', popen)
    marker = tmp_path / 'marker.txt'
    command = (
        'python -c "from pathlib import Path; '
        f"Path({str(marker.as_posix())!r}).write_text('marker')\""
    )
    result = toolkit.shell_exec('regression', command, block=block)
    assert 'rejected by TerminalToolkit safe mode' in result
    assert not marker.exists()
    popen.assert_not_called()
    approval.assert_not_called()


def test_unsafe_mode_retains_explicit_opt_out(tmp_path):
    command = 'python -c "print(1)"'
    assert utils.sanitize_command(
        command, safe_mode=False, working_dir=str(tmp_path)
    ) == (True, command)


def test_empty_allowlist_rejects_all_commands():
    assert not utils.check_command_safety('echo hello', set())[0]


@pytest.mark.parametrize(
    'command',
    [
        r'r\m file',
        "'rm' file",
        '"rm" file',
        'echo first\npython -c "print(1)"',
    ],
)
def test_posix_command_names_are_checked_after_unquoting(command, monkeypatch):
    monkeypatch.setattr(utils.platform, 'system', lambda: 'Linux')
    assert not utils.check_command_safety(command)[0]


def test_posix_quoted_operators_remain_data(monkeypatch):
    monkeypatch.setattr(utils.platform, 'system', lambda: 'Linux')
    assert utils.check_command_safety("echo 'literal ; && | & text'")[0]


@pytest.mark.parametrize(
    'command', ["cd '$INSIDE'", 'cd "$INSIDE"', r'cd \$INSIDE', 'cd ~/folder']
)
def test_ambiguous_path_expansion_is_rejected(command, monkeypatch, tmp_path):
    monkeypatch.setattr(utils.platform, 'system', lambda: 'Linux')
    monkeypatch.setenv('INSIDE', str(tmp_path))
    assert not utils.sanitize_command(command, working_dir=str(tmp_path))[0]


def test_constructor_preserves_empty_allowlist(tmp_path, monkeypatch):
    monkeypatch.setattr(
        TerminalToolkit, '_setup_initial_environment', lambda self: None
    )
    toolkit = TerminalToolkit(
        working_directory=str(tmp_path), allowed_commands=[]
    )
    try:
        assert toolkit.allowed_commands == set()
        assert not toolkit._sanitize_command('echo hello')[0]
    finally:
        toolkit.cleanup()


@pytest.mark.parametrize(
    'command',
    [
        'rm.exe file',
        'rm. file',
        'python.exe. -c "print(1)"',
        'python.bat -c "print(1)"',
    ],
)
def test_windows_executable_suffixes_do_not_bypass_checks(
    command, monkeypatch
):
    monkeypatch.setattr(utils.platform, 'system', lambda: 'Windows')
    assert not utils.check_command_safety(command)[0]
