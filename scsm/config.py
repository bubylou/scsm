import os
import platform
from pkg_resources import resource_filename
from ruamel.yaml import YAML


if platform.system() != 'Windows':
    if os.geteuid() == 0:
        BASE_DIR = '/opt/scsm'
    else:
        BASE_DIR = os.path.expanduser('~/.local/share/scsm')
else:
    BASE_DIR = os.path.join(os.getenv('APPDATA'), 'scsm')


DEFAULTS = f"""
    general:
        compression: gz
        steam_guard: true
        verbose: false
        max_backups: 5
        wait_time: 30
    directories:
        app_dir: {os.path.join(BASE_DIR, 'apps')}
        backup_dir: {os.path.join(BASE_DIR, 'backups')}
    steam:
        username: anonymous
        password:
    """


class Config():
    system_wide = False
    data_dir = resource_filename(__name__, 'data')

    if platform.system() != 'Windows':
        config_dir = os.path.expanduser('~/.config/scsm')
        if not os.path.exists(config_dir) and os.path.exists('/etc/scsm'):
            system_wide = True
            config_dir = '/etc/scsm'
    else:
        config_dir = os.path.join(os.getenv('APPDATA'), 'scsm')

    _yaml = YAML(typ='safe')

    config_f = os.path.join(config_dir, 'config.yaml')

    if os.path.isfile(config_f):
        with open(config_f, 'r') as _f:
            data = _yaml.load(_f)
    else:
        data = _yaml.load(DEFAULTS)

    compression = data['general']['compression']
    steam_guard = data['general']['steam_guard']
    verbose = data['general']['verbose']
    max_backups = data['general']['max_backups']
    wait_time = data['general']['wait_time']
    app_dir = data['directories']['app_dir']
    backup_dir = data['directories']['backup_dir']
    username = data['steam']['username']
    password = data['steam']['password']

    @staticmethod
    def create(system_wide=False):
        if platform.system() != 'Windows':
            if system_wide:
                config_dir = '/etc/scsm'
            else:
                config_dir = os.path.expanduser('~/.config/scsm')
        else:
            config_dir = os.path.join(os.getenv('APPDATA'), 'scsm')

        if not os.path.exists(config_dir):
            os.makedirs(os.path.join(config_dir, 'apps'))

        Config.config_dir = config_dir
        Config.config_f = os.path.join(config_dir, 'config.yaml')

        with open(os.path.join(config_dir, 'config.yaml'), 'w') as f:
            yaml = YAML(typ='safe')
            yaml.dump(yaml.load(DEFAULTS), f)
