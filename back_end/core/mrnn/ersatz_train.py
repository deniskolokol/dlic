import json
import subprocess
import threading
import collections
import time
import os
import shutil
import traceback
import sys
from multiprocessing import Process, Pipe
from termcolor import colored
from . import ersatz_main
from .ersatz_dp import DP
from ..exception import ApiStoppedTraining, BaseErsatzError
from .. import api
from ..listener import Consumer
from ..conf import settings
from .. import get_logger
from .memory import get_batch_size
from .util import grab_gpu_boards, calculate_batch_size
from .. import spearmint_wrapper as swrap
from .. import hyperparams as hp
from ..data import dataset
from ..shared.cifar import BatchWriter
from .cnn_maker4 import make_cnn
from ..misc import Tee
from ..reporter import build_train_pipe
from StringIO import StringIO
import sys
import re
import numpy as np


log = get_logger('ersatz_train')
# Spearmint parameters.
CHOOSER = 'GPEIChooser'
PROJECT_NAME = 'ersatz'

def runProcess(exe):
    p = subprocess.Popen(exe, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while(True):
      retcode = p.poll() #returns None while subprocess is running
      line = p.stdout.readline()
      yield line
      if(retcode is not None):
        break


def train_MRNN(hyperparams, pipe, worker_params, runner):
    _, ensemble_id, _, model_id = runner.train_pipe.routing_key.split('.')
    train_pipe_param = (int(ensemble_id), int(model_id), 1)
    mrnn_train_pipe = build_train_pipe(*train_pipe_param)

    sys.stdout = Tee('stdout', mrnn_train_pipe)
    sys.stderr = Tee('stderr', mrnn_train_pipe)

    log.debug('Train MRNN process PID: %s' % os.getpid())
    try:
        lower_loss, running_time = ersatz_main.main(hyperparams,
                                                    worker_params,
                                                    runner.report_pipe,
                                                    train_pipe_param)
        pipe.send((lower_loss, running_time, None))
        pipe.close()
    except Exception as e:
        e.traceback = traceback.format_exc()
        pipe.send((100000, 100000, e))
        pipe.close()
    finally:
        sys.stdout.close()
        sys.stderr.close()


def send_training_failed_error(model_id, traceback, queue_key,
                               error="Training failed"):
    params = {'model': model_id, 'state': 'ERROR',
              'traceback': traceback, 'error': error,
              'queue_key': queue_key}
    api.post('/api/train/status/', params)
    print 'stop processing ensemble'
    print '#' * 80


def set_batch_size(dp_data, hyperparams, output_len):
    T, strain, vo = dp_data['train']['shape']
    Ts, stest, _ = dp_data['test']['shape']
    T = max(Ts, T)
    max_batch_size, gpu_memory = get_batch_size(vo - output_len,
                                                output_len,
                                                hyperparams.h.value,
                                                hyperparams.f.value,
                                                T)
    min_num_batches = len(grab_gpu_boards())
    train_batch_size, num_train_batches = calculate_batch_size(
        strain, max_batch_size, min_num_batches)
    test_batch_size, num_test_batches = calculate_batch_size(
        stest, max_batch_size, min_num_batches)

    dp_data['train']['num_batches'] = num_train_batches
    dp_data['test']['num_batches'] = num_test_batches
    dp_data['train']['batch_size'] = train_batch_size
    dp_data['test']['batch_size'] = test_batch_size
    dp_data['memory'] = gpu_memory
    return dp_data


def conf_fname(model_name):
    return model_name.lower() + '.json'


def extract_config(fname):
    if not os.path.isfile(fname):
        fname = os.path.join(settings.SPEARMINT, PROJECT_NAME, fname)
    try:
        f = open(fname, 'r')
    except IOError:
        return None

    return json.loads(f.read(), object_pairs_hook=collections.OrderedDict)


def update_config(target, source):
    """
    Updates ranges of hyperparameters.
    """
    for k, v in source.iteritems():
        try:
            target[k]['min'] = source[k]['min']
            target[k]['max'] = source[k]['max']
        except:
            pass

    return target


def ensure_hyperparams(model_name, config, hyperparams=None):
    """
    Extracts configuration for hyperparameters from config file,
    using OrderedDict, because order of element matters.
    """
    sp_config = extract_config(conf_fname(model_name))
    try:
        sp_config = update_config(sp_config, config)
    except:
        pass

    if hyperparams:
        hyperparams.conf = sp_config
        return hyperparams

    return hp.HyperParams(sp_config.keys(), **sp_config)


def fill_hyperparams(model, sp_results, config, hyperparams=None):
    """
    Obtains parameters for training a new model:
    * for the first two models parameters hard-coded in the conf file,
    * for the models starting from the 3rd one launches spearmint-lite
      to predict parameters.

    Before obtaining parameters updates (min, max) ranges in config.
    """
    hyperparams = ensure_hyperparams(model['name'], config, hyperparams)
    parms_user = hp.unroll_params(model['model_params'])

    try:
        parms_auto = hyperparams.get_init_values(len(sp_results))
    except (IndexError, KeyError):
        spw = swrap.SpearmintLightWrapper(project_name=PROJECT_NAME,
                                          config=hyperparams.get_conf_ordered())
        parms_auto = spw.perform(sp_results)[-1][2:]

    hyperparams.set_values(parms_auto)  # set calculated params
    for k, v in parms_user.iteritems(): # but respect user's choice
        if v: hyperparams.set_value(k, v)

    return hyperparams


def train_models(message_data, dp_data, output_len, runner):
    models = message_data['models']
    ensemble = message_data['ensemble']
    queue_key = message_data['queue_key']
    config = message_data['config']
    sp_results = []
    if message_data['sp_results']:
        sp_results = message_data['sp_results'].strip().split('\n')
    number_of_timesteps_to_use = message_data['options'].get('num_timesteps', 99999999)
    max_timesteps = message_data['options'].get('max_timesteps')
    bayesian_name = str(ensemble) # each model gets a different ID but the bayesian
                                  # optimization stuff needs same ID throughout training
                                  # we will use ensemble id for this
    pwd = settings.WORKING_DIR.child('runs').child(bayesian_name)
    pwd.mkdir(parents=True)

    if os.path.exists(pwd):
        shutil.rmtree(pwd)
    for line in runProcess(['mkdir', pwd]):
        print line

    # Initiate container for hyperparams.
    hyperparams = None

    for model in models:
        settings.WORKING_DIR.child('models', str(model['id'])).mkdir(parents=True)

        # Calculate hyperparams values for the current model.
        hyperparams = fill_hyperparams(model, sp_results, config, hyperparams)
        params = hyperparams.values()

        dp_data = set_batch_size(dp_data, hyperparams, output_len)

        # Populate hyperparams with additional values for ersatz_main.
        hyperparams_main = hyperparams.as_dict()
        hyperparams_main.update({'max_timesteps': max_timesteps,
                                 'train_shape': dp_data['train']['shape'],
                                 'output_len': output_len,
                                 'model_id': str(model['id']),
                                 'timesteps': number_of_timesteps_to_use})

        # Obtain parameters for API (add `max_timesteps` for display).
        params_json = hyperparams.as_dict()
        params_json.update({'T': max_timesteps})
        api_params = {'model': model['id'],
                      'model_params': params_json,
                      'queue_key': queue_key,
                      'state': 'TRAIN'}

        # worker should set job state to train
        # if job will have another state, stats send will not work
        if not api.post('/api/train/status/', api_params):
            #api not allowed set status to train; quit
            print "Can't set model status to the TRAIN (api response not 200), return"
            return

        parent_conn, child_conn = Pipe()
        model.update({'queue_key': queue_key, 'dp_data': dp_data})
        log.debug('Ersatz train process PID: %s' % os.getpid())

        p = Process(target=train_MRNN, args=(hyperparams_main, child_conn, model, runner))
        p.start()
        exc = None
        while True:
            if not p.is_alive() and not parent_conn.poll():
                exc = BaseErsatzError(original_traceback='train_MRNN process died.')
                break
            if parent_conn.poll(0.01):
                try:
                    lower_loss, running_time, exc = parent_conn.recv()
                except EOFError:
                    exc = BaseErsatzError('train_MRNN process died.')
                break
        p.join()
        if exc is not None:
            if isinstance(exc, ApiStoppedTraining):
                pass
            elif isinstance(exc, BaseErsatzError):
                error = 'Training failed'
                if exc.show_to_user:
                    error = exc.message
                send_training_failed_error(model['id'], exc.get_traceback(),
                                           queue_key, error)
            else:
                print exc.traceback
                send_training_failed_error(model['id'], exc.traceback,
                                           queue_key)
            return

        # WARNING! Check if int(running_time) is necessary. For small datasets
        # training time might be equal to 0, which will lead to errors in
        # spearmint's prediction.
        #
        # Update `params` and `sp_results` after current run.
        params = [max(.0001, lower_loss), int(running_time)] + params
        sp_results.append(' '.join([str(x) for x in params]))

        dr = settings.WORKING_DIR.child('models', str(model['id']), 'detailed_results')
        with open(dr, 'r') as f:
            detailed_results = f.read()

        api_params = {'model': model['id'],
                      'state': 'FINISHED',
                      'sp_results': sp_results[-1],
                      'detailed_results': detailed_results,
                      'model_params': params_json,
                      'queue_key': queue_key}
        if not api.post('/api/train/status/', api_params):
            return


def train_timeseries(message_data, runner):
    dp = DP(message_data)
    dp.load_data()
    data = dp.create_view()
    params = {'ensemble': message_data['ensemble'],
              'quantiles': [],  #TODO: fix quantiles
              'queue_key': message_data['queue_key']}
    if not api.post('/api/ensemble/status/', params):
        return
    train_models(message_data, data, dp.len_output, runner)


def print_output(proc):
    while True:
        line = proc.stdout.readline()
        if line:
            print line.strip()
        else:
            return


def create_configs(params, work_dir):
    if not params.get('test_freq'):
        params['test_freq'] = 20
    if not params.get('maxnum_iter'):
        params['maxnum_iter'] = 1000
    layer_def = os.path.join(work_dir, 'layers.cfg')
    layer_params = os.path.join(work_dir, 'layer-params.cfg')
    if not params.get('layers'):
        with open(settings.CONVNET.child(*('example-layers', 'layers-18pct.cfg')), 'r') as f:
            params['layers'] = f.read()
    with open(layer_def, 'w') as f:
        f.write(params['layers'])
    if not params.get('layer_params'):
        with open(settings.CONVNET.child(*('example-layers', 'layer-params-18pct.cfg')), 'r') as f:
            params['layer_params'] = f.read()
    with open(layer_params, 'w') as f:
        f.write(params['layer_params'])
    return layer_def, layer_params


def get_data_options(message_data, model):
    train_dset = dataset.get_dataset(message_data['train_dataset'])
    test_dset = dataset.get_dataset(message_data['test_dataset'])
    data_path = dataset.prepare_dataset_file_dir(message_data['train_dataset']['key']).parent
    bw = BatchWriter(data_path, img_size=model['model_params']['img_size'])
    bw.prepare_training(train_dset, test_dset)
    return bw.get_data_options()


def convert_params_for_config(hyperparams, model_params):
    """
    WARNING! Temporary solution for converting
    'learning_rate': {'init': 0.1} into 'learning_rate': 0.1
    """
    result = {}
    for k, v in model_params.iteritems():
        if isinstance(v, dict):
            try:
                result[k] = v['init']
            except KeyError:
                result[k] = hyperparams[k]['conf']['init'][0]
        else:
            result[k] = v
    #layers = message_data['options']['layers_cfg'] % result
    #layer_params = message_data['options']['layer_params_cfg'] % result
    layers, layer_params = make_cnn(**result)
    result.update({'layers': layers, 'layer_params': layer_params})

    return result


def train_images(message_data):
    #simple interaction with convnet, better construct and run it from code,
    #but for beginning it ok
    models = message_data['models']
    config = message_data.get('config', {})
    consumer = Consumer(default_queue=message_data['queue_key'])
    ens_dir = settings.WORKING_DIR.child('runs', str(message_data['ensemble']))
    # create cmd
    exe_base = ['python', settings.CONVNET.child('convnet.py')]

    # Initiate spearmint results list and container for hyperparams.
    sp_results = []
    if message_data['sp_results']:
        sp_results = message_data['sp_results'].strip().split('\n')
    hyperparams = None

    try:
        for model in models:
            exe = exe_base[:]
            exe += get_data_options(message_data, model)

            # Calculate hyperparams values for the current model.
            hyperparams = fill_hyperparams(model, sp_results, config, hyperparams)
            model['model_params'] = hp.roll_params(hyperparams,
                                                   model['model_params'])

            # Put the final output count into each model.
            model['model_params']['final_output'] = message_data['final_output']

            model_params = convert_params_for_config(hyperparams,
                                                     model['model_params'])
                                                     #,message_data)
            params = hyperparams.values()

            work_dir = ens_dir.child(str(model['id']))
            work_dir.mkdir(parents=True)
            layer_def, layer_params = create_configs(model_params, work_dir)
            exe += ['--epochs=' + str(model['model_params']['maxnum_iter']),
                    '--queue-key=' + message_data['queue_key'],
                    '--model-id=' + str(model['id']),
                    '--ensemble-id=' + str(message_data['ensemble']),
                    '--test-freq=' + str(model['model_params']['test_freq']),
                    '--save-freq=' + str(model['model_params']['save_freq'])]
            if os.environ.get('ERSATZ_GPU_ID'):
                exe += ['--gpu=' + os.environ.get('ERSATZ_GPU_ID')]
            if model.get('resume'):
                exe += ['-f', model['resume_X']]
            else:
                exe += ['--save-path=' + work_dir,
                        '--layer-def=' + layer_def,
                        '--layer-params=' + layer_params]
            api_params = {'model': model['id'], 'state': 'TRAIN',
                          'model_name': 'CONV',
                          'queue_key': message_data['queue_key'],
                          'model_params': model['model_params']}
            if not api.post('/api/train/status/', api_params):
                #api not allowed set status to train; quit
                print "Can't set model status to the TRAIN (api response not 200), return"
                return
            print ' '.join(exe)
            proc = subprocess.Popen(exe, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

            # consumer for stop message
            thr = threading.Thread(target=print_output, args=(proc,))
            thr.start()
            while proc.poll() is None:
                if consumer.check_stop_message():
                    proc.kill()
                    thr.join()
                    raise ApiStoppedTraining()
                time.sleep(1)
            thr.join()

            if proc.poll() == 100:
                print colored('Maybe user out of money.', 'yellow')
            elif proc.poll() == 0:
                print colored('training finished.', 'blue')
                # Get stats for Spearmint from API.
                stats = api.get('/api/worker/model/stats/',
                                params={'model':model['id']})

                lower_loss = max(0.1, 1 - stats['test_accuracy'])
                running_time = stats['total_time']
                # If above is giving best not last, replace w/ this:
                # lower_loss = 1 - stats['train_outputs'][-1][2]

                # Update `params` and `sp_results` after current run.
                params = [lower_loss, int(running_time)] + params
                sp_results.append(' '.join([str(x) for x in params]))
                api_params = {'model': model['id'],
                              'model_name': 'CONV',
                              'state': 'FINISHED',
                              'queue_key': message_data['queue_key'],
                              'sp_results': sp_results[-1]}
                api.post('/api/train/status/', api_params)
            else:
                error = proc.stderr.read().strip()
                print colored(error, 'red')
                traceback = error
                error = 'Training failed'
                send_training_failed_error(model['id'], traceback,
                                           message_data['queue_key'], error)



    except ApiStoppedTraining:
        print colored('training stopped.', 'blue')
    finally:
        consumer.close()


def train_tsne(message_data, pre_finish_callback=None):
    from sklearn.manifold import TSNE
    from ..data.dataset import get_dataset
    TESTING_SUBSET = 1000

    #params = message_data['models'][0]['model_params']
    #tsne = TSNE(**params)
    #tsne.verbose = 2
    #data = get_dataset( message_data['train_dataset'] ).get_training_data()
    #output = tsne.fit_transform(data[:1000])

    dataset = get_dataset( message_data['train_dataset'] )
    data = [x[:-1] for x in dataset.get_training_data()] #exclude lastcol output
    classes = dataset.output
    #Note: In the unsplit type of dataset that t-sne works with,
    #      get_training_data() and get_predict_data() return the same ndarray,
    #      albeit not in the same order.
    #
    #      The output attribute returns the last column outputs in an order
    #      matching the training order. If there's a mystery in the future
    #      regarding dots being mislabeled/micolored, revisit this assumption.
    models = message_data['models']
    consumer = Consumer(default_queue=message_data['queue_key'])
    try:
        for model in models:
            params = model['model_params']
            api_params = {'model': model['id'], 'state': 'TRAIN',
                          'model_name': model['name'],
                          'queue_key': message_data['queue_key'],
                          'model_params': model['model_params']}
            if not api.post('/api/train/status/', api_params):
                #api not allowed set status to train; quit
                print "Can't set model status to the TRAIN (api response not 200), return"
                return
            try:
                params.pop('tsne_output')
            except:
                pass

            mod_params = params.copy()
            mod_params['n_iter'] = mod_params.pop('maxnum_iter')
            tsne = TSNE(**mod_params)
            tsne.verbose = 2
            #old_stdout = sys.stdout #statskludge
            #alt_stdout = StringIO() #statskludge
            #sys.stdout = alt_stdout #statskludge
            output = tsne.fit_transform(data[:TESTING_SUBSET]) ##TODO## if subset is being taken, need to shuffle output, classes in unison ##TODO##
            labeled_output = np.concatenate( (output, classes[:TESTING_SUBSET]), axis=1) #append classes for graph dot coloring
            #sys.stdout = alt_stdout #statskludge
            #verbose_dump = alt_stdout.getvalue().split('\n') #statskludge
            #stats = parse_verbosity(verbose_dump) #statskludge

            model['model_params']['tsne_output'] = json.dumps([list(x) for x in labeled_output])

            # give the caller an opportunity to do something
            # before we change the state to FINISHED
            if callable(pre_finish_callback):
                pre_finish_callback(model)

            api_params = {'model': model['id'], 'state': 'FINISHED',
                          'model_name': model['name'],
                          'queue_key': message_data['queue_key'],
                          'model_params': model['model_params'],
                          'tsne_output': output}
            api.post('/api/train/status/', api_params)
    except ApiStoppedTraining:
        print colored('training stopped.', 'blue')
    finally:
        consumer.close()


def parse_verbosity(v):
    stats = []
    for line in v:
        if line.startswith('[t-SNE] Iteration') and '=' in line:
            stats.append( re.findall(r'[0-9.]+', line) )
    return stats
