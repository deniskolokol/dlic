Quickstart
==========

INSTALL
-------

Data mangement worker not included in this repo, run::

    git submodule init  # on first setup
    git submodule update  # every time when dmworker will be changed

Install Cuda.

Python::

    pip install numpy
    pip install -r requirements.txt

Convnet::
    
    git checkout cb37982
    cd convnet
    # edit build.sh
    sh build.sh
    git check master

Cudamat::

    cd ersatz/mrnn
    rm -r cudamat
    hg clone https://cudamat.googlecode.com/hg/ cudamat
    cd cudamat && make

A Note about Theano::

In the early days of Ersatz Labs, we once ran into a problem with Theano on
staging branch which stemmed from the production version of Theano and the
staging version of Theano writing to the same directory by default: `~/.theano`.

If you are reinstalling the staging environment from scratch, make the following
change to the theano package installed in the associated virtualenv:

Find the file `env/lib/python2.7/site-packages/theano/gof/compiledir.py` and
change line 160 to

    `default_base_compiledir = os.path.join(get_home_dir(), '.theano_staging')`


Settings
--------

Each worker should be started with environment option ``ERSATZ_SETTINGS``.
You can find prepared settings in settings module.
``ERSATZ_SETTINGS`` can be set from export like::

    export ERSATZ_SETTINGS=settings.staging
    python bin/errun

or for each command like::

    ERSATZ_SETTINGS=settings.staging python bin/errun

If program not found ``ERSATZ_SETTINGS`` variable, it will try to start with
``settings.local`` settings, which works with localhost api only.

Prepared settings
    - production # production api server
    - staging # staging api server
    - test # for test only
    - local # mostly for development


Run worker
----------

User can run worker in 3 modes:

- train+predict: `python bin/errun`
- train only: `python bin/ertrain`
- predict only: `python bin/erpredict`


In all this modes user can select which gpus to use, or run it on cpu::

    ERSATZ_SETTINGS=settings.local python bin/errun -h
    usage: errun [-h] [--cpu] [--mcpus MCPUS] [--gpu GPU] [--mgpu MGPU]

    optional arguments:
      -h, --help     show this help message and exit

    cpu:
      options to run on cpu

      --cpu          run all jobs on CPU
      --mcpus MCPUS  numer of cpu to use for mrnn. CPU mode only (default: 1)

    gpu:
      options to run on gpu

      --gpu GPU      which GPU to use for running jobs (default: 0)
      --mgpu MGPU    which gpus to use for mrnn training, if not specified then it
                     will run on one gpu with id from --gpu or 0.(example: --mgpu
                     0 --mgpu 2. This will run mrnn on two gpus with id 0 and 2)

Ex. if you want to run job on gpu id=2::

    ERSATZ_SETTINGS=settings.local python bin/errun --gpu=2

if you want to run mrnn on 2 gpus (1,2) and all other jobs on gpu 0::

    ERSATZ_SETTINGS=settings.local python bin/errun --gpu=0 --mgpu 1 --mgpu 2

if you want to run program on cpu and mrnn should have 4 workers::

    ERSATZ_SETTINGS=settings.local python bin/errun --cpu --mcpus 4


Run test
--------
with py.test::
    THEANO_FLAGS="floatX=float32,device=gpu0" ERSATZ_SETTINGS='settings.test' py.test tests

Helpers
-------

To get file form s3 run ``bin/s3get``. You should set production settings,
because by default it will use test bucket.

To upload file on s3 run ``bin/s3upload``. You should set production settings,
because by default it will use test bucket.

Setup as library
----------------

Now you can also setup ersatz as library.
You only need to select module with ersatz settings (You can copy settings dir to another location)
NOT TESTED YET!
::

    python setyp.py develop
    # from any directory run
    ERSATZ_SETTINGS=settings.<name> errun
