from scsm.config import Config


def test_init():
    assert Config.compression == 'gz'


def test_create(system_wide=False):
    Config.create()
    assert Config.config_f.is_file()
