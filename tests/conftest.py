from pathlib import Path
from time import sleep
import pytest
from scsm.core import App, Server, SteamCMD

APP_ID = 232370
APP_NAME = 'hl2dm'
APP_ID_FAIL = 380840
APP_NAME_FAIL = 'teeworld'

APP_DIR = Path('~/.local/share/scsm/apps').expanduser()
BACKUP_DIR = Path('~/.local/share/scsm/backups').expanduser()


@pytest.fixture
def app():
    app = App(APP_ID, APP_DIR, BACKUP_DIR)
    return app


@pytest.fixture
def app_installed(app, steamcmd_installed):
    if not app.installed:
        app.update()
    return app


@pytest.fixture
def app_removed(app, server_stopped):
    if app.installed:
        app.remove()
    return app


@pytest.fixture
def server():
    server = Server(APP_NAME, APP_DIR, BACKUP_DIR)
    return server


@pytest.fixture
def server_running(server, app_installed):
    if not server.running:
        server.start()
        sleep(5)
    return server


@pytest.fixture
def server_stopped(server, app_installed):
    if server.running:
        server.stop()
        for _ in range(10):
            if not server.running:
                break
            sleep(1)
        else:
            server.kill()
    return server


@pytest.fixture
def steamcmd():
    steamcmd = SteamCMD()
    return steamcmd


@pytest.fixture
def steamcmd_installed(steamcmd):
    if not steamcmd.installed:
        steamcmd.install()
        steamcmd.update()
    return steamcmd


@pytest.fixture
def steamcmd_removed(steamcmd):
    if steamcmd.installed and steamcmd.exe != 'steamcmd':
        steamcmd.remove()
    return steamcmd
