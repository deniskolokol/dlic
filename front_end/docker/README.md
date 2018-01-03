### Requirements

- [Docker](http://docker.io/)

    See [here](https://docs.docker.com/installation/#installation) for your distro specific installation.

- [Fig](http://www.fig.sh/) - used for managing containers.

    ```bash
    $ curl -L https://github.com/docker/fig/releases/download/0.5.2/linux > /usr/local/bin/fig
    $ chmod +x /usr/local/bin/fig
    ```

    For Fig to able to connect to Docker, change your `DOCKER_OPTS` settings under `/etc/default/docker.io` to:
    
    `DOCKER_OPTS="-H tcp://127.0.0.1:4243 -H unix:///var/run/docker.sock"`

- `id_rsa` - private key pair of your deployment keys, the public half should be added on your github account that has access to the following repos:

    * [https://github.com/davebs/ersatz_api](https://github.com/davebs/ersatz_api)
    * [https://github.com/davebs/DM_Worker](https://github.com/davebs/DM_Worker)
    * [https://github.com/davebs/ersatz_worker](https://github.com/davebs/ersatz_worker)

### Setup

- Requires the following envars present on the host, they will automatically be picked-up by fig and injected on the container:

    `CONTAINER_HOST`
    `DB_NAME`  
    `DB_USER`  
    `DB_PASSWORD`
    `BROKER_USER`  
    `BROKER_PASSWORD`  
    `BROKER_VHOST`  
    `DMWORKER_VHOST`  
    `REDIS_PASSWORD`  

- Exposes the following ports that are auto-mapped to equivalent ports on the host:

    `8000` - Django  
    `5672` - RabbitMQ  
    `4000` - SocketIO  
    `8887` - SocketJS  

### Running

Set your host's IP on `envars` file first then export envars:

    $ source envars

Building image base off of `Dockerfile`:

    $ fig build

Spawning container based off of built image:

    $ fig up

Once running you can visit http://<container ip>:8000. See `run.sh` for more info on what's happening after the container is spawned. You can do `docker inspect —format="{{ .NetworkSettings.IPAddress }}" <container id>` to find out the container's IP.

### Improvements

- Move Postgres, Redis and RabbitMQ to their own container
- ...

### Notes

- Using `sockjs-tornado==1.0.0` produces 403 error upon connection, installing latest dev version fixes it. See Dockerfile#L57 for more info.
