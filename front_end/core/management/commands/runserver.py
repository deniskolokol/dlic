import os
import subprocess
import atexit
import signal
from optparse import make_option
from multiprocessing import Process

from django.conf import settings
from django.contrib.staticfiles.management.commands.runserver import Command\
    as StaticfilesRunserverCommand


class Command(StaticfilesRunserverCommand):
    option_list = StaticfilesRunserverCommand.option_list + (
        make_option(
            '--no-grunt',
            default=True,
            action='store_false',
            dest='grunt',
            help='Prevents grunt from running at the same time as runserver'
        ),
        make_option(
            '--no-ws',
            default=True,
            action='store_false',
            dest='ws',
            help=('Prevents web sockets server from running at '
                  'the same time as runserver')
        ),
    )

    def inner_run(self, *args, **options):
        grunt = options.get('grunt')
        ws = options.get('ws')
        if ws:
            self.start_ws_server()
        if grunt:
            self.start_grunt()
        return super(Command, self).inner_run(*args, **options)

    def start_grunt(self):
        self.stdout.write('>>> Starting grunt')
        cmd = ('{0}/node_modules/grunt-cli/bin/grunt '
               '--gruntfile={0}/Gruntfile.js --base=. --force')
        self.grunt_process = subprocess.Popen(
            [cmd.format(settings.PROJECT_DIR)],
            shell=True,
            stdin=subprocess.PIPE,
            stdout=self.stdout,
            stderr=self.stderr,
            preexec_fn=os.setsid
        )

        self.stdout.write(
            '>>> Grunt process on pid {0}'.format(self.grunt_process.pid)
        )

        def kill_grunt_process(pid):
            self.stdout.write('>>> Closing grunt process')
            os.killpg(pid, signal.SIGTERM)

        atexit.register(kill_grunt_process, self.grunt_process.pid)

    def start_ws_server(self, *args, **options):
        def ws_worker():
            from web.ws_server import run as ws_run
            try:
                ws_run()
            except:
                self.stdout.write('>>> Closing web sockets server')

        def kill_ws_server(p):
            p.terminate()

        self.stdout.write('>>> Starting web sockets server')
        p = Process(target=ws_worker)
        p.start()
        self.stdout.write('>>> WS process on pid {0}'.format(p.pid))
        atexit.register(kill_ws_server, p)
