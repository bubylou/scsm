# SteamCMD Server Manager ( SCSM )
[![PyPi version](https://img.shields.io/pypi/v/scsm.svg)](https://pypi.org/project/scsm/)
[![Actions Status: CI](https://github.com/bubylou/scsm/actions/workflows/tests.yml/badge.svg)](https://github.com/bubylou/scsm/actions?query=workflow)
[![Codecov coverage](https://img.shields.io/codecov/c/github/bubylou/scsm.svg)](https://codecov.io/gh/bubylou/scsm)
[![PyUp status](https://pyup.io/repos/github/bubylou/scsm/shield.svg)](https://pyup.io/repos/github/bubylou/scsm)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

SCSM is a python program used to manage SteamCMD servers. It includes a core library, basic configuration file management, and a command line interface.

## Features

- Backup / Restore
- Install / Update / Validate
- Start / Stop / Restart / Kill
- Monitor running servers
- Multiple server support

## Requirments

- python (3.6+)
- pip
- screen
- steamcmd

If SteamCMD is not available in your repository you can install it through SCSM itself by using the `scsm install steamcmd` command.

## Install

Install using pip.
```
pip install scsm
```

## Basic Usage

```
scsm setup
scsm install gmod
scsm start gmod
scsm --help
```
