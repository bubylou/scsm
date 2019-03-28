import os
from scsm.config import Config


def test_init():
    assert Config.verbose is False


def test_create(system_wide=False):
    Config.create()
    assert os.path.isfile(Config.config_f)
