import shlex
import time
from subprocess import Popen, STDOUT

cmd1 = "celery worker --app=dmworker.tasks -l info -Q default -n default@server --logfile=./var/default.log --pid=./var/pid-default.pid"
cmd1 = shlex.split(cmd1)
p1 = Popen(cmd1, stderr=STDOUT)


cmd2 = "celery worker --app=dmworker.tasks -l info -Q parser -n parser@server --logfile=./var/parser.log --pid=./var/pid-parser.pid"
cmd2 = shlex.split(cmd2)

p2 = Popen(cmd2, stderr=STDOUT)


cmd3 = "celery beat --app=dmworker.tasks"
cmd3 = shlex.split(cmd3)

p3 = Popen(cmd3, stderr=STDOUT)

try:
    time.sleep(999999)
except KeyboardInterrupt:
    pass

p1.kill()
p2.kill()
p1.kill()
p2.kill()
p3.kill()
p3.kill()
