import os
import platform
import shutil
import signal
import sys
from email.mime.text import MIMEText
from pathlib import Path
from smtplib import SMTP
from time import sleep

import click

from .config import Config
from .core import App, Index, Server, SteamCMD


LOGIN_OPTIONS = [
    click.option('-u', '--username', default=Config.username, help='Steam username'),
    click.option('-p', '--password', default=Config.password, help='Steam password'),
    click.option('-g', '--steam-guard', default='', help='Steam guard code'),
]


def add_options(options):
    def wrapper(func):
        for option in reversed(options):
            func = option(func)
        return func
    return wrapper


@click.group()
@click.version_option()
@click.pass_context
def main(ctx):
    signal.signal(signal.SIGINT, signal_handler)

    if ctx.invoked_subcommand != 'setup':
        if not Config.config_f.exists():
            click.echo('[ ------ ]')
            message('Error', 'No config file found')
            ctx.forward(setup)
        Index.update()

    if ctx.invoked_subcommand in ['console', 'kill', 'monitor', 'restart',
                                  'send', 'start', 'status', 'stop']:
        if platform.system() == 'Windows':
            click.echo('[ ------ ]')
            message('Error', 'Not supported on Windows')
            sys.exit(1)

        if not shutil.which('tmux'):
            click.echo('[ ------ ]')
            message('Error', 'Tmux is not installed')
            sys.exit(1)


@main.command()
@click.argument('apps', nargs=-1)
@click.option('-c', '--compression', default=Config.compression, help='Compression method')
@click.option('-f', '--force', is_flag=True, help='Run command even if running')
@click.option('-n', '--no-compress', is_flag=True, help='No compression')
def backup(apps, compression, no_compress, force):
    '''Backup app'''

    if compression and compression not in ['bz2', 'gz', 'xz']:
        message('Error', 'Invalid compression method')
    else:
        if no_compress:
            compression = None

        for app in app_special_names(apps):
            a = app_wrapper(app)
            info(a.app_name, a.app_id)

            if not a.installed:
                message('Error', 'App not installed')
            elif not force and a.running:
                message('Error', 'Stop server before backup')
            else:
                a.backup_dir.mkdir(parents=True, exist_ok=True)
                backups = os.listdir(a.backup_dir)
                length = len(backups)

                if Config.max_backups != 0 and length >= Config.max_backups:
                    message('Status', 'Max backups reached')
                    message('Status', 'Removing old backups')

                    for backup in backups[0:length - Config.max_backups + 1]:
                        Path(a.backup_dir, backup).unlink()

                message('Status', 'Backup started')
                a.backup(compression)
                message('Status', 'Backup complete')


@main.command()
@click.argument('apps', nargs=-1)
def console(apps):
    '''Attach to server session'''

    for app in app_special_names(apps):
        s = server_wrapper(app)
        info(s.server_name)

        if not s.installed:
            message('Error', 'App not installed')
        elif not s.running:
            message('Error', 'Stopped')
        else:
            message('Status', 'Attaching to session')
            s.console()
            message('Status', 'Disconnected from session')


@main.command()
@click.argument('apps', nargs=-1)
@click.option('-e', '--editor', help='Text editor')
def edit(apps, editor):
    '''Edit config files'''

    if apps == ('config',):
        click.edit(editor=editor, filename=Config.config_f)
    else:
        for app in app_special_names(apps):
            a = app_wrapper(app)

            if not a.installed:
                info(a.app_name, a.app_id)
                message('Error', 'App not installed')
            elif a.config_is_default:
                a.copy_config()
                a = App(a.app_id, a.app_dir)
                click.edit(editor=editor, filename=a.config_f)
                Index.update()
            else:
                click.edit(editor=editor, filename=a.config_f)
                Index.update()


@main.command()
@click.argument('apps', nargs=-1)
@add_options(LOGIN_OPTIONS)
@click.pass_context
def install(ctx, apps, username, password, steam_guard):
    '''Install app'''

    if apps == ('steamcmd',):
        steamcmd = SteamCMD()
        if steamcmd.installed:
            message('Error', 'SteamCMD is already installed')

            if steamcmd.exe == 'steamcmd':
                message('Error', 'SteamCMD is not managed by SCSM')
            else:
                text = f'[ {click.style("Status", "green")} ] - Reinstall SteamCMD?'
                if click.confirm(text):
                    steamcmd_install()
        else:
            steamcmd_install()
    else:
        ctx.forward(update)


@main.command()
@click.argument('apps', nargs=-1)
def kill(apps):
    '''Kill server'''

    for app in app_special_names(apps, server=True):
        s = server_wrapper(app)
        info(s.server_name)

        if not s.installed:
            message('Error', 'App not installed')
        elif not s.running:
            message('Error', 'Stopped')
        else:
            message('Status', 'Killing')
            s.kill()
            message('Status', 'Stopped')


@main.command()
@click.argument('apps', nargs=-1)
def list(apps):
    '''List installed or all installable apps'''

    arg = None

    if apps == ('all',):
        apps = Index.list_all()
    elif apps == ('backups',):
        arg = 'backups'

    for app in app_special_names(apps):
        a = app_wrapper(app)

        click.echo('[ ------ ]')
        message('F-Name', a.full_name)
        message('Name', a.app_name)
        message('App ID', a.app_id)

        if a.installed:
            message('Status', 'Installed')
        else:
            message('Status', 'Not installed')

        if arg == 'backups':
            message('Status', f'Backups (Max {Config.max_backups})')

            backups = os.listdir(a.backup_dir)
            backups.sort(reverse=True)

            for i, backup in enumerate(backups):
                message(i + 1, backup)


@main.command()
@click.argument('apps', nargs=-1)
@click.option('-e', '--email', is_flag=True, help='Email')
@click.option('-r', '--restart', is_flag=True, help='Restart if stopped')
def monitor(apps, email, restart):
    '''Monitor server status'''

    sessions = {}

    for app in app_special_names(apps, server=True):
        try:
            s = Server(app, Config.app_dir)
        except FileNotFoundError:
            info(app)
            message('Error', 'No server entry')
        else:
            if s.server_name:
                sessions[s.session_name] = {}
            else:
                for server_name in s.server_names:
                    sessions[f'{s.app_name}-{server_name}'] = {}

    sessions = {session: {'running': False, 'restarts': 0, 'time': 0}
                for session in sessions}

    while sessions:
        for session in sessions:
            app_name, server_name = session.split('-')

            if sessions[session]['running']:
                if not Server.running_check(app_name, server_name):
                    sessions[session]['running'] = False

                    info(server_name)
                    message('Status', 'Stopped')

                    if restart:
                        if sessions[session]['restarts'] == 3:
                            message('Error', 'Restarted 3 times in 30 seconds')
                            message('Error', 'Not restarting')

                            if email:
                                from_addr = 'scsm@localhost'
                                to_addr = f'{os.getlogin()}@localhost'
                                text = f''''Server {session} has been restarted more
                                        than 3 times in 30  seconds and will
                                        not be restarted'''

                                msg = MIMEText(text)
                                msg['Subject'] = 'SCSM - Monitor'
                                msg['From'] = from_addr
                                msg['To'] = to_addr

                                e = SMTP('localhost')
                                e.sendmail(from_addr, to_addr, msg.as_string())
                                e.quit()

                        else:
                            sessions[session]['restarts'] += 1
                            start(server_name)
            else:
                if Server.running_check(app_name, server_name):
                    sessions[session]['running'] = True

                    info(server_name)
                    message('Status', 'Running')

            if sessions[session]['time'] == 30:
                sessions[session]['restarts'] = 0
                sessions[session]['time'] = 0
            elif sessions[session]['restarts'] != 0:
                sessions[session]['time'] += 1

        sleep(1)


@main.command()
@click.argument('apps', nargs=-1)
@click.option('-f', '--force', is_flag=True, help='Run command even if running')
def remove(apps, force):
    '''Remove app'''

    if apps == ('steamcmd',):
        steamcmd = SteamCMD()
        if steamcmd.exe == 'steamcmd':
            message('Error', 'SteamCMD is not managed by SCSM')
        else:
            steamcmd.remove()
            message('Status', 'SteamCMD removed')

    else:
        for app in app_special_names(apps):
            a = app_wrapper(app)
            info(a.app_name, a.app_id)

            if not a.installed:
                message('Error', 'App not installed')
            elif not force and a.running:
                message('Error', 'Stop server before validating')
            else:
                message('Status', 'Removing')
                a.remove()
                message('Status', 'Remove complete')


@main.command()
@click.argument('apps', nargs=-1)
@click.option('-w', '--wait-time', type=int, default=Config.wait_time, help='Wait time')
@click.pass_context
def restart(ctx, apps, wait_time):
    '''Restart server'''

    for app in app_special_names(apps, server=True):
        ctx.invoke(stop, apps=[app], wait_time=wait_time)
        ctx.invoke(start, apps=[app], attach=False, debug=False)


@main.command()
@click.argument('apps', nargs=-1)
@click.option('-f', '--force', is_flag=True, help='Run command even if running')
@click.option('-l', '--latest', is_flag=True, help='Select the latest backup automatically')
def restore(apps, force, latest):
    '''Restore app from backup'''

    for app in app_special_names(apps):
        a = app_wrapper(app)
        info(a.app_name, a.app_id)

        if not a.backup_dir.exists() or not os.listdir(a.backup_dir):
            message('Error', 'No backups found')
        elif not force and a.running:
            message('Error', 'Stop server before restoring')
        else:
            backups = os.listdir(a.backup_dir)
            backups.sort(reverse=True)
            length = len(backups)

            while length > 1 and not latest:
                message('Status', 'Backups')
                for i, backup in enumerate(backups):
                    message(i + 1, backup)
                answer = int(input(f'[ {click.style("Status", "green")} ] - Choose one: '))

                if answer > length or answer < 1:
                    message('Error', 'Invalid selection')
                    click.echo('[ ------ ]')
                else:
                    backup = backups[answer - 1]
                    break
            else:
                backup = backups[0]

            a.app_dir.mkdir(parents=True, exist_ok=True)
            message('Status', 'Restoring')
            a.restore(backup)
            message('Status', 'Restore complete')


@main.command()
@click.argument('command')
@click.argument('apps', nargs=-1)
def send(apps, command):
    '''Send command to server'''

    for app in app_special_names(apps, server=True):
        s = server_wrapper(app)
        info(s.server_name)

        if not s.installed:
            message('Error', 'App not installed')
        elif not s.running:
            message('Error', 'Stopped')
        else:
            message('Status', 'Command sent')
            s.send(command)
            message('Status', 'Command finished')


@main.command()
@click.option('-s', '--system-wide', is_flag=True, default=False, help='System wide config')
def setup(system_wide):
    '''Setup SteamCMD and config files'''

    click.echo('[ ------ ]')

    if Config.config_f and Config.config_f.exists():
        if not system_wide and Config.system_wide:
            message('Status', 'Creating config files')
            Config.create(system_wide)
            message('Status', 'Configs installed')
        else:
            message('Error', 'Config file already exists')

            if click.confirm(f'[ {click.style("Status", "green")} ] - Overwrite config?'):
                message('Status', 'Creating config files')
                message('Status', 'Configs installed')
                Config.create(system_wide)
    else:
        message('Status', 'Creating config files')
        Config.create(system_wide)
        message('Status', 'Configs installed')

    for d in Config.app_dir, Config.backup_dir:
        d.mkdir(parents=True, exist_ok=True)


@main.command()
@click.argument('apps', nargs=-1)
@click.option('-a', '--attach', is_flag=True, help='Attach to starting server session')
@click.option('-d', '--debug', is_flag=True, help='Debug mode')
def start(apps, attach, debug):
    '''Start server'''

    for app in app_special_names(apps, server=True):
        s = server_wrapper(app)
        info(s.server_name)

        if not s.installed:
            message('Error', 'App not installed')
        elif s.running:
            message('Error', 'Already running')
        else:
            message('Status', 'Starting')
            s.start(debug)
            message('Status', 'Started')

            if attach or debug:
                s.console()
            if debug and s.running:
                # kill any left open tmux debugging session
                message('Status', 'Killing')
                s.kill()
                message('Status', 'Stopped')


@main.command()
@click.argument('apps', nargs=-1)
def status(apps):
    '''Status server'''

    for app in app_special_names(apps, server=True):
        s = server_wrapper(app)
        info(s.server_name)
        if not s.installed:
            message('Error', 'App not installed')
        elif s.running:
            message('Status', 'Running')
        else:
            message('Status', 'Stopped')


@main.command()
@click.argument('apps', nargs=-1)
@click.option('-w', '--wait-time', type=int, default=Config.wait_time, help='Wait time')
def stop(apps, wait_time):
    '''Stop server'''

    for app in app_special_names(apps, server=True):
        s = server_wrapper(app)
        info(s.server_name)

        if not s.installed:
            message('Error', 'App not installed')
        elif not s.running:
            message('Error', 'Stopped')
        else:
            message('Status', 'Stopping')
            s.stop()

            for i in range(int(wait_time)):
                if not s.running:
                    break
                sleep(1)
            else:
                message('Error', f'Waited {wait_time} seconds')
                message('Error', 'Killing')
                s.kill()

            message('Status', 'Stopped')


@main.command()
@click.argument('apps', nargs=-1)
@add_options(LOGIN_OPTIONS)
@click.option('-f', '--force', is_flag=True, help='Run command even if running')
@click.option('-vv', '--validate', is_flag=True, default=False, help='Validate after update')
def update(apps, username, password, steam_guard, force, validate):
    '''Update app'''

    for app in app_special_names(apps):
        a = app_wrapper(app)
        steamcmd_check()
        info(a.app_name, a.app_id)

        if not force and a.running:
            message('Error', 'Stop server before update')
        elif not a.installed:
            # no subscription installs leave games partially installed
            message('Status', 'Checking for license')
            steamcmd = SteamCMD()
            if steamcmd.license(a.app_id, username, password, steam_guard):
                message('Status', 'Installing')
                exit_code = a.update(username, password, steam_guard, validate)

                if exit_code == 0:
                    message('Status', 'Installed')
                else:
                    message('Error', 'Install failed')
            else:
                message('Error', 'No subscription')
        else:
            if validate:
                message('Status', 'Updating and Validating')
            else:
                message('Status', 'Updating')

            exit_code = a.update(username, password, steam_guard, validate)

            if exit_code == 0:
                message('Status', 'Updated')
            else:
                message('Error', 'Update failed')


def app_wrapper(app):
    try:
        a = App(app, Config.app_dir, Config.backup_dir)
    except FileNotFoundError:
        click.echo('[ ------ ]')

        try:
            int(app)
        except ValueError:
            message('Name', app)
            message('Error', 'Invalid app name')
        else:
            message('App ID', app)
            message('Error', 'Invalid app id')
        sys.exit(1)
    else:
        return a


def server_wrapper(app):
    try:
        s = Server(app, Config.app_dir)
    except FileNotFoundError:
        click.echo('[ ------ ]')

        try:
            int(app)
        except ValueError:
            message('Name', app)
            message('Error', 'Invalid app or server name')
        else:
            message('App ID', app)
            message('Error', 'Invalid app id')
        sys.exit(1)
    else:
        return s


def app_special_names(apps, server=False):
    if apps in [('all',), ('installed',)]:
        if server:
            apps = server_expand_names(Index.list(Config.app_dir))
        else:
            apps = Index.list(Config.app_dir)
    elif apps in [('running',), ('stopped',)]:
        status = apps[0]
        apps = []
        for app in Index.list(Config.app_dir):
            s = Server(app, Config.app_dir)

            if s.running:
                for server in s.server_names:
                    if Server.running_check(s.app_name, server):
                        if status == 'running':
                            apps.append(server)
                    else:
                        if status == 'stopped':
                            apps.append(server)
            else:
                if status == 'stopped':
                    apps.append(app)
    elif apps == ('backups',):
        apps = Index.list(Config.backup_dir)
    elif server:
        apps = server_expand_names(apps)

    for app in apps:
        yield app


def server_expand_names(apps):
    for app in apps:
        try:
            s = Server(app, Config.app_dir)
        except FileNotFoundError:
            yield app
        else:
            if s.server_name == s.app_name or app == s.app_id:
                for server in s.server_names:
                    yield server
            else:
                yield app


def info(name, app_id=None):
    click.echo('[ ------ ]')
    message('Name', name)
    if app_id:
        message('App ID', app_id)


def message(title, text):
    if title in ['Name', 'App ID', 'F-Name']:
        color = 'yellow'
    elif title in ['Status', 'Done']:
        color = 'green'
    elif title in ['Error', 'Alert']:
        color = 'red'
    else:
        color = 'white'

    click.echo(f'[ {click.style(str(title).ljust(6), color)} ] - {text}')


def signal_handler(signal, frame):
    click.echo(' ')
    message('Status', 'Quitting')
    sys.exit(0)


def steamcmd_check():
    steamcmd = SteamCMD()
    if not steamcmd.installed:
        click.echo('[ ------ ]')
        message('Error', 'SteamCMD not installed')
        steamcmd_install()

    if not steamcmd.installed:
        sys.exit(1)


def steamcmd_install():
    click.echo('[ ------ ]')
    message('Status', 'SteamCMD installing')

    steamcmd = SteamCMD()
    steamcmd.install()
    message('Status', 'SteamCMD installed')

    message('Status', 'SteamCMD updating')
    exit_code, text = steamcmd.update()

    if exit_code == 0:
        message('Status', 'SteamCMD updated')
    else:
        message('Error', text)
