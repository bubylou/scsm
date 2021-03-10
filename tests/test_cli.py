import os
import shutil
import textwrap
import types

import pytest
from click.testing import CliRunner

from scsm import cli
from scsm.config import Config


@pytest.fixture(scope='module')
def runner():
    return CliRunner()


def test_backup(runner, server_stopped):
    if server_stopped.backup_dir.exists():
        shutil.rmtree(server_stopped.backup_dir)

    result = runner.invoke(cli.backup, [str(server_stopped.app_id), '--no-compress'])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ App ID ] - 232370
        [ Status ] - Backup started
        [ Status ] - Backup complete
    ''')


def test_backup_bad_compression(runner, server_stopped):
    result = runner.invoke(cli.backup, [str(server_stopped.app_id), '--compression', 'test'])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ Error  ] - Invalid compression method
    ''')


def test_backup_not_installed(runner, app_removed):
    result = runner.invoke(cli.backup, [str(app_removed.app_id), '--no-compress'])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ App ID ] - 232370
        [ Error  ] - App not installed
    ''')


def test_backup_running(runner, server_running):
    result = runner.invoke(cli.backup, [str(server_running.app_id), '--no-compress'])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ App ID ] - 232370
        [ Error  ] - Stop server before backup
    ''')


def test_console(runner, server_running):
    # Tests error out due to not being run in a real terminal
    assert True


def test_edit(runner, app_installed):
    result = runner.invoke(cli.edit, [str(app_installed.app_id), '--editor', 'more'])
    assert result.exit_code == 0


def test_install(runner, app_removed):
    result = runner.invoke(cli.install, [str(app_removed.app_id)])
    assert result.exit_code == 0


def test_kill(runner, server_running):
    result = runner.invoke(cli.kill, [server_running.app_name])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ Status ] - Killing
        [ Status ] - Stopped
    ''')


def test_list(runner, app_installed):
    result = runner.invoke(cli.list, [str(app_installed.app_id)])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ F-Name ] - Half-Life 2: Deathmatch
        [ Name   ] - hl2dm
        [ App ID ] - 232370
        [ Status ] - Installed
    ''')


# def test_monitor():
#     result = runner.invoke(cli.monitor, [app_id], input='$\'\003\'\n')
#     assert result.exit_code == 0


def test_remove(runner, server_stopped):
    result = runner.invoke(cli.remove, [str(server_stopped.app_id)])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ App ID ] - 232370
        [ Status ] - Removing
        [ Status ] - Remove complete
    ''')


def test_restart(runner, server_running):
    result = runner.invoke(cli.restart, [server_running.app_name])
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


def test_restore(runner, server_stopped):
    server_stopped.backup_dir.mkdir(parents=True, exist_ok=True)
    if len(os.listdir(server_stopped.backup_dir)) < 1:
        server_stopped.backup(compression=None)

    result = runner.invoke(cli.restore, [str(server_stopped.app_id)], input='1\n')
    assert result.exit_code == 0
    assert result.output.split('\n')[-2] == textwrap.dedent('''\
        [ Status ] - Restore complete''')


def test_send(runner, server_running):
    result = runner.invoke(cli.send, ['test', server_running.app_name])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ Status ] - Command sent
        [ Status ] - Command finished
    ''')


def test_setup(runner):
    if Config.config_f.exists() and not Config.system_wide:
        Config.remove()

    result = runner.invoke(cli.setup, input='N\n')
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
         [ ------ ]
         [ Status ] - Creating config files
         [ Status ] - Configs installed
    ''')


def test_start(runner, server_stopped):
    result = runner.invoke(cli.start, [server_stopped.app_name])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
         [ ------ ]
         [ Name   ] - hl2dm
         [ Status ] - Starting
         [ Status ] - Started
    ''')


def test_status(runner, server_running):
    result = runner.invoke(cli.status, [server_running.app_name])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ Status ] - Running
    ''')


def test_stop(runner, server_running):
    result = runner.invoke(cli.stop, [server_running.app_name])
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
        [ ------ ]
        [ Name   ] - hl2dm
        [ Status ] - Stopping
        [ Status ] - Stopped
    ''')


def test_update(runner, app_installed):
    result = runner.invoke(cli.update, [str(app_installed.app_id)])
    assert result.exit_code == 0


@pytest.mark.parametrize('app,result', [
    (('all',), types.GeneratorType),
    (('running',), types.GeneratorType),
    (('backups',), types.GeneratorType)
])
def test_app_special_names(app, result):
    tmp = cli.app_special_names(app)
    assert type(tmp) is result
    assert isinstance(tmp, result)
