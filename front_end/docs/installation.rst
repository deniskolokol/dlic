INSTALLATION
============

Install dependencies::

    pip install -r requirements/local.txt

Rabbitmq::

    sudo apt-get install rabbitmq-server
    sudo rabbitmqctl add_user "ersatz" "ija9fj432ertuerthjfsa"
    sudo rabbitmqctl add_vhost "ersatz"
    sudo rabbitmqctl set_permissions -p 'ersatz' ersatz '.*'  '.*' '.*'
    sudo rabbitmqctl add_vhost "dmworker"
    sudo rabbitmqctl set_permissions -p 'dmworker' ersatz '.*'  '.*' '.*'

Redis Server::

    sudo apt-get install redis-server
    sudo gedit /etc/redis/redis.conf  
        remove comment # requirepass foobared
        change pwd to REDIS_PASSWORD located in ersatz/setttings/base.py
    sudo service redis-server restart

Postgresql::

    echo "host    all             all             127.0.0.1/32            password" | sudo tee -a /etc/postgresql/9.1/main/pg_hba.conf

Put output of the command to your database::

    ./manage.py sqlcreate --settings=ersatz.settings.local --router=default

Sync db::

    ./manage.py syncdb --settings=ersatz.settings.local 
    ./manage.py migrate --settings=ersatz.settings.local

Run
---
::

    ./manage.py runserver --settings=ersatz.settings.local
