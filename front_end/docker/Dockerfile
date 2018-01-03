FROM ubuntu:14.04

RUN locale-gen en_US.UTF-8 && \
    update-locale LANG=en_US.UTF-8

RUN apt-get update && apt-get install -y \
    build-essential \
    python-dev \
    rabbitmq-server \
    postgresql \
    libpq-dev \
    redis-server \
    git \
    curl \
    libcurl4-openssl-dev \
    unzip \
    python-pip \
    g++ \
    libboost-all-dev \
    zlib1g \
    supervisor

# setup deploy key
ADD ./id_rsa /root/.ssh/id_rsa
RUN mkdir -p /root/.ssh && \
    touch /root/.ssh/known_hosts && \
    ssh-keyscan github.com >> /root/.ssh/known_hosts && \
    chmod 700 /root/.ssh -R

# setup postgres
RUN echo "host    all             all             127.0.0.1/32            password" | tee -a /etc/postgresql/9.3/main/pg_hba.conf && \
    service postgresql restart

# install nvm
RUN curl https://raw.githubusercontent.com/creationix/nvm/v0.17.2/install.sh | bash
ENV NVM_DIR /.nvm
RUN echo '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"' >> /.bashrc

# install node
RUN bash -c "source /.bashrc && nvm install 0.11.13" && \
    echo "nvm use 0.11.13" >> /.bashrc

# install virtualenv and activate
RUN pip install virtualenv && \
    virtualenv /envs/ersatz && \
    virtualenv /envs/dmworker && \
    mkdir -p /srv/www

# setup api
RUN cd /srv/www && \
    git clone git@github.com:davebs/ersatz_api.git ersatz && \
    cd ersatz && \
    git checkout staging && \
    cp run_gunicorn.sh run_gunicorn_staging.sh && \
    sed -i "s|USER=.*|USER=root|g" run_gunicorn_staging.sh && \
    sed -i "s|GROUP=.*|GROUP=root|g" run_gunicorn_staging.sh && \
    sed -i "s|env/bin/activate|/envs/ersatz/bin/activate|g" run_gunicorn_staging.sh && \
    sed -i "/source ersatz\/secret_settings/d" run_gunicorn_staging.sh && \
    sed -i "/--bind=unix:$SOCKFILE/d" run_gunicorn_staging.sh && \
    sed -i "s|ersatz.settings.production|ersatz.settings.staging|g" run_gunicorn_staging.sh && \
    sed -i "s|run_gunicorn|run_gunicorn 0.0.0.0:8000|g" run_gunicorn_staging.sh && \
    service postgresql start && \
    echo 'export PATH=$(npm bin):$PATH' >> /.bashrc && \
    bash -c "source /.bashrc && npm install && grunt build" && \
    bash -c "source /envs/ersatz/bin/activate && pip install -r requirements/production.txt" && \
    bash -c "source /envs/ersatz/bin/activate && pip uninstall -y sockjs-tornado" && \
    bash -c "source /envs/ersatz/bin/activate && pip install -e git+https://github.com/mrjoes/sockjs-tornado.git#egg=sockjs-tornado"

# setup dmworker
RUN cd /srv/www && \
    git clone git@github.com:davebs/DM_Worker.git dmworker && \
    cd dmworker && \
    git checkout staging && \
    bash -c "source /envs/dmworker/bin/activate && pip install -r requirements/staging.txt" && \
    cd native/projects/csvstat && \
    make && \
    make install

# setup supervisor config
RUN mkdir -p /etc/supervisor/conf.d && \
    echo_supervisord_conf > /etc/supervisor/supervisord.conf && \
    sed -i "s|;[include]|[include]|g" /etc/supervisor/supervisord.conf && \
    sed -i "s|;files = relative/directory/\*.ini|files = /etc/supervisor/conf.d/\*.conf|g" /etc/supervisor/supervisord.conf && \
    sed -i "s|nodaemon=false|nodaemon=true|g" /etc/supervisor/supervisord.conf && \
    cp /srv/www/ersatz/supervisord/staging.conf /etc/supervisor/conf.d/ersatz.conf && \
    sed -i "s|^user.*|user=root|g" /etc/supervisor/conf.d/ersatz.conf && \
    sed -i "s|/srv/www/ersatz/env/bin/python manage.py|/envs/ersatz/bin/python manage.py|g" /etc/supervisor/conf.d/ersatz.conf && \
    NODE=$(bash -c "source /.bashrc > /dev/null && which node") && \
    sed -i "s|command=node|command=$NODE|g" /etc/supervisor/conf.d/ersatz.conf && \
    cp /srv/www/dmworker/supervisord/staging.conf /etc/supervisor/conf.d/dmworker.conf && \
    sed -i "s|^user.*|user=root|g" /etc/supervisor/conf.d/dmworker.conf && \
    sed -i "s|/srv/www/dmworker/env/bin/celery|/envs/dmworker/bin/celery|g" /etc/supervisor/conf.d/dmworker.conf

# add run scripts
ADD ./run.sh /usr/local/bin/run.sh
RUN chmod +x /usr/local/bin/run.sh && \
    apt-get autoremove -y && \
    apt-get clean

CMD ["/usr/local/bin/run.sh"]
