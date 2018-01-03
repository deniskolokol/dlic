import os
import sys
import shutil
import json
import string
from collections import OrderedDict

# Spearmint lives in spearmint-lite.py
from spearmint_proxy import spearmint_lite
SPEARMINT_ROOT = os.path.dirname(os.path.realpath(spearmint_lite.__file__))
execfile(os.path.join(SPEARMINT_ROOT, 'spearmint-lite.py'))


class SpearmintOptions():
    """
    Surrogate class to pass options to spearmint_lite.
    """
    def __init__(self, **kwargs):
        self.num_jobs = kwargs.get('num_jobs', 1)
        self.grid_seed = kwargs.get('grid_seed', 1)
        self.grid_size = kwargs.get('grid_size', 1000)
        self.max_finished_jobs = kwargs.get('max_finished_jobs', 1000)
        self.chooser_module = kwargs.get('chooser_module', 'GPEIChooser')
        self.chooser_args = kwargs.get('chooser_args', '')
        self.config_file = kwargs.get('config_file', 'config.json')
        self.results_file = kwargs.get('results_file', '')


class SpearmintLightWrapper(object):
    """
    Wraps up spearmint-lite calling it transparently.

    Parameters:
    * project_name - if blank, a new temp directory will be created:
      /path/to/spearmint-lite/<project_name>

    * config - parameters configuration (dictionary).
      If blank, SpearmintLightWrapper tries to find file 
      /path/to/spearmint-lite/<project_name>/config.json

    * opts - spearmint options (dictionary).
      Use it to re-define default options. For the list of default options
      see SpearmintOptions class.
    """

    folder_created = False
    config_created = False
    dat_created = False

    def __init__(self, project_name, opts={}, config=None):
        self.project_name = project_name
        self.project_root = os.path.join(SPEARMINT_ROOT, self.project_name)

        opts = self.check_type(opts, 'opts', dict)

        if config:
            self.config = self.check_type(config, 'config', OrderedDict)

        if 'config_file' not in opts:
            opts['config_file'] = 'config.json'
        self.config_filename = opts['config_file']

        if 'results_file' not in opts:
            opts['results_file'] = self.id_generator(size=12) + '.dat'
        self.filename = opts['results_file']

        # Default options.
        self.opts = SpearmintOptions(**opts)

    def check_type(self, param_val, param_name, param_type):
        if not isinstance(param_val, param_type):
            raise TypeError('Parameter %s should be %s (got %s instead)!' % \
                            (param_name, param_type, type(param_val)))
        return param_val

    def id_generator(self, size=6, chars=string.ascii_lowercase+string.digits):
        """
        Generates quazi-unique sequence from random digits and letters.
        """
        import random
        return ''.join(random.choice(chars) for x in range(size))

    def _remove_chooser_file(self):
        """
        Removes chooser file to avoid this exception:
        https://github.com/JasperSnoek/spearmint/issues/9

        Respects the filename: depending on the version of spearmint
        it can be ChooserName.pkl or chooser.ChooserName.pkl.
        """
        try:
            for spfile in os.listdir(self.project_root):
                if ("%s.pkl" % self.opts.chooser_module) in spfile:
                    os.remove(os.path.join(self.project_root, spfile))
        except OSError:
            return

    def _ensure_config_file(self, update_config=None):
        """
        Ensures config file is in place (updates or create).
        `update_config` is OrderedDictionary with a new config. The original
        one is returned as in `orig_conf`.
        """
        if update_config is None:
            update_config = self.config

        conf_file = os.path.join(self.project_root, self.config_filename)
        try:
            f = open(conf_file, 'r+')
            orig_conf = json.loads(f.read(),
                                   object_pairs_hook=collections.OrderedDict)
            f.seek(0)
        except IOError:
            f = open(conf_file, 'w')
            orig_conf = self.config.copy()

        f.write(json.dumps(update_config, indent=4))
        f.truncate()
        f.close()

        return orig_conf

    def setUp(self):
        """
        Ensures all temporary folders and files are in place
        (creates if they aren't).
        """
        # Ensure project root folder.
        if not os.path.exists(self.project_root):
            os.makedirs(self.project_root)
            self.folder_created = True

        # Ensure config file.
        self.original_config = self._ensure_config_file(self.config)

        # Write experiments file.
        if self.experiments:
            with open(os.path.join(self.project_root, self.filename), 'w') as f:
                for exp in self.experiments:
                    f.write(exp + '\n')
                f.close()
                self.dat_created = True

        # Removes <chooser>.pkl before starting spearmint-lite.
        self._remove_chooser_file()

    def cleanUp(self):
        """
        Deletes all temporary files (only those that were created).
        """
        if self.folder_created:
            shutil.rmtree(self.project_root)
        else:
            if self.dat_created:
                os.remove(os.path.join(self.project_root, self.filename))

            # Revert config file to its original form
            self.config = self._ensure_config_file(self.original_config)

        # Removes <chooser>.pkl after spearmint-lite returns results.
        self._remove_chooser_file()

    def _adjust_types(self, data):
        """
        Sets proper types to the result of spearmint prediction
        after extracting them from the file (basestring)
        """
        result = []
        for num, line in enumerate(data):
            result.append(list())
            for x in line:
                if x.isdigit():
                    result[num].append(int(x))
                else:
                    try:
                        result[num].append(float(x))
                    except ValueError:
                        result[num].append(x)
        return result

    def _do_perform(self):
        self.setUp()

        # Do it!
        main_controller(self.opts, [self.project_root])

        # Collect results.
        result_file = open(os.path.join(self.project_root, self.filename), 'rb')
        result_data = [line.strip().split(' ') for line in result_file.readlines()]

        # Clean all files created in the process.
        self.cleanUp()

        return self._adjust_types(result_data)

    def perform(self, experiments=None):
        """
        Perform prediction using spearmint_lite.
        It is assumed, all the options are already defined (see __init__).

        Parameters:
        * experiments - list of strings of space delimited parameters
          as descriped in self.config. Example:
            ['.1  50.    0.1796875 0.3046875',
             '.05 49.896 0.6796875 0.8046875']

        Returns list of lists of all the parameters.
        Thus the last prediction can be obtained like so: result[-1][2:]
        """
        # Ensure list of basestrings.
        for i, elm in enumerate(experiments):
            if isinstance(elm, list):
                experiments[i] = ' '.join([str(e) for e in elm])

        self.experiments = experiments
        return self._do_perform()
