import os
from pathlib import Path
import pytest
from time import sleep

from scsm.core import App, Index, Server, SteamCMD
from scsm.config import Config


APP_DIR = Path('~/.local/share/scsm/apps').expanduser()
APP_ID = 232370
APP_ID_FAIL = 380840
APP_NAME = 'hl2dm'
BACKUP_DIR = Path('~/.local/share/scsm/backups').expanduser()

Config.create()
Index.update()


@pytest.fixture(scope='class')
def app():
    app = App(APP_ID, APP_DIR, BACKUP_DIR)

    if app.installed:
        app.remove()

    steamcmd = SteamCMD()
    if not steamcmd.installed:
        steamcmd.install()
        steamcmd.update()

    return app


class TestApp():
    @pytest.mark.parametrize('app,app_name', [
        (APP_ID, APP_NAME),
        (f'{APP_ID}', APP_NAME),
        (APP_NAME, APP_NAME),
    ])
    def test_init(self, app, app_name):
        a = App(app, APP_DIR, BACKUP_DIR)
        assert a.app_name == app_name

    def test_build_id_steam(self, app):
        assert app.build_id_steam > 0

    def test_installed(self, app):
        assert app.installed is False

    def test_running(self, app):
        assert app.running is False

    def test_update(self, app):
        exit_code, text = app.update()
        assert exit_code == 0

    def test_build_id_local_success(self, app):
        assert app.build_id_local > 0

    def test_build_id_local_failure(self):
        app = App(APP_ID_FAIL, APP_DIR, BACKUP_DIR)
        assert app.build_id_local == 0

    def test_backup_gz(self, app):
        app.backup_dir.mkdir(parents=True, exist_ok=True)
        backups = os.listdir(app.backup_dir)
        app.backup(compression='gz')
        assert len(os.listdir(app.backup_dir)) > len(backups)

    def test_backup_tar(self, app):
        app.backup_dir.mkdir(parents=True, exist_ok=True)
        backups = os.listdir(app.backup_dir)
        app.backup(compression=None)
        assert len(os.listdir(app.backup_dir)) > len(backups)

    def test_copy_config(self, app):
        app.copy_config()
        assert app.config_is_default is False

    def test_remove(self, app):
        app.remove()
        assert app.installed is False

    def test_restore(self, app):
        backups = os.listdir(app.backup_dir)
        app.restore(backups[0])
        assert app.installed is True


class TestIndex():
    def test_list(self):
        assert len(list(Index.list(APP_DIR))) > 0

    def test_list_all(self):
        assert len(list(Index.list_all())) > 0

    def test_update(self):
        Index.f.unlink()
        Index.update()
        assert Index.f.is_file()

    @pytest.mark.parametrize('app,result', [
        (APP_ID, (APP_ID, None, None)),
        (f'{APP_ID}', (APP_ID, None, None)),
        (APP_NAME, (APP_ID, APP_NAME, APP_NAME)),
    ])
    def test_search(self, app, result):
        assert Index.search(app) == result


@pytest.fixture
def server(scope='class'):
    Index.update()
    server = Server(APP_NAME, APP_DIR)

    if not server.installed:
        steamcmd = SteamCMD()
        if not steamcmd.installed:
            steamcmd.install()
            steamcmd.update()
        server.update()
    elif server.running:
        server.stop()

    return server


class TestServer():
    def test_init(self, server):
        assert server.server_name == APP_NAME

    def test_running(self, server):
        assert server.running is False

    def test_running_check(self, server):
        assert server.running_check(APP_NAME) is False

    def test_start(self, server):
        server.start()
        sleep(5)
        assert server.running is True

    def test_console(self, server):
        assert True

    def test_send(self, server):
        assert server.send('test') == 0

    def test_stop(self, server):
        if not server.running:
            server.start()

        server.stop()

        for i in range(10):
            if not server.running:
                break
            sleep(1)

        assert server.running is False

    def test_kill(self, server):
        if not server.running:
            server.start()

        server.kill()

        for i in range(10):
            if not server.running:
                break
            sleep(1)

        assert server.running is False


@pytest.fixture
def steamcmd(scope='class'):
    steamcmd = SteamCMD()
    return steamcmd


class TestSteamCMD():
    def test_install(self, steamcmd):
        if steamcmd.installed and steamcmd.exe != 'steamcmd':
            steamcmd.remove()

        steamcmd.install()
        assert steamcmd.installed is True

    def test_update(self, steamcmd):
        exit_code, text = steamcmd.update()
        assert exit_code == 0

    def test_is_installed(self, steamcmd):
        assert steamcmd.installed is True

    def test_app_update(self, steamcmd):
        d = Path(APP_DIR, str(APP_ID), APP_NAME)
        exit_code, text = steamcmd.app_update(APP_ID, d)
        assert exit_code == 0

    def test_cached_login(self, steamcmd):
        assert steamcmd.cached_login('anonymous') is False

    def test_filter(self, steamcmd):
        exit_code, text = steamcmd.filter(['echo', 'Success'])
        assert exit_code == 0

    def test_info(self, steamcmd):
        assert type(steamcmd.info(APP_ID)) is dict

    def test_license_true(self, steamcmd):
        assert steamcmd.license(APP_ID) is True

    def test_license_false(self, steamcmd):
        assert steamcmd.license(380840) is False

    def test_run(self, steamcmd):
        exit_code, text = steamcmd.run(['+quit'], verbose=False)
        assert exit_code == 0

    def test_run_verbose(self, steamcmd):
        exit_code, text = steamcmd.run(['+quit'], verbose=True)
        assert exit_code == 0

    def test_remove(self, steamcmd):
        steamcmd.remove()
        assert steamcmd.installed is False
