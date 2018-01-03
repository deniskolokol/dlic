import os
from unipath import Path
from ..exception import ProgramSetupError
from . import global_settings

class Settings(object):
    def __init__(self):
        # TODO: check all settings without default value
        try:
            settings_module = os.environ['ERSATZ_SETTINGS']
        except KeyError:
            raise ProgramSetupError('Settings are not configured')
        submod = settings_module.rsplit('.', 1)[-1]
        mod = __import__(settings_module)
        mod = getattr(mod, submod)
        for attr_ in dir(global_settings):
            if attr_ == attr_.upper():
                try:
                    setattr(self, attr_, getattr(mod, attr_))
                except AttributeError:
                    setattr(self, attr_, getattr(global_settings, attr_))

    def post_update(self):
        self.check_paths()

    def check_paths(self):
        paths = 'PROJECT_DIR SPEARMINT WORKING_DIR S3_CACHEDIR CONVNET'
        for path in paths.split():
            if not isinstance(getattr(self, path), Path):
                raise ProgramSetupError


settings = Settings()

def get_api_port():
    port = settings.API_SERVER.split(':')
    if len(port) == 3:
        try:
            return int(port[2])
        except ValueError:
            pass
    raise ValueError('Can\'t find api port')
