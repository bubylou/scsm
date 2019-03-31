import os
import platform
import shutil
import signal
import sys
from email.mime.text import MIMEText
from smtplib import SMTP
from time import sleep

import click

from .config import Config
from .core import App, Index, Server, SteamCMD

APP_OPTIONS = [
    click.option('-f', '--force', is_flag=True, help='Run command even if running'),
    click.option('-r', '--restart', 'arg', flag_value='restart', help='Restart during command'),
    click.option('-i', '--start', 'arg', flag_value='start', help='Start after command'),
    click.option('-s', '--stop', 'arg', flag_value='stop', help='Stop before command')
]

LOGIN_OPTIONS = [
    click.option('-u', '--username', default=Config.username, help='Steam username'),
    click.option('-p', '--password', default=Config.password, help='Steam password'),
    click.option('-g', '--steam-guard', default='', help='Steam guard code'),
    click.option('-v', '--verbose', is_flag=True, default=Config.verbose, help='Verbose mode')
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
        if not os.path.isfile(Config.config_f):
            click.echo('[ ------ ]')
            message('Error', 'No config file found')
            ctx.forward(setup_cmd)
        Index.update()

    if ctx.invoked_subcommand in ['console', 'kill', 'monitor', 'restart',
                                  'send', 'start', 'status', 'stop']:
        if platform.system() == 'Windows':
            click.echo('[ ------ ]')
            message('Error', 'Not supported on Windows')
            sys.exit(1)

        if not shutil.which('screen'):
            click.echo('[ ------ ]')
            message('Error', 'GNU Screen is not installed')
            sys.exit(1)


@main.command(name='backup')
@click.argument('apps', nargs=-1)
@add_options(APP_OPTIONS)
@click.option('-c', '--compression', default=Config.compression, help='Compression method')
@click.option('-n', '--no-compress', is_flag=True, help='No compression')
def backup_cmd(apps, arg, compression, no_compress, force):
    '''Backup app'''

    if compression and compression not in ['bz2', 'gz', 'xz']:
        message('Error', 'Invalid compression method')
    else:
        if no_compress:
            compression = None

        for app in app_special_names(apps):
            backup(app, arg, compression, force)


@main.command(name='console')
@click.argument('apps', nargs=-1)
def console_cmd(apps):
    '''Attach to server session'''

    for app in app_special_names(apps):
        console(app)


@main.command(name='edit')
@click.argument('apps', nargs=-1)
@click.option('--editor', help='Text editor')
def edit_cmd(apps, editor):
    '''Edit config files'''

    if apps == ('config',):
        click.edit(editor=editor, filename=Config.config_f)
    else:
        for app in app_special_names(apps):
            edit(app, editor)


@main.command(name='install')
@click.argument('apps', nargs=-1)
@add_options(LOGIN_OPTIONS)
@click.option('-i', '--start', 'arg', flag_value='start', help='Start after command')
@click.pass_context
def install_cmd(ctx, apps, arg, username, password, steam_guard, verbose):
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
                    steamcmd_install(verbose)
        else:
            steamcmd_install(verbose)
    else:
        ctx.forward(update_cmd)


@main.command(name='kill')
@click.argument('apps', nargs=-1)
def kill_cmd(apps):
    '''Kill server'''

    for app in app_special_names(apps):
        kill(app)


@main.command(name='list')
@click.argument('apps', nargs=-1)
def list_cmd(apps):
    '''List installed or all installable apps'''

    arg = None

    if apps == ('all',):
        apps = Index.list_all()
    elif apps == ('backups',):
        arg = 'backups'

    for app in app_special_names(apps):
        _list(app, arg)


@main.command(name='monitor')
@click.argument('apps', nargs=-1)
@click.option('-e', '--email', is_flag=True, help='Email')
@click.option('-r', '--restart', is_flag=True, help='Restart if stopped')
def monitor_cmd(apps, email, restart):
    '''Monitor server status'''

    sessions = {}

    for app in app_special_names(apps):
        try:
            s = Server(app, Config.app_dir)
        except FileNotFoundError:
            info(app)
            message('Error', 'No server entry')
        else:
            if s.server_name:
                sessions[s.session] = {}
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


@main.command(name='remove')
@click.argument('apps', nargs=-1)
@click.option('-f', '--force', is_flag=True, help='Run command even if running')
@click.option('-s', '--stop', 'arg', flag_value='stop', help='Stop before command')
def remove_cmd(apps, arg, force):
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
            remove(app, arg, force)


@main.command(name='restart')
@click.argument('apps', nargs=-1)
@click.option('-w', '--wait-time', type=int, default=Config.wait_time, help='Wait time')
def restart_cmd(apps, wait_time):
    '''Restart server'''

    for app in app_special_names(apps):
        stop(app, wait_time)
        start(app, debug=False, verbose=False)


@main.command(name='restore')
@click.argument('apps', nargs=-1)
@add_options(APP_OPTIONS)
def restore_cmd(apps, arg, force):
    '''Restore app from backup'''

    for app in app_special_names(apps):
        restore(app, arg, force)


@main.command(name='send')
@click.argument('command')
@click.argument('apps', nargs=-1)
def send_cmd(apps, command):
    '''Send command to server'''

    for app in app_special_names(apps):
        send(app, command)


@main.command(name='setup')
@click.option('-s', '--system-wide', is_flag=True, default=False, help='System wide config')
def setup_cmd(system_wide):
    '''Setup SteamCMD and config files'''

    click.echo('[ ------ ]')

    if Config.config_f and os.path.isfile(Config.config_f):
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
        if not os.path.exists(d):
            os.makedirs(d)


@main.command(name='start')
@click.argument('apps', nargs=-1)
@click.option('-d', '--debug', is_flag=True, help='Debug mode')
@click.option('-v', '--verbose', is_flag=True, default=Config.verbose, help='Verbose mode')
def start_cmd(apps, debug, verbose):
    '''Start server'''

    for app in app_special_names(apps):
        start(app, debug, verbose)


@main.command(name='status')
@click.argument('apps', nargs=-1)
def status_cmd(apps):
    '''Status server'''

    for app in app_special_names(apps):
        status(app)


@main.command(name='stop')
@click.argument('apps', nargs=-1)
@click.option('-w', '--wait-time', type=int, default=Config.wait_time, help='Wait time')
def stop_cmd(apps, wait_time):
    '''Stop server'''

    for app in app_special_names(apps):
        stop(app, wait_time)


@main.command(name='update')
@click.argument('apps', nargs=-1)
@add_options(APP_OPTIONS)
@add_options(LOGIN_OPTIONS)
@click.option('-c', '--check-only', is_flag=True, help='Check for an update only')
@click.option('-n', '--no-check', is_flag=True, help='Don\'t check for an update')
@click.option('-vv', '--validate', is_flag=True, default=False, help='Validate after update')
def update_cmd(apps, arg, username, password, steam_guard,
               check_only, no_check, force, validate, verbose):
    '''Update app'''

    if username != 'anonymous' and not verbose:
        click.echo('[ ------ ]')
        message('Status', 'Checking for cached credentials')

        steamcmd = SteamCMD()
        if not steamcmd.cached_login(username):
            message('Status', 'Cached credentials not available')
            message('Alert', 'Login info can be read in OS process list')
            message('Alert', 'To avoid this use -v or --verbose')

            if not password:
                password = click.prompt('password: ', hide_input=True)
            if not steam_guard:
                steam_guard = click.prompt('steam guard: ',)
        else:
            message('Status', 'Using cached credentials')
            password = steam_guard = ''
    else:
        password = steam_guard = ''

    for app in app_special_names(apps):
        update(app, arg, username, password, steam_guard,
               check_only, no_check, force, validate, verbose)


def run(func):
    def wrapper(a, arg, *args, **kwargs):
        stopped = []

        if arg in ['restart', 'stop']:
            try:
                server_names = Server(a.app_name, Config.app_dir).server_names
            except FileNotFoundError:
                pass
            else:
                for server_name in server_names:
                    if Server.running_check(a.app_name, server_name):
                        print(a.app_name, server_name)
                        stopped.append(server_name)
                        stop(server_name, Config.wait_time)
        elif arg == 'start':
            stopped = Server(a.app_name, Config.app_dir).server_names

        func(a, *args, **kwargs)

        if arg in ['restart', 'start']:
            for server_name in stopped:
                start(server_name, False, False)
    return wrapper


def app(func):
    def wrapper(app, *args, **kwargs):
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
        else:
            func(a, *args, **kwargs)
    return wrapper


def server(func):
    def wrapper(app, *args, **kwargs):
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
        else:
            if s.server_name:
                func(s, *args, **kwargs)
            else:
                for server_name in s.server_names:
                    s = Server(server_name, Config.app_dir)
                    func(s, *args, **kwargs)
    return wrapper


def app_special_names(apps):
    if apps in [('all',), ('installed',)]:
        return Index.list(Config.app_dir)
    if apps in [('running',), ('stopped',)]:
        tmp = []

        for app in Index.list(Config.app_dir):
            s = Server(app, Config.app_dir)

            if s.running:
                for server in s.server_names:
                    if Server.running_check(s.app_name, server):
                        if apps[0] == 'running':
                            tmp.append(server)
                    else:
                        if apps[0] == 'stopped':
                            tmp.append(server)
            else:
                if apps[0] == 'stopped':
                    tmp.append(app)

        return tmp

    if apps == ('backups',):
        return Index.list(Config.backup_dir)
    return apps


@app
@run
def backup(a, compression, force):
    info(a.app_name, a.app_id)

    if not a.installed:
        message('Error', 'App not installed')
    elif not force and a.running:
        message('Error', 'Stop server before backup')
    else:
        if not os.path.exists(a.backup_dir):
            os.makedirs(a.backup_dir)
        backups = os.listdir(a.backup_dir)
        length = len(backups)

        if Config.max_backups != 0 and length >= Config.max_backups:
            message('Status', 'Max backups reached')
            message('Status', 'Removing old backups')

            for backup in backups[0:length - Config.max_backups + 1]:
                os.remove(os.path.join(a.backup_dir, backup))

        message('Status', 'Backup started')
        a.backup(compression)
        message('Status', 'Backup complete')


@server
def console(s):
    info(s.server_name)

    if not s.installed:
        message('Error', 'App not installed')
    elif not s.running:
        message('Error', 'Stopped')
    else:
        message('Status', 'Attaching to session')
        s.console()
        message('Status', 'Disconnected from session')


@app
def edit(a, editor):
    if not a.installed:
        info(a.app_name, a.app_id)
        message('Error', 'App not installed')
    else:
        click.edit(editor=editor, filename=a.config_f)
        Index.update()


@server
def kill(s):
    info(s.server_name)

    if not s.installed:
        message('Error', 'App not installed')
    elif not s.running:
        message('Error', 'Stopped')
    else:
        message('Status', 'Killing')
        s.kill()
        message('Status', 'Stopped')


@app
def _list(a, arg=None):
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


@app
@run
def remove(a, force):
    info(a.app_name, a.app_id)

    if not a.installed:
        message('Error', 'App not installed')
    elif not force and a.running:
        message('Error', 'Stop server before validating')
    else:
        message('Status', 'Removing')
        a.remove()
        message('Status', 'Remove complete')


@app
@run
def restore(a, force):
    info(a.app_name, a.app_id)

    if not os.path.exists(a.backup_dir) or not os.listdir(a.backup_dir):
        message('Error', 'No backups found')
    elif not force and a.running:
        message('Error', 'Stop server before restoring')
    else:
        backups = os.listdir(a.backup_dir)
        length = len(backups)

        while length > 1:
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

        if not os.path.exists(a.app_dir):
            os.makedirs(a.app_dir)
        message('Status', 'Restoring')
        a.restore(backup)
        message('Status', 'Restore complete')


@server
def send(s, command):
    info(s.server_name)

    if not s.installed:
        message('Error', 'App not installed')
    elif not s.running:
        message('Error', 'Stopped')
    else:
        message('Status', 'Command sent')
        s.send(command)
        message('Status', 'Command finished')


@server
def start(s, debug=False, verbose=False,):
    info(s.server_name)

    if not s.installed:
        message('Error', 'App not installed')
    elif s.running:
        message('Error', 'Already running')
    else:
        message('Status', 'Starting')
        s.start(debug)
        message('Status', 'Started')

        if verbose and not debug:
            sleep(1)
            s.console()


@server
def status(s):
    info(s.server_name)

    if not s.installed:
        message('Error', 'App not installed')
    elif s.running:
        message('Status', 'Running')
    elif not s.running:
        message('Status', 'Stopped')


@server
def stop(s, wait_time):
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


@app
@run
def update(a, username, password, steam_guard, check_only, no_check, force, validate, verbose):
    steamcmd_check()
    info(a.app_name, a.app_id)

    if not force and a.running:
        message('Error', 'Stop server before update')
    elif not a.installed:
        message('Status', 'Installing')
        exit_code, text = a.update(username, password, steam_guard,
                                   validate, verbose)

        if not verbose:
            if exit_code == 0:
                message('Status', text)
            else:
                message('Error', text)
    else:
        if not no_check and not validate:
            message('Status', 'Checking for updates')

            if a.build_id_local >= a.build_id_steam:
                message('Status', 'Already up to date')
                return
            else:
                message('Status', 'Update available')

        if not check_only:
            if validate:
                message('Status', 'Updating and Validating')
            else:
                message('Status', 'Updating')

            exit_code, text = a.update(username, password, steam_guard,
                                       validate, verbose)

            if not verbose:
                if exit_code == 0:
                    message('Status', text)
                else:
                    message('Error', text)


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
        steamcmd_install(verbose=False)

    if not steamcmd.installed:
        sys.exit(1)


def steamcmd_install(verbose):
    click.echo('[ ------ ]')
    message('Status', 'SteamCMD installing')

    steamcmd = SteamCMD()
    steamcmd.install()
    message('Status', 'SteamCMD installed')

    message('Status', 'SteamCMD updating')
    exit_code, text = steamcmd.update(verbose)

    if not verbose:
        if exit_code == 0:
            message('Status', 'SteamCMD updated')
        else:
            message('Error', text)
