#!/bin/bash
set -e

# setup rabbitmq
service rabbitmq-server start
rabbitmqctl add_user $BROKER_USER $BROKER_PASSWORD && \
rabbitmqctl add_vhost $BROKER_VHOST && \
rabbitmqctl set_permissions -p $BROKER_VHOST $BROKER_USER ".*" ".*" ".*" && \
rabbitmqctl add_vhost $DMWORKER_VHOST && \
rabbitmqctl set_permissions -p $DMWORKER_VHOST $BROKER_USER ".*" ".*" ".*"

# setup redis
sed -i "s/# requirepass .*/requirepass $REDIS_PASSWORD/g" /etc/redis/redis.conf && \
service redis-server start

# setup postgres
service postgresql start
cat <<EOF | su postgres -c psql > /dev/null
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD' CREATEDB;
CREATE DATABASE $DB_NAME WITH ENCODING 'UTF-8' OWNER $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

# update db
cd /srv/www/ersatz && \
source /envs/ersatz/bin/activate && \
CONTAINER_IP=$(/sbin/ip route | awk '/scope link/ { print $9 }') && \
sed -i "s|ALLOWED_HOSTS.*|ALLOWED_HOSTS = ('127.0.0.1', 'localhost', '$CONTAINER_IP', '$CONTAINER_HOST')|g" ersatz/settings/staging.py && \
sed -i "s|DMWORKER_REMOTE_ADDRESSES.*|DMWORKER_REMOTE_ADDRESSES = ('127.0.0.1', '$CONTAINER_IP')|g" ersatz/settings/staging.py && \
sed -i "s|DMWORKER_CALLBACK_URL.*|DMWORKER_CALLBACK_URL = 'http://$CONTAINER_IP:8000'|g" ersatz/settings/staging.py && \
sed -i "s|SOCKET_URL.*|SOCKET_URL = '$CONTAINER_HOST:4000'|g" ersatz/settings/staging.py && \
echo "WS_SERVER_URL = 'http://$CONTAINER_HOST:8887/sockjs'" >> ersatz/settings/staging.py && \
echo 'DEBUG = True' >> ersatz/settings/staging.py && \
python manage.py syncdb --noinput --settings=ersatz.settings.staging && \
python manage.py migrate --settings=ersatz.settings.staging

/usr/bin/supervisord -c /etc/supervisor/supervisord.conf

