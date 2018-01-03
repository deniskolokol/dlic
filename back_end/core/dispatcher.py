from copy import deepcopy
from . import get_logger
from exception import ApiParamsError

log = get_logger('ersatz.dispatcher')


class ApiTrainDispatcher(object):
    def __init__(self, api_message):
        self.api_message = deepcopy(api_message)
        log.info('Api train dispatcher got message.')
        log.debug(api_message)
        self.data_type = api_message['data_type']
        if self.data_type == 'TIMESERIES':
            from .runners import TimeseriesEnsembleRunner
            self.runner = TimeseriesEnsembleRunner(api_message)
        elif self.data_type == 'IMAGES':
            from .runners import ImageEnsembleRunner
            self.runner = ImageEnsembleRunner(api_message)
        elif self.api_message['models'][0]['name'] == 'TSNE':
            from .runners import TSNEEnsembleRunner
            self.runner = TSNEEnsembleRunner(api_message)
        elif self.data_type == 'GENERAL':
            from .pylearn.runners import TrainRunner
            self.runner = TrainRunner(api_message)
        else:
            raise ApiParamsError('Invalid ensemble data type.')
        self.run()

    def run(self):
        self.runner.train_models()


class ApiPredictDispatcher(object):
    def __init__(self, api_message):
        self.api_message = deepcopy(api_message)
        log.info('Api predict dispatcher got message.')
        log.debug(api_message)
        self.data_type = api_message['data_type']
        if self.data_type == 'TIMESERIES':
            from .runners import MRNNPredictRunner
            predictor = MRNNPredictRunner(api_message)
            predictor.predict_models()
        elif self.data_type == 'IMAGES':
            from .predictors import predict_convnet
            predict_convnet(api_message)
        else:
            if self.api_message['predicts'][0]['model_name'] == 'AUTOENCODER':
                from .pylearn.runners import PylearnAutoencoderPredictRunner
                predictor = PylearnAutoencoderPredictRunner(api_message)
                predictor.predict_models()
            else:
                from .pylearn.runners import PylearnMLPPredictRunner
                predictor = PylearnMLPPredictRunner(api_message)
                predictor.predict_models()
