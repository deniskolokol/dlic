from collections import OrderedDict


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
    conf_dict = {
        'max': 20, 'min': 20, 'name': 'maxnum_iter', 'size': 1, 'type': 'int'
    }
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
    conf_dict = {
        'max': 20, 'min': 20, 'name': 'maxnum_iter', 'size': 1, 'type': 'int'
    }
    hp_maxnum_iter = HyperParam(conf_dict)

    Call attributes:
    hp_maxnum_iter.name
    hp_maxnum_iter.value  # returns None after initialization
    hp_maxnum_iter.names  # order of elements
    hp_maxnum_iter.conf   # instance of HyperParamConf class (dict)
    hp_maxnum_iter.conf.as_ordered_dict()  # ordered conf of the param

    Set value:
    hp_maxnum_iter.value = 123
    """
    conf_names = ('name', 'type', 'min', 'max', 'size')

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
    maxnum_iter_conf = {
        'max': 20, 'min': 20, 'name': 'maxnum_iter', 'size': 1, 'type': 'int'
    }
    mu_conf = {
        'max': 0.1, 'min': 0.001, 'name': 'mu', 'size': 1, 'type': 'float'
    }
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
        hp = HyperParam(self.conf[name])
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
            raise Exception('Number of values (%d) should be equal to the '
                            'number of names (%d)!'
                            % (len(values), len(self.names)))
        # Set values.
        for i, name in enumerate(self.names):
            self.set_value(name, values[i])
