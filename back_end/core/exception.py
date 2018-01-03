import traceback


class BaseErsatzError(Exception):
    def __init__(self, *args, **kwargs):
        self.show_to_user = kwargs.pop('show_to_user', False)
        if 'original_traceback' in kwargs:
            self.original_traceback = kwargs.pop('original_traceback')
        else:
            self.original_traceback = traceback.format_exc()
        super(BaseErsatzError, self).__init__(*args, **kwargs)

    def get_traceback(self):
        if self.original_traceback is None:
            original_traceback = ''
        else:
            original_traceback = 'Original traceback:\n' + self.original_traceback + '\n\n'
        original_traceback += traceback.format_exc()
        print original_traceback
        return original_traceback

class DataFileError(BaseErsatzError):
    pass

class ApiParamsError(BaseErsatzError):
    pass

class ProgramSetupError(BaseErsatzError):
    pass

class ApiStoppedTraining(BaseErsatzError):
    pass

class AWSError(BaseErsatzError):
    pass

class UnstableModelException(BaseErsatzError):
    pass

class MRNNWorkerException(BaseErsatzError):
    pass
