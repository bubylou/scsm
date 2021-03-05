import os
import platform
from pathlib import Path
from pkg_resources import resource_filename
from ruamel.yaml import YAML


if platform.system() != 'Windows':
    if os.geteuid() == 0:
        BASE_DIR = Path('/opt/scsm')
    else:
        BASE_DIR = Path('~/.local/share/scsm').expanduser()
else:
    BASE_DIR = Path(os.getenv('APPDATA'), 'scsm')


DEFAULTS = f"""
    general:
        compression: gz
        steam_guard: true
        max_backups: 5
        wait_time: 30
    directories:
        app_dir: {Path(BASE_DIR, 'apps')}
        backup_dir: {Path(BASE_DIR, 'backups')}
    steam:
        username: anonymous
        password:
    """


class Config():
    system_wide = False
    data_dir = resource_filename(__name__, 'data')

    if platform.system() != 'Windows':
        config_dir = Path('~/.config/scsm').expanduser()
        if not config_dir.exists() and Path('/etc/scsm').exists():
            system_wide = True
            config_dir = Path('/etc/scsm')
    else:
        config_dir = Path(os.getenv('APPDATA'), 'scsm')

    _yaml = YAML(typ='safe')
    config_f = Path(config_dir, 'config.yaml')

    if config_f.exists():
        with open(config_f, 'r') as _f:
            data = _yaml.load(_f)
    else:
        data = _yaml.load(DEFAULTS)

    compression = str(data['general']['compression'])
    steam_guard = str(data['general']['steam_guard'])
    max_backups = int(data['general']['max_backups'])
    wait_time = int(data['general']['wait_time'])
    app_dir = Path(data['directories']['app_dir'])
    backup_dir = Path(data['directories']['backup_dir'])
    username = str(data['steam']['username'])
    password = str(data['steam']['password'])

    @staticmethod
    def create(system_wide=False):
        if platform.system() != 'Windows':
            if system_wide:
                config_dir = Path('/etc/scsm')
            else:
                config_dir = Path('~/.config/scsm').expanduser()
        else:
            config_dir = Path(os.getenv('APPDATA'), 'scsm')

        Path(config_dir, 'apps').mkdir(parents=True, exist_ok=True)
        Config.config_dir = config_dir
        Config.config_f = Path(config_dir, 'config.yaml')

        with open(Path(config_dir, 'config.yaml'), 'w') as f:
            yaml = YAML(typ='safe')
            yaml.dump(yaml.load(DEFAULTS), f)

    @staticmethod
    def remove():
        Config.config_f.unlink()
