#!/usr/bin/python

import numpy
from .opt.hfs.c3_par_c import HF, std_backtrack_arithmetic_factory
from termcolor import colored
import time


class Settings(object):
    def __init__(self, settings):
        self.__dict__ = settings


def get_network(settings, train_pipe_param):
    t = HF(
       path = settings.save_path,

       grad_batches = settings.grad_batches,
       GN_batches = settings.GN_batches,
       line_search_batches = settings.line_search_batches,

       cg_prep_exprs = ['loss_0_GN = loss(0, batches=GN_batches)',
                        'BT_batches = range(1,10)'],
       # NOTE: len(BT_batches) >= num_gpus
       #cg_prep_exprs not used now see in c3c_par_c

       BT_fn_str =   'lambda x: model(x, batches=BT_batches, damp=True)',
       STOP_fn_str = 'lambda x: loss(x, batches=GN_batches) - loss_0_GN',
       RHO_nom_str =   'loss(new_x, batches=GN_batches) - loss_0_GN',
       RHO_denom_str = 'model(new_x, batches=GN_batches, damp=False)', # Note, implementations vary on whether or not to have damping here... test the effect if any sometime...

       backtrack_iter_set = std_backtrack_arithmetic_factory(freq=20),

       cg_max_cg = settings.cg_max_cg,
       cg_min_cg = settings.cg_min_cg,

       #cg_damper_expr='damp * (grad2 + 2e-6 + 1e-2*grad2.mean())**.75',
       #cg_precond_expr='(grad2 + 2e-6 + 1e-2*grad2.mean())**.75',

       #cg_damper_expr = 'damp',
       #cg_precond_expr = '(grad2 + damp)**.75',

       cg_damper_expr='damp + 2e-6',
       cg_precond_expr='1',


       test_freq = 1,
       test_otherwise_on_num = 24,

       save_freq = settings.save_freq,

       maxnum_iter=settings.maxnum_iter,
       settings=settings,
       rotate_data_after=settings.rotate_data_after,
       use_dropout=settings.use_dropout,
       worker_params=settings.worker_params,
       number_of_timesteps_to_use=settings.number_of_timesteps_to_use,
       train_pipe_param=train_pipe_param
       )
    if settings.try_resume and settings.worker_params.get('resume_X'):
        print colored('resuming model', 'blue')
        params = settings.worker_params
        t.load(s3_data=params['resume_X'], high_score=params.get('high_score'),
                lower_loss=params.get('lower_loss'))
    return t


def main(params, worker_params={}, stats_reporter=None, train_pipe_param=None):
    start_time = time.time()
    settings = Settings({
        'save_path': params['model_id'],
        'input_file': ['None'],
        'T': params['train_shape'][1],
        'T_frac': 0.9, #wtf is this? it's not test fraction or train fraction...
        'T_warmup': 10,
        'batch_size': 300,
        'maxnum_iter': params['maxnum_iter'], # max HF iterations
        'test_fraction': 0.2, # how much data will be used for testing
        'gnumpy_max_memory': 1500000000,
        'h': params['h'],
        'f': params['f'],
        'KK': 15, # during init: init_scale = 1./np.sqrt(KK)
        'L2_decay': 2e-6,
        'grad_batches': range(10),
        'GN_batches': range(20), # the length of this must be >= num_gpus
        'line_search_batches': range(10),
        'test_batches': range(5),
        'cg_max_cg': params['cg_max_cg'], # max CG iterations
        'cg_min_cg': params['cg_min_cg'], # min CG iterations
        'save_freq': 2,
        'init_damping': numpy.array([params['lambda'], params['mu']]), #*1,
        'max_damping': numpy.array([100., 10.]) * 1,
        'behavior_at_max_damping': 1., #2./3, # a number <1 to multiply damping by if max is reached
    	'try_resume': worker_params.get('resume', False),
        'lambda_override': True, # set this to true if you want to use init_damping, even on resume
        'rotate_data_after': 999, # controls how often child processes request a new set of random data from
                                  # twisted data server
        'use_dropout': False,
        'job_server_url': None, # Where to check for new jobs
        'reporting_server_url': None, # Where to report results (if not local)
        'worker_key': None, # Private string identifying this system and giving access to job server
        'v': params['train_shape'][2] - params['output_len'], #num visible units
        'o': params['output_len'], #num output units
        'worker_params': worker_params,
        'number_of_timesteps_to_use': params['timesteps'] 
        #Add these for the web app: S3_url, S3_model_url
    })
    print settings
    result, high_score = get_network(settings, train_pipe_param).optimize(stats_reporter)
    running_time = time.time() - start_time
    print colored('Accuracy for model ID %s: %2f' % (params['model_id'], high_score), 'blue')
    return result, running_time
