from copy import deepcopy
import time
import traceback
import json
import sys
import re
from . import get_logger
from .exception import ApiParamsError, ApiStoppedTraining
from . import api
from . import aws
from .mrnn.ersatz_train import train_timeseries, train_images, train_tsne
from .exception import BaseErsatzError
from .predictors import Predictor, RunEnsemblePredictor
from . misc import NPArrayEncoder
from .reporter import (RabbitReporterMixin, RabbitPipe, logs_transformer,
                       logs_saver, build_train_pipe, LogsBufferWatcher)
from .rabbit import get_connection
from .misc import Tee


log = get_logger('ersatz.runner')


class BasePredictRunner(object):

    def __init__(self, api_message):
        self.api_message = deepcopy(api_message)
        self.input_data = api_message.get('input_data')
        try:
            self.ensemble = api_message['ensemble']
            self.train_ensemble_id = api_message['train_ensemble_id']
            self.queue_key = api_message['queue_key']
            self.options = api_message['options']
            self.quantiles = api_message['quantiles']
            self._predicts = api_message['predicts']
        except KeyError as e:
            raise ApiParamsError(e.message)

    def predict_models(self):
        self.start_time = time.time()
        try:
            result = self._predict_models()
        except BaseErsatzError as e:
            if e.show_to_user:
                self.report_error(error=e.message,
                                  orig_traceback=e.original_traceback)
            else:
                self.report_error(orig_traceback=e.original_traceback)
        except:
            self.report_error()
        else:
            self.report_result(result)

    def _predict_models(self):
        raise NotImplementedError

    def report_error(self, error='Predict failed', orig_traceback=None):
        if orig_traceback is None:
            orig_traceback = ''
        else:
            orig_traceback = 'Original traceback:\n' + orig_traceback + '\n\n'
        orig_traceback += traceback.format_exc()
        print orig_traceback
        params = {'ensemble': self.ensemble,
                  'traceback': orig_traceback,
                  'error': error,
                  'queue_key': self.queue_key,
                  'state': 'ERROR',
                  'time': time.time() - self.start_time}
        api.post('/api/predict-ensemble/status/', params)
        print 'stop processing ensemble'
        print '#' * 80

    def report_result(self, result):
        data = {
            'ensemble': self.ensemble,
            'queue_key': self.queue_key,
            'time': time.time() - self.start_time,
            'results': result
        }
        api.post('/api/predict-ensemble/status/', data)


class MRNNPredictRunner(BasePredictRunner):

    def _predict_models(self):
        if self.api_message.get('MODE') == 'DATASET':
            predictor = RunEnsemblePredictor(**self.api_message)
            result = predictor.run_ensemble()
        else:
            predictor = Predictor(**self.api_message)
            result = predictor.predict(input_data=self.input_data)
        return result


class BaseTrainRunner(RabbitReporterMixin):

    def __init__(self, api_message):
        # initialize training pipe
        ensemble_id = api_message.get('ensemble', 0)
        model_id = api_message['models'][0].get('id', 0)
        self.train_pipe = build_train_pipe(ensemble_id, model_id)
        self.api_message = api_message

        self.initialize_train_pipe()
        self.initialize_stats_reporter()
        self.mount_pipes()

        try:
            self.ensemble = api_message['ensemble']
            self.train_dataset = api_message['train_dataset']
            self.queue_key = api_message['queue_key']
            self.options = api_message['options']
            self.sp_results = api_message['sp_results']
            self.config = api_message['config']
            self._models = api_message['models']
        except KeyError as e:
            raise ApiParamsError(e.message)
        self.test_dataset = api_message.get('test_dataset')
        self.valid_dataset = api_message.get('valid_dataset')

    def train_models(self):
        sys.stdout = Tee('stdout', self.train_pipe)

        try:
            self._train_models()
        except ApiStoppedTraining:
            pass
        except BaseErsatzError as e:
            if e.show_to_user:
                self.report_error(e.message,
                                  orig_traceback=e.original_traceback)
            else:
                self.report_error(orig_traceback=e.original_traceback)
        except:
            self.report_error()

        # cleanup
        sys.stdout.close()
        sys.stderr.close()
        self.train_pipe.close()  # close logs pipe
        self.report_pipe.close() # close stats pipe

    def _train_models(self):
        raise NotImplementedError

    def is_resume(self):
        raise NotImplementedError

    def initialize_train_pipe(self):
        # initialize training pipe
        ensemble_id = self.api_message.get('ensemble', 0)
        model_id = self.api_message['models'][0].get('id', 0)
        routing_key = 'ensemble.%d.model.%d' % (ensemble_id, model_id)
        pre_hooks = [logs_transformer(model_id)]
        post_hooks = [logs_saver(model_id)]
        self.train_pipe = RabbitPipe(get_connection(),
                                     exchange_name='training_logs',
                                     exchange_type='topic',
                                     routing_key=routing_key,
                                     buffer_age=2,
                                     pre_hooks=pre_hooks,
                                     post_hooks=post_hooks)

    def mount_pipes(self):
        # capture stdout and stderr starting from instantiation
        sys.stdout = Tee('stdout', self.train_pipe)
        sys.stderr = Tee('stderr', self.train_pipe)

    def report_start_training(self):
        api_params = {'model': self.model['id'],
                      'state': 'TRAIN',
                      'model_name': self.model['name'],
                      'queue_key': self.queue_key,
                      'model_params': self.model['model_params']}

        if not api.post('/api/train/status/', api_params):
            log.warn("Can't set model status to TRAIN (api response not 200)")
            raise ApiStoppedTraining
        self.training_start_time = time.time()

    def report_finish_training(self):
        api_params = {'model': self.model['id'], 'state': 'FINISHED',
                      'model_name': self.model['name'],
                      'queue_key': self.queue_key,
                      'sp_results': self.sp_results[-1],
                      'detailed_results': "all fine"}
        if not api.post('/api/train/status/', api_params):
            log.warn("Can't set model status to FINISHED (api response not 200)")
            raise ApiStoppedTraining

    def report_error(self, error='Training failed', orig_traceback=None):
        if orig_traceback is None:
            orig_traceback = ''
        else:
            orig_traceback = 'Original traceback:\n' + orig_traceback + '\n\n'
        orig_traceback += traceback.format_exc()
        print orig_traceback
        params = {'ensemble': self.ensemble,
                  'traceback': orig_traceback,
                  'error': error,
                  'queue_key': self.queue_key}
        api.post('/api/ensemble/status/', params)
        print 'stop processing ensemble'
        print '#' * 80
        return

    def report_stats(self, modeldata, stats, upload_modeldata=True):
        log.info('Reporting stats.')
        if upload_modeldata:
            start_time = time.time()
            s3_data = aws.upload_modeldata(modeldata,
                                           self.model.get('resume_X'),
                                           self.model['id'])
            self.model['resume_X'] = s3_data
            log.debug('Model data uploading time: %s seconds' %
                      (time.time() - start_time))
            if s3_data is None:
                print "s3_data is None", self.id
                log.critical('Model data uploading returned None. Stop training.')
                raise Exception
        else:
            s3_data = self.model.get('resume_X')
        stats['time'] = time.time() - self.training_start_time
        payload = {
            'model': self.model['id'],
            'model_name': self.model['name'],
            's3_data': s3_data,
            'queue_key': self.queue_key,
            'data': stats
        }
        start_time = time.time()

        # publish stats first
        self.stats_publish(json.dumps(payload, cls=NPArrayEncoder))

        # then persist stats
        if not api.post('/api/stats/', payload):
            log.critical('Post stats to api failed. Stop training.')
            raise ApiStoppedTraining

        log.debug('Report stats time: %s seconds' % (time.time() - start_time))
        self.model['last_report_epoch'] = stats['iteration'] + 1
        self.training_start_time = time.time()


class ImageEnsembleRunner(BaseTrainRunner):

    def __init__(self, api_message):
        super(ImageEnsembleRunner, self).__init__(api_message)
        self.api_message = api_message

    def _train_models(self):
        train_images(self.api_message)


class TimeseriesEnsembleRunner(BaseTrainRunner):

    def __init__(self, api_message):
        super(TimeseriesEnsembleRunner, self).__init__(api_message)
        self.config = api_message.get('config', None)
        self.quantiles = api_message.get('quantiles', None)
        self.sp_results = api_message.get('sp_results', None)
        self.api_message = api_message

    def _train_models(self):
        train_timeseries(self.api_message, self)


class TSNEEnsembleRunner(BaseTrainRunner):
    
    def __init__(self, api_message):
        super(TSNEEnsembleRunner, self).__init__(api_message)

        # pipe stdout to both train_pipe (for console output on ui)
        # and report_pipe (for live stats and d3 graph updates)
        buffer_age = 2
        self.report_pipe.buffer_age = buffer_age
        self.report_pipe.donotflush = True
        self.report_pipe.buffer_watcher = LogsBufferWatcher(self.report_pipe, buffer_age)
        self.report_pipe.buffer_watcher.start()

        #TODO de-duplicate call to _extract_stats:
        self.report_pipe.pre_hooks = [self._report_pipe_pre_hook]
        self.report_pipe.publish_conditions = [lambda x: self._extract_stats(x)]

        # pattern for iteration line matching
        self.iteration_pattern = re.compile('\[t-SNE\] Iteration (\d+): error = (\d+.?\d*), gradient norm = (\d+.?\d*)')

    def mount_pipes(self):
        # override so we could mount stdout to both report and train pipes
        sys.stdout = Tee('stdout', self.train_pipe, self.report_pipe)
        sys.stderr = Tee('stderr', self.train_pipe)

    def _train_models(self):
        # since we're not calling self.report_start_training,
        # we set training start time manually
        self.training_start_time = time.time()

        train_tsne(self.api_message, self._pre_finish_callback)

    def _pre_finish_callback(self, model):
        # all stats should be reported before this ends
        # otherwise when the status is set to FINISHED,
        # late stats are not accepted.

        # once training is done, flush logs and stats
        self.train_pipe.flush()
        self.report_pipe.donotflush = False
        self.report_pipe.flush()

    def _report_pipe_pre_hook(self, data):
        stats_list = self._extract_stats(data)

        # if we're unable to extract any stats,
        # just return the data as it is
        if not stats_list:
            return data

        payload = self._make_payload(self._models[0], stats_list)

        # persist stats
        if not api.post('/api/stats/', payload):
            log.critical('Post stats to api failed.')

        return json.dumps(payload, cls=NPArrayEncoder)

    def _extract_stats(self, rawdata=None):
        rawdata = rawdata if rawdata else self.report_pipe.buffer
        output = ''.join(rawdata)
        lines = output.strip().split('\n')
        stats_list = []
        for line in lines:
            match = self.iteration_pattern.match(line)
            if match:
                iteration, error, gradient_norm = match.groups()
                stats_list.append({'iteration': int(iteration),
                                   'error': float(error),
                                   'gradient_norm': float(gradient_norm)})
        return stats_list

    def _make_payload(self, model, stats_list): 
        training_time = time.time() - self.training_start_time
        outputs_header = ['iteration', 'error', 'gradient_norm']

        modeldata = {
            'model': model,
            'epoch': 1,
            'train_outputs': stats_list,
            'outputs_header': outputs_header,
        }

        s3_data = self._upload_modeldata(modeldata, model)
        payload = {
            'model': self.api_message['models'][0]['id'],
            'model_name': self.api_message['models'][0]['name'],
            's3_data': s3_data,
            'queue_key': self.api_message['queue_key'],
            'data': {
                'iteration': int(stats_list[-1]['iteration']),
                'test_accuracy': 0.1,
                'train_accuracy': 0.1,
                'outputs_header': outputs_header,
                'time': training_time,
                'train_outputs': stats_list
            }
        }

        return payload

    def _upload_modeldata(self, modeldata, model):
        start_time = time.time()
        s3_data = aws.upload_modeldata(modeldata,
                                       model.get('resume_X'),
                                       model['id'])
        log.debug('Model data uploading time: %s seconds' %
                  (time.time() - start_time))
        return s3_data
