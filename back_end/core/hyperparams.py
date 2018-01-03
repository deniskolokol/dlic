from collections import OrderedDict, Mapping


def set_path_dict(path, val, container={}):
    """
    Creates a nested dictionary, provided the path and value, recursively.
    Parameters:
      container - should be empty dict {}
      path - list or tuple representing path to be created,
             e.g. ['top', 'mid', 'bot']
      val - value to be set to the key in the deepest level.
    Result:
      container = {'top': {'mid': {'bot': val}}}
    """
    if len(path) == 1:
        container[path[0]] = val
    else:
        set_path_dict(path[1:], val, container.setdefault(path[0], {}))
    return container


def update_nested(dest, upd):
    """
    Updates dictionary recursively, respects nested
    structures, e.g. ['momentum']['init'].
    Parameters:
      dest - destination dict, e.g.
             {'p': {'p1': 1,
                    'p2': 2,
                    'p3': {'p3_1': 31, 'p3_2': 32}}}
      upd - dict to update dest, e.g. {'p3': {'p3_1': 3100.}}
    Returns: {'p': {'p1': 1,
                    'p2': 2,
                    'p3': {'p3_1': 3100., 'p3_2': 32}}}
    """
    for k, v in upd.iteritems():
        if isinstance(v, Mapping):
            r = update_nested(dest.get(k, {}), v)
            dest[k] = r
        else:
            dest[k] = upd[k]
    return dest


def unroll_params(params, unrolled={}, parent=None):
    """
    Recursively flattens nested dictionaries of arbitrary number of levels.
    Example:
    {'learning_rate': {'init': 0.001,
                       'save': {'iter': 20,
                                'stop': 100}}}
    becomes
    {'learning_rate_init': 0.001,
     'learning_rate_save_iter': 20,
     'learning_rate_save_stop': 100}
    """
    for key, val in params.iteritems():
        updated_key = '%s_%s' % (parent, key) if parent else key
        if isinstance(val, dict):
            unroll_params(val, unrolled, updated_key)
        else:
            unrolled[updated_key] = val
    return unrolled

def roll_params(fro, to):
    """
    Updates parameters taking care of nested structures.
    """
    for param_name, param_val in fro.as_dict().iteritems():
        if 'path' in fro[param_name].conf.keys():
            sub_param = set_path_dict(fro[param_name].conf['path'],
                                      param_val)
            update_nested(to, sub_param)
        else:
            to[param_name] = param_val
    return to


def validate_params(params, conf):
    """
    Validates parameters:
    """
    try:
        if params['learning_rate']['init'] < params['learning_rate']['final']:
            params['learning_rate']['init'] = conf['learning_rate_init']['init'][0]
            params['learning_rate']['final'] = conf['learning_rate_final']['init'][0]
    except KeyError:
        pass
    try:
        if params['momentum']['init'] > params['momentum']['final']:
            params['momentum']['init'] = conf['momentum_init']['init'][0]
            params['momentum']['final'] = conf['momentum_final']['init'][0]
    except KeyError:
        pass

    return params

class AttrDict(dict):
    """
    Dictionary that acts like a class, i.e. access its keys as attributes.

    **kwargs set attributes and their values.
    *args specifies order of attributes.
    """
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(**kwargs)
        self.__dict__ = self

        # `names` specifies order of (key, value) pair.
        self.names = list(args)

    def as_dict(self):
        """
        Returns keys and values of the instance as unordered
        dictionary, excluding `names` attribute.
        """
        return dict((k, self[k]) for k in self.names)

    def as_ordered_dict(self):
        """
        Returns instance keys and values of the instance
        as ordered dictionary as specified by `names` attribute.
        """
        return OrderedDict((k, self[k]) for k in self.names)


class HyperParamConf(AttrDict):
    """
    Describes configuration of a hyperparameter.

    Example of usage:
    conf_names = ('name', 'type', 'min', 'max', 'size')
    conf_dict = {'max': 20, 'min': 20, 'name': 'maxnum_iter', 'size': 1, 'type': 'int'}
    conf = HyperParamConf(*conf_names, **conf_dict)

    Call attributes:
    conf.type
    conf.name
    conf.names # returns order of elements
    """
    def __init__(self, *args, **kwargs):
        super(HyperParamConf, self).__init__(*args, **kwargs)


class HyperParam(AttrDict):
    """
    Describes single hyperparameter (its conf and value).
    Order of the keys is pre-defined by self.conf_names.

    Example of usage:
    conf_dict = {'max': 20, 'min': 20, 'name': 'maxnum_iter', 'size': 1, 'type': 'int'}
    hp_maxnum_iter = HyperParam(conf_dict)

    Call attributes:
    hp_maxnum_iter.name
    hp_maxnum_iter.value                  # returns None after initialization
    hp_maxnum_iter.names                  # order of elements
    hp_maxnum_iter.conf                   # instance of HyperParamConf class (dict)
    hp_maxnum_iter.conf.as_ordered_dict() # ordered conf of the param

    Set value:
    hp_maxnum_iter.value = 123
    """
    conf_names = ('name', 'type', 'min', 'max', 'size', 'init', 'path')

    def __init__(self, conf):
        # Initialize it empty (value = None).
        super(HyperParam, self).__init__(**{'value': None})

        # Describe its configuration (filling up `names` for ordering).
        self.conf = HyperParamConf(*self.conf_names, **conf)

        # Name it.
        self.name = self.conf.name


class HyperParams(AttrDict):
    """
    Describes collection of hyperparameter, each item of which is
    an instance of HyperParam class.

    Example of usage:
    maxnum_iter_conf = {'max': 20, 'min': 20, 'name': 'maxnum_iter', 'size': 1, 'type': 'int'}
    mu_conf = {'max': 0.1, 'min': 0.001, 'name': 'mu', 'size': 1, 'type': 'float'}
    maxnum_iter = HyperParam(maxnum_iter_conf)
    mu = HyperParam(mu_conf)

    Set values:
    mu.value = 0.05
    maxnum_iter.value = 12
    hpr = HyperParams(('maxnum_iter', 'mu'))
    hpr.mu = mu
    hpr.maxnum_iter = maxnum_iter

    # Re-define value (works only if `maxnum_iter` exists):
    hpr.maxnum_iter.value = 15

    # In other case - this way:
    hpr.set_value(maxnum_iter, 15)

    Call attributes:
    hpr.mu.conf
    hpr.as_ordered_dict()
    hpr.as_dict()
    """

    def __init__(self, names=(), **conf):
        # Initialize: fill .names (order of parameters)
        # and .conf (dict for .conf_names).
        super(HyperParams, self).__init__(*names)

        # **conf may come as OrderedDict, convert to dict.
        self.conf = {}
        for key, sett in conf.iteritems():
            self.conf[key] = dict((k, v) for k, v in sett.iteritems())            

    def as_dict(self):
        """
        Returns instance keys and values of the instance
        as unordered dictionary, excluding all other attributes.
        """
        return dict((n, self[n].value) for n in self.names)

    def as_ordered_dict(self):
        """
        Returns instance keys and values of the instance
        as ordered dictionary as specified by `names` attribute.
        """
        return OrderedDict((n, self[n].value) for n in self.names)

    def values(self):
        return [self[n].value for n in self.names]

    def fill_conf(self):
        self.conf = {}
        for name in self.names:
            self.conf[name] = dict((n, self[name].conf[n])
                                   for n in self[name].conf.names)

    def get_conf(self):
        if not self.conf:
            self.fill_conf()

        return self.conf

    def get_conf_ordered(self):
        conf = OrderedDict()
        for name in self.names:
            # Try to obtain conf from keys (ordered).
            try:
                conf[name] = OrderedDict((n, self[name].conf[n])
                                         for n in self[name].conf.names)
            # No data yet - use unordered dict for each conf key.
            except KeyError:
                conf[name] = self.conf[name]

        return conf

    def get_init_values(self, index):
        """
        Returns a list of the initial values as specified in conf,
        ordered according to self.names.
        """
        return [self.conf[n]['init'][index] for n in self.names]

    def set_value(self, name, value):
        """
        Creates or updates HyperParam with a given value.
        """
        try:
            hp = HyperParam(self.conf[name])
        except KeyError:
            return

        hp.value = value
        self[name] = hp

    def set_values(self, values):
        """
        Fills values from list or dict.

        If `values` is a dict, it should contain all the keys from `self.name`.
        In case it is a list, its len and order should be equal to the len and
        order defined by `self.name`.
        """
        # Convert values to list, if it's a dict.
        if isinstance(values, dict):
            values = [values[n] for n in self.names]

        # Control number of elements.
        if len(values) != len(self.names):
            raise Exception('Number of values (%d) should be equal to the number of names (%d)!' % \
                            len(values), len(self.names))
        # Set values.
        for i, name in enumerate(self.names):
            self.set_value(name, values[i])
