import os
import shutil
import textwrap
import types
from pathlib import Path
from time import sleep

import pytest
from click.testing import CliRunner

from scsm import cli
from scsm.config import Config
from scsm.core import App, Server, SteamCMD


APP_DIR = Path('~/.local/share/scsm/apps').expanduser()
APP_ID = '232370'
APP_ID_FAIL = '380840'
APP_NAME = 'hl2dm'
BACKUP_DIR = Path('~/.local/share/scsm/backups').expanduser()


@pytest.fixture
def app_installed():
    steamcmd = SteamCMD()
    if not steamcmd.installed:
        steamcmd.install()
        steamcmd.update()

    app = App(APP_ID, APP_DIR, BACKUP_DIR)
    if not app.installed:
        app.update()
    return app


@pytest.fixture
def app_removed(server_stopped):
    app = App(APP_ID, APP_DIR, BACKUP_DIR)
    if app.installed:
        app.remove()
    return app


@pytest.fixture
def server_running(app_installed):
    server = Server(APP_NAME, APP_DIR, BACKUP_DIR)
    if not server.running:
        server.start()
    return server


@pytest.fixture
def server_stopped(app_installed):
    server = Server(APP_NAME, APP_DIR, BACKUP_DIR)
    if server.running:
        server.stop()
        for _ in range(10):
            if not server.running:
                break
            sleep(1)
        else:
            server.kill()
    return server


def test_backup(server_stopped):
    if server_stopped.backup_dir.exists():
        shutil.rmtree(server_stopped.backup_dir)

    runner = CliRunner()
    result = runner.invoke(cli.backup, [APP_ID, '--no-compress'])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ App ID ] - 232370
        [ Status ] - Backup started
        [ Status ] - Backup complete
    ''')


def test_console(server_running):
    runner = CliRunner()
    result = runner.invoke(cli.console, [APP_NAME], input='$\'\003\'\n')
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ Status ] - Attaching to session
        [ Status ] - Disconnected from session
    ''')


def test_edit(app_installed):
    runner = CliRunner()
    result = runner.invoke(cli.edit, [APP_ID, '--editor', 'more'])
    assert result.exit_code == 0


def test_install(app_removed):
    runner = CliRunner()
    result = runner.invoke(cli.install, [APP_ID])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent(f'''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ App ID ] - 232370
        [ Status ] - Installing
        [ Status ] - Success! App \'{APP_ID}\' fully installed.
    ''')


def test_kill(server_running):
    runner = CliRunner()
    result = runner.invoke(cli.kill, [APP_NAME])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ Status ] - Killing
        [ Status ] - Stopped
    ''')


def test_list(app_installed):
    runner = CliRunner()
    result = runner.invoke(cli.list, [APP_ID])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ F-Name ] - Half-Life 2: Deathmatch
        [ Name   ] - hl2dm
        [ App ID ] - 232370
        [ Status ] - Installed
    ''')


# def test_monitor():
#     runner = CliRunner()
#     result = runner.invoke(cli.monitor, [APP_ID], input='$\'\003\'\n')
#     assert result.exit_code == 0


def test_remove(server_stopped):
    runner = CliRunner()
    result = runner.invoke(cli.remove, [APP_ID])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ App ID ] - 232370
        [ Status ] - Removing
        [ Status ] - Remove complete
    ''')


def test_restart(server_running):
    runner = CliRunner()
    result = runner.invoke(cli.restart, [APP_NAME])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ Status ] - Stopping
        [ Status ] - Stopped
        [ ------ ]
        [ Name   ] - hl2dm
        [ Status ] - Starting
        [ Status ] - Started
    ''')


def test_restore(server_stopped):
    server_stopped.backup_dir.mkdir(parents=True, exist_ok=True)
    if len(os.listdir(server_stopped.backup_dir)) < 1:
        server_stopped.backup(compression=None)

    runner = CliRunner()
    result = runner.invoke(cli.restore, [APP_ID], input='1\n')
    assert result.exit_code == 0
    assert result.output.split('\n')[-2] == textwrap.dedent('''\
        [ Status ] - Restore complete''')


def test_send(server_running):
    runner = CliRunner()
    result = runner.invoke(cli.send, ['test', APP_NAME])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ Status ] - Command sent
        [ Status ] - Command finished
    ''')


def test_setup():
    if Config.config_f.exists() and not Config.system_wide:
        Config.remove()

    runner = CliRunner()
    result = runner.invoke(cli.setup, input='N\n')
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
         [ ------ ]
         [ Status ] - Creating config files
         [ Status ] - Configs installed
    ''')


def test_start(server_stopped):
    runner = CliRunner()
    result = runner.invoke(cli.start, [APP_NAME])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
         [ ------ ]
         [ Name   ] - hl2dm
         [ Status ] - Starting
         [ Status ] - Started
    ''')


def test_status(server_running):
    runner = CliRunner()
    result = runner.invoke(cli.status, [APP_NAME])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ Status ] - Running
    ''')


def test_stop(server_running):
    runner = CliRunner()
    result = runner.invoke(cli.stop, [APP_NAME])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ Status ] - Stopping
        [ Status ] - Stopped
    ''')


def test_update(app_installed):
    runner = CliRunner()
    result = runner.invoke(cli.update, [APP_ID])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ App ID ] - 232370
        [ Status ] - Checking for updates
        [ Status ] - Already up to date
    ''')


@pytest.mark.parametrize('app,result', [
    (('all',), types.GeneratorType),
    (('running',), list),
    (('backups',), types.GeneratorType)
])
def test_app_special_names(app, result):
    tmp = cli.app_special_names(app)
    assert type(tmp) is result
    assert isinstance(tmp, result)
