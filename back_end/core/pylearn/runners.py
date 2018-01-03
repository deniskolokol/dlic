import os
import re
import StringIO
import uuid
import gzip
import json
import cPickle
import traceback
import collections
import numpy as np
from ..data.providers import CsvDataProvider
from ..data.dataset import get_dataset
from ..data.csv import GeneralDataset
from ..data import dataset
from .interface import (create_dense_design_matrix,
                        create_2d_dense_design_matrix)
from .trainers import (MaxOutTrainer, AutoEncoderTrainer, SigmoidTrainer,
                       RectifiedLinearTrainer, MaxOutConvTrainer)
from ..runners import BaseTrainRunner, BasePredictRunner
from .. import aws
from ..aws import S3Key
from ..exception import DataFileError
from ..conf import settings
from .. import spearmint_wrapper as swrap
from .. import hyperparams as hp

from theano import function


# TODO: fix pylearn2 crash with unicode params
def u_to_str(value):
    if isinstance(value, unicode):
        return str(value.encode('utf-8'))
    if isinstance(value, dict):
        temp = {}
        for k, v in value.iteritems():
            if isinstance(k, unicode):
                k = str(k)
            temp[k] = u_to_str(v)
        return temp
    if isinstance(value, list):
        return [u_to_str(x) for x in value]
    return value


class TrainRunner(BaseTrainRunner):
    def __init__(self, api_message):
        api_message = u_to_str(api_message)
        super(TrainRunner, self).__init__(api_message)

    def get_model_info(self):
        name = self._models[0]['name']
        output_len = self.get_output_len()
        params = {'MLP_MAXOUT': [MaxOutTrainer, output_len],
                  'MLP_MAXOUT_CONV': [MaxOutConvTrainer, output_len],
                  'AUTOENCODER': [AutoEncoderTrainer, 0],
                  'MLP_SIGMOID': [SigmoidTrainer, output_len],
                  'MLP_RECTIFIED': [RectifiedLinearTrainer, output_len]}
        return params[name]

    def get_output_len(self):
        try:
            output = [f for f in self.train_dataset['filters']
                      if f['name'] == 'outputs'][0]
            return len(output['columns'])
        except Exception as e:
            return 1

    def _train_models(self):
        self.trainer_class, output_len = self.get_model_info()
        train, test, valid = dataset.load(self.train_dataset,
                                          self.test_dataset,
                                          self.valid_dataset)
        self.dp = CsvDataProvider(train_datafile=train,
                                  test_datafile=test,
                                  valid_datafile=valid,
                                  output_len=output_len)
        if self.sp_results:
            self.sp_results = self.sp_results.strip().split('\n')
        else:
            self.sp_results = []

        for model in self._models:
            self.model = model
            self._train()

    def ensure_config(self, hyperparams):
        """
        Copies self.config to hyperparameters.conf.
        Leaves it as is, if self.config is empty or None
        (self.config contains updates to config from API).
        """
        config = hyperparams.get_conf_ordered()
        if (not self.config) or (self.config is None):
            return config

        for k, v in self.config.iteritems():
            for keyname in ['min', 'max']:
                try:
                    config[k][keyname] = self.config[k][keyname]
                except KeyError:
                    pass
        return config

    def ensure_hyperparams(self):
        """
        Extracts configuration for hyperparameters from config file,
        using OrderedDict, because order of element matters.

        Does it only for the training of the first model.
        """
        try:
            hyperparams = self.hyperparams
        except AttributeError:
            with open(os.path.join(settings.SPEARMINT, 'ersatz',
                                   self.model['name'].lower() + '.json'), 'r') as f:
                sp_config = json.loads(f.read(),
                                       object_pairs_hook=collections.OrderedDict)
                hyperparams = hp.HyperParams(sp_config.keys(), **sp_config)

        hyperparams.conf = self.ensure_config(hyperparams)

        return hyperparams

    def fill_hyperparams(self):
        """
        Fills hyper-parameters to train a new model. Parameters specified
        by user remain untouched, if they pass through validation.

        Uses hard-coded hyper-parameters for as many init values as defined
        in conf (normally the first two models).
        Launches spearmint-lite when fails to find standard params.
        """
        self.hyperparams = self.ensure_hyperparams()
        parms_user = hp.unroll_params(self.model['model_params'])

        try:
            parms_auto = self.hyperparams.get_init_values(len(self.sp_results))
        except (IndexError, KeyError):
            spw = swrap.SpearmintLightWrapper(project_name='ersatz',
                                              config=self.hyperparams.get_conf_ordered())
            parms_auto = spw.perform(self.sp_results)[-1][2:]

        self.hyperparams.set_values(parms_auto) # set calculated params
        for k, v in parms_user.iteritems():     # but respect user's choice
            self.hyperparams.set_value(k, v)

        model_params = hp.roll_params(self.hyperparams,
                                      self.model['model_params'])
        model_params = hp.validate_params(model_params, self.hyperparams.conf)
        self.model['model_params'] = model_params

    def update_sp_results(self, trainer):
        """
        Updates results after each model training for use it with spearmint
        on the next model.
        """
        reporters = ['MLPStatReporter', 'AutoEncoderStatReporter']
        try:
            stat_reporter = [x for x in trainer.train_obj.extensions
                             if x.__class__.__name__ in reporters][-1]
        except IndexError:
            sp_result = [str(x) for x in [.00001, 1.] + self.hyperparams.values()]
            self.sp_results.append(sp_result)
            return

        # First index is loss, second is training time.
        if stat_reporter.__class__.__name__ == 'MLPStatReporter':
            ind = [3, -1]
        elif stat_reporter.__class__.__name__ == 'AutoEncoderStatReporter':
            ind = [1, -1]

        loss = stat_reporter.train_outputs[-1][ind[0]]
        model_train_time = sum([e[ind[1]] for e in stat_reporter.train_outputs])

        sp_result = [loss, model_train_time] + self.hyperparams.values()
        sp_result = ' '.join([str(x) for x in sp_result])
        self.sp_results.append(sp_result)

    def _train(self):
        self.fill_hyperparams()

        self.report_start_training()

        resume, resume_data, s3_data = self.is_resume(self.model)
        trainer = self.trainer_class(self, self.model['model_params'],
                                     resume, resume_data, s3_data)
        trainer.train()

        self.update_sp_results(trainer)

        self.report_finish_training()

    def is_resume(self, model):
        resume = model.get('resume')
        if not resume:
            return False, None, None
        s3_data = model['resume_X']
        resume_data = aws.get_data(s3_data)
        resume_data = cPickle.loads(resume_data)
        return resume, resume_data, s3_data


#TODO: refactor more better
class PylearnBasePredictRunner(BasePredictRunner):
    def _predict_models(self):
        dp, error_lines = self._get_input_data()

        predicted_results, average = self._predict(dp, error_lines)

        if self.api_message.get('MODE') == 'DATASET':
            iteration_ids = []
            for val in predicted_results:
                s3_key = '/download/predict/result/%s/ensemble-%s-iteration-%s.csv.gz'
                s3_key = s3_key % (uuid.uuid4(), self.ensemble, val['iteration'])
                val['output'] = self._save_as_s3_file(val['output'], s3_key)
                iteration_ids.append(val['iteration'])

            if average != None:
                s3_key = '/download/predict/result/%s/avg-ensemble-%s-iterations-%s.csv.gz'
                s3_key = s3_key % (uuid.uuid4(), self.ensemble,
                                   '-'.join(str(x) for x in iteration_ids))
                average = self._save_as_s3_file(average, s3_key)

        return {'predictions': predicted_results,
                'ensemble_prediction': average}

    def _get_input_data(self):
        if self.api_message.get('MODE') == 'DATASET':
            dataset = get_dataset(self.api_message['dataset'])
        else:
            dataset = GeneralDataset()
            kwargs = self.api_message['dataset']['data']
            kwargs['with_header'] = False # Adjust for prediction
            norm_min_max = self.api_message['dataset']['norm_min_max']
            dataset.load_from_lines(self.input_data, with_output=False,
                                    norm_min_max=norm_min_max, **kwargs)
        try:
            error_lines = dataset.extra_params['error_lines']
        except KeyError:
            error_lines = []
        output_len = self.get_output_len(self.api_message['dataset'])
        dp = CsvDataProvider(train_datafile=dataset.get_predict_data(),
                             output_len=0, shuffle=False) # output_len is 0 in dataset for prediction

        return dp, error_lines

    def _predict(self, dp, error_lines):
        raise NotImplementedError()

    def _run_function(self, func, data):
        try:
            return func(data)
        except ValueError as e:
            m = re.match((r'^dimension mismatch in args to gemm '
                          r'\(\d+,(\d+)\)x\((\d+),\d+\).*'), e.message)
            if m:
                # TODO: add tests
                raise DataFileError(('Your data has dimension %s, '
                                     'but model trained on data '
                                     'with dimension %s') % m.groups(),
                                    show_to_user=True,
                                    original_traceback=traceback.format_exc())
            else:
                raise

    def _save_as_s3_file(self, rval, s3_key):
        raise NotImplementedError()

    def _fetch_model(self, predict):
        with S3Key(predict['s3_data']).get_file() as data:
            model = cPickle.load(data)['model']
        return model

class PylearnMLPPredictRunner(PylearnBasePredictRunner):
    def get_output_len(self, dataset_params):
        try:
            return [len(f['columns']) for f in dataset_params['filters']
                    if f['name'] == 'outputs'][0]
        except:
            return 1

    def _predict(self, dp, error_lines):
        output_len = self.get_output_len(self.api_message['dataset'])
        predicted_results = []

        average = []
        for predict in self._predicts:
            model = self._fetch_model(predict)
            model.set_batch_size(128)
            data_specs = (model.get_input_space(), 'features')

            num_classes = 1
            if predict['model_name'] == 'MLP_MAXOUT_CONV':
                dataset = create_2d_dense_design_matrix(x=dp.train_set_x,
                                                        y=np.zeros((dp.train_set_x.shape[0], 1)),
                                                        num_classes=num_classes,
                                                        axes=['c', 0, 1, 'b'])
            else:
                if predict['out_nonlin'] == 'LINEARGAUSSIAN':
                    num_classes = None
                dataset = create_dense_design_matrix(x=dp.train_set_x,
                                                     y=np.zeros((dp.train_set_x.shape[0], output_len)),
                                                     num_classes=num_classes)
            batches = dataset.iterator(mode='sequential',
                                       batch_size=128,
                                       data_specs=data_specs)
            Xb = model.get_input_space().make_batch_theano()
            Xb.name = 'Xb'
            ymf = model.fprop(Xb)
            ymf.name = 'ymf'
            f1 = function([Xb], [ymf])                

            rval = rval_avg = None
            for batch in batches:
                probs = self._run_function(f1, batch)[0]
                if predict['out_nonlin'] == 'LINEARGAUSSIAN':
                    result = np.around(probs.astype(np.double), 5)
                else:
                    result = probs.argmax(axis=1)

                if rval is None:
                    rval = result
                    rval_avg = probs
                else:
                    rval = np.hstack((rval, result))
                    rval_avg = np.vstack((rval_avg, probs))

            average.append(rval_avg)
            rval = self._translate_predictions(rval, error_lines=error_lines)

            predicted_results.append({
                'iteration': predict['iteration_id'],
                'output': rval,
                'probs': np.around(probs.astype(np.double), 3)
            })
        average = np.array(average).mean(axis=0)
        if self.api_message['predicts'][0]['out_nonlin'] == 'LINEARGAUSSIAN':
            average = np.around(average.astype(np.double), 5)
        else:
            average = average.argmax(axis=1)

        average = self._translate_predictions(average, error_lines=error_lines)

        return predicted_results, average

    def _save_as_s3_file(self, rval, s3_key):
        rval = '\n'.join((str(x) for x in rval))
        gz = StringIO.StringIO()
        f = gzip.GzipFile(fileobj=gz, mode='w')
        f.write(rval)
        f.close()
        aws.save_modeldata_to_filename(s3_key, gz.getvalue())
        return s3_key

    def get_output_len(self, dataset_params):
        try:
            return [len(f['columns']) for f in dataset_params['filters']
                    if f['name'] == 'outputs'][0]
        except:
            return 1

    def _translate_predictions(self, values, num_outputs=1, **kwargs):
        data_keys = self.api_message['dataset']['data']
        if data_keys['dtypes'][-1] == 'S':
            kls = np.array(data_keys['classes'][np.negative(num_outputs)])
            result = kls[values].astype(str)
        else:
            result = values
        error_lines = kwargs.get('error_lines', [])
        error_msg = 'ERROR'
        dtype_size = max(len(error_msg), result.dtype.itemsize)
        result = result.astype('|S%s' % dtype_size)
        for line in error_lines:
            try:
                result = np.insert(result, line, error_msg)
            except IndexError:
                result = np.append(result, error_msg)
        return result

class PylearnAutoencoderPredictRunner(PylearnBasePredictRunner):
    def _predict(self, dp, error_lines):
        predicted_results = []

        for predict in self._predicts:
            model = self._fetch_model(predict)
            dataset = create_dense_design_matrix(x=dp.train_set_x)
            data_specs = (model.get_input_space(), 'features')
            batches = dataset.iterator(mode='sequential',
                                       batch_size=128,
                                       data_specs=data_specs)

            X = model.get_input_space().make_batch_theano()
            X.name = 'X'
            y = model.encode(X)
            y.name = 'y'
            f1 = function([X], [y])

            val = None
            for batch in batches:
                results = self._run_function(f1, batch)[0]
                if val is None:
                    val = results
                else:
                    val = np.vstack((val, results))

            predicted_results.append({
                'iteration': predict['iteration_id'],
                'output': val
            })

        return predicted_results, None

    def _save_as_s3_file(self, rval, s3_key):
        gz = StringIO.StringIO()
        f = gzip.GzipFile(fileobj=gz, mode='w')
        np.savetxt(f, rval, delimiter=",", fmt="%.5f")
        f.close()
        aws.save_modeldata_to_filename(s3_key, gz.getvalue())
        return s3_key

