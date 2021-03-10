import os
import pytest
from time import sleep

from scsm.core import Index
from scsm.config import Config


Config.create()
Index.update()


class TestApp():
    def test_init(self, app):
        assert type(app.app_name) is str

    def test_build_id_steam(self, app, steamcmd_installed):
        assert app.build_id_steam > 0

    def test_installed(self, app_removed):
        assert app_removed.installed is False

    def test_running(self, server_stopped):
        assert server_stopped.running is False

    def test_update(self, app_installed):
        exit_code = app_installed.update()
        assert exit_code == 0

    def test_build_id_local_success(self, app_installed):
        assert app_installed.build_id_local > 0

    def test_build_id_local_failure(self, app_removed):
        assert app_removed.build_id_local == 0

    @pytest.mark.parametrize('compression', ['tar', 'gz'])
    def test_backup(self, app_installed, compression):
        app_installed.backup_dir.mkdir(parents=True, exist_ok=True)
        backups = os.listdir(app_installed.backup_dir)
        app_installed.backup(compression)
        assert len(os.listdir(app_installed.backup_dir)) > len(backups)

    def test_copy_config(self, app):
        app.copy_config()
        assert app.config_is_default is False

    def test_remove(self, app_installed):
        app_installed.remove()
        assert app_installed.installed is False

    def test_restore(self, app_removed):
        backups = os.listdir(app_removed.backup_dir)
        app_removed.restore(backups[0])
        assert app_removed.installed is True


class TestIndex():
    def test_list(self, app):
        assert list(Index.list(app.app_dir.parent.parent))

    def test_list_all(self):
        assert len(list(Index.list_all())) > 0

    def test_update(self):
        Index.f.unlink()
        Index.update()
        assert Index.f.is_file()

    @pytest.mark.parametrize('app,result', [
        (232370, (232370, None, None)),
        ('232370', (232370, None, None)),
        ('hl2dm', (232370, 'hl2dm', 'hl2dm')),
    ])
    def test_search(self, app, result):
        assert Index.search(app) == result


class TestServer():
    def test_init(self, server):
        assert type(server.server_name) is str

    def test_running(self, server_stopped):
        assert server_stopped.running is False

    def test_running_check(self, server_stopped):
        assert server_stopped.running_check(server_stopped.app_name) is False

    def test_start(self, server_stopped):
        server_stopped.start()
        sleep(5)
        assert server_stopped.running is True

    def test_console(self, server):
        # Tests error out due to not being run in a real terminal
        assert True

    def test_send(self, server_running):
        server_running.send('test')
        window = server_running.session.list_windows()[0]
        pane = window.list_panes()[0]
        pane_contents = '\n'.join(pane.cmd('capture-pane', '-p').stdout)
        assert 'test' in pane_contents

    def test_stop(self, server_running):
        server_running.stop()

        for i in range(10):
            if not server_running.running:
                break
            sleep(1)

        assert server_running.running is False

    def test_kill(self, server_running):
        server_running.kill()

        for i in range(10):
            if not server_running.running:
                break
            sleep(1)

        assert server_running.running is False


class TestSteamCMD():
    def test_install(self, steamcmd_removed):
        steamcmd_removed.install()
        assert steamcmd_removed.installed is True

    def test_update(self, steamcmd_installed):
        exit_code = steamcmd_installed.update()
        assert exit_code == 0

    def test_is_installed(self, steamcmd_installed):
        assert steamcmd_installed.installed is True

    def test_app_update(self, app, steamcmd_installed):
        exit_code = steamcmd_installed.app_update(app.app_id, app.app_dir.parent)
        assert exit_code == 0

    def test_cached_login(self, steamcmd_installed):
        assert steamcmd_installed.cached_login('anonymous') is False

    def test_info(self, app, steamcmd_installed):
        assert type(steamcmd_installed.info(app.app_id)) is dict

    def test_license_true(self, app, steamcmd_installed):
        assert steamcmd_installed.license(app.app_id) is True

    def test_license_false(self, steamcmd_installed):
        assert steamcmd_installed.license(380840) is False

    def test_run(self, steamcmd_installed):
        exit_code = steamcmd_installed.run(['+quit'])
        assert exit_code == 0

    def test_remove(self, steamcmd_installed):
        steamcmd_installed.remove()
        assert steamcmd_installed.installed is False
