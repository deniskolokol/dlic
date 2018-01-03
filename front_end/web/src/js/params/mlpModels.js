/* global Backbone */
/* global _ */

"use strict";


var mlpComponents = require('./mlpComponents.jsx'),
    MLPModelComponent = mlpComponents.mlp,
    Utils = require('../Utils.js');

_.extend(Backbone.Model.prototype, Backbone.Validation.mixin, Utils.ApplyTypesMixin);
Backbone.Validation.configure({labelFormatter: 'label'});


var BaseLayer = Backbone.Model.extend({
    initialize: function() {
        if (this.get('switch_uniform_init') === undefined) {
            if (this.get('irange') === undefined) {
                this.set('switch_uniform_init', false);
            } else {
                this.set('switch_uniform_init', true);
            }
        }
    },

    dumpParams: function() {
        var params = _.clone(this.attributes);
        params = this.selectWeightInit(params);
        return this.applyTypes(params);
    },

    isParamsValid: function() {
        var params = _.clone(this.labels);
        this.validate();
        params = this.selectWeightInit(params);
        return this.isValid(_.keys(params));
    },

    selectWeightInit: function(params) {
        if (this.get('switch_uniform_init')) {
            delete params.sparse_init;
        } else {
            delete params.irange;
        }
        delete params.switch_uniform_init;
        return params;
    },

    labels: {
        'irange': "Range of uniform initialization",
        'switch_uniform_init': "",
        'sparse_init': "Initial sparseness",
        'dim': "Number of hidden units"
    },

    validation: {
        'dim': {
            required: true,
            pattern: 'digits',
            range: [1, 1000]
        },
        'sparse_init': {
            required: true,
            pattern: 'digits',
            range: [0, 100]
        },
        'irange': {
            required: true,
            pattern: 'number',
            range: [1e-10, 1]
        }
    }
});

var BaseLayersList = Backbone.Collection.extend({
    model: BaseLayer,

    isParamsValid: function() {
        if (this.length > 0) {
            return this.reduce(function(prev, cur) { return prev && cur.isParamsValid(); }, true);
        }
    },

    dumpParams: function() {
        var params;
        return this.map(function(layer, i) {
            params = layer.dumpParams();
            params.layer_name = 'h' + i;
            return params;
        });
    }
});

var MaxoutLayer = BaseLayer.extend({
    labels: {
        'num_units': 'Number of hidden units',
        'num_pieces': 'Number of pieces',
        'irange': "Range of uniform initialization",
        'switch_uniform_init': "",
        'sparse_init': "Initial sparseness",
        'max_col_norm': 'Max column norm'
    },

    validation: {
        'num_units': {
            required: true,
            pattern: 'digits',
            range: [1, 1000]
        },
        'num_pieces': {
            required: true,
            pattern: 'digits',
            range: [1, 1000]
        },
        'irange': {
            required: true,
            pattern: 'number',
            range: [1e-10, 1]
        },
        'sparse_init': {
            required: true,
            pattern: 'digits',
            range: [0, 100]
        },
        'max_col_norm': {
            required: true,
            pattern: 'number',
            min: 0.1
        }
    }
});

var MaxoutLayersList = BaseLayersList.extend({
    model: MaxoutLayer
});

var MaxoutConvLayer = BaseLayer.extend({
    initialize: function() {
        // do not use base initialization of switch uniform init
    },

    labels: {
        'num_units': 'Number of hidden units',
        'num_pieces': 'Number of pieces',
        'irange': 'Range of uniform initialization',
        'kernel_shape': 'Kernel shape',
        'pool_shape': 'Pool shape',
        'pad': 'Padding',
        'pool_stride': 'Pool stride',
        'max_kernel_norm': 'Max kernel norm'
    },

    selectWeightInit: function(params) {
        return params;
    },

    validation: {
        'num_units': {
            required: true,
            pattern: 'digits',
            range: [1, 1000]
        },
        'num_pieces': {
            required: true,
            pattern: 'digits',
            range: [1, 1000]
        },
        'irange': {
            required: true,
            pattern: 'number',
            range: [1e-10, 1]
        },
        'kernel_shape': {
            required: true,
            pattern: 'digits',
            range: [1, 1000]
        },
        'pool_shape': {
            required: true,
            pattern: 'digits',
            range: [1, 1000]
        },
        'pad': {
            required: true,
            pattern: 'digits',
            range: [0, 1000]
        },
        'pool_stride': {
            required: true,
            pattern: 'digits',
            range: [0, 1000]
        },
        'max_kernel_norm': {
            required: true,
            pattern: 'number',
            min: 0.1
        }
    }
});

var MaxoutConvLayersList = BaseLayersList.extend({
    model: MaxoutConvLayer
});

var LearningRateModel = Backbone.Model.extend({
    dumpParams: function() {
        var params = _.clone(this.attributes);
        if (params.constant) {
            params = {init: params.init, constant: true};
        }
        return this.applyTypes(params);
    },

    isParamsValid: function() {
        this.validate();
        if (this.get('constant')) {
            return this.isValid('init');
        } else {
            return this.isValid();
        }
    },

    labels: {
        'constant': '',
        'init': 'initial learning rate',
        'final': 'final learning rate',
        'decay_factor': 'Decay factor'
    },

    validation: {
        'init': {
            required: false,
            pattern: 'number',
            range: [1e-10, 100]
        },
        'final': {
            required: false,
            pattern: 'number',
            range: [1e-10, 100],
            fn: 'gtInit'
        },
        'decay_factor': {
            required: false,
            pattern: 'number',
            range: [1, 100]
        }
    },

    gtInit: function(fin, attr, state) {
        if (state.init !== undefined && fin !== undefined &&
            parseFloat(state.init) <= parseFloat(fin)) {
            return "should be lower then initial";
        }
    }
});

var MomentumModel = Backbone.Model.extend({
    dumpParams: function() {
        var params = _.clone(this.attributes);
        if (params.constant) {
            params = {init: params.init, constant: true};
        }
        return this.applyTypes(params);
    },

    isParamsValid: function() {
        this.validate();
        if (this.get('constant')) {
            return this.isValid('init');
        } else {
            return this.isValid();
        }
    },

    labels: {
        'constant': '',
        'init': 'initial momentum',
        'final': 'final momentum',
        'start': 'start',
        'stop': "stop"
    },


    validation: {
        'init': {
            required: false,
            pattern: 'number',
            range: [1e-10, 10]
        },
        'final': {
            required: false,
            pattern: 'number',
            range: [1e-10, 10],
            fn: 'gtInit'
        },
        'start': {
            required: false,
            pattern: 'digits',
            range: [1, 10000]
        },
        'stop': {
            required: false,
            pattern: 'digits',
            range: [1, 10000],
            fn: 'gtStart'
        },
    },

    gtInit: function(fin, attr, state) {
        if (state.init !== undefined && fin !== undefined &&
            parseFloat(state.init) >= parseFloat(fin)) {
            return "should be greate then initial";
        }
    },
    gtStart: function(stop, attr, state) {
        if (state.start !== undefined && stop !== undefined &&
            parseInt(state.start, 10) >= parseInt(stop, 10)) {
            return "should be greate then start";
        }
    }
});

var BaseModel = Backbone.Model.extend({
    initialize: function() {
        this.learningRateModel = new LearningRateModel();
        this.momentumModel = new MomentumModel();
        switch (this.get('model_name')) {
            case "MLP_RECTIFIED":
                this.set('layer_type', 'rectified_linear');
                break;
            case "MLP_SIGMOID":
                this.set('layer_type', 'sigmoid');
                break;
            case "MLP_MAXOUT":
                this.set('layer_type', 'maxout');
                break;
            case "MLP_MAXOUT_CONV":
                this.set('layer_type', 'maxout_convolution');
                break;
        }
        this.initLayers();
    },

    populate: function(params) {
        params = _.clone(params);
        this.learningRateModel.set(params.learning_rate);
        delete params.learning_rate;
        this.momentumModel.set(params.momentum);
        delete params.momentum;
        this.layers.reset(params.layers);
        this.layers.trigger('add'); //for react update
        delete params.layers;
        this.set(params);
    },

    getComponent: function() {
        return MLPModelComponent({model: this, withDropout: true});
    },

    getBackboneModels: function() {
        return [this, this.learningRateModel, this.momentumModel, this.layers];
    },

    initLayers: function(layers) {
        this.layers = new BaseLayersList(layers);
    },

    getDefaultLayer: function() {
        if (this.attributes.out_nonlin === 'LINEARGAUSSIAN') {
            return {type: this.get('layer_type'), dim: 200, irange: 0.005, switch_uniform_init: true, out_nonlin: 'LINEARGAUSSIAN'};
        } else {
            return {type: this.get('layer_type'), dim: 200, sparse_init: 10, irange: 0.005, switch_uniform_init: false};
        }
    },

    dumpParams: function() {
        var params = _.clone(this.attributes);
        delete params.model_name;
        delete params.layer_type;
        params.learning_rate = this.learningRateModel.dumpParams();
        params.momentum = this.momentumModel.dumpParams();
        params.layers = this.layers.dumpParams();
        return this.applyTypes(params);
    },

    isParamsValid: function() {
        return this.isValid(true) &&
               this.learningRateModel.isParamsValid() &&
               this.momentumModel.isParamsValid() &&
               this.layers.isParamsValid();
    },

    labels: {
        batch_size: 'size of batches',
        maxnum_iter: 'number of iterations',
        percent_batches_per_iter: 'number of batches to proccess per iteration'
    },

    validation: {
        'batch_size': {
            required: true,
            pattern: 'digits',
            range: [10, 10000]
        },
        'maxnum_iter': {
            required: true,
            pattern: 'digits',
            range: [1, 10000]
        },
        'percent_batches_per_iter': {
            required: true,
            pattern: 'digits',
            range: [0, 100]
        }
    }
});

var MaxoutModel = BaseModel.extend({
    initLayers: function(layers) {
        this.layers = new MaxoutLayersList(layers);
    },

    getComponent: function() {
        return MLPModelComponent({model: this, withDropout: false});
    },

    getDefaultLayer: function() {
        return {
            type: this.get('layer_type'),
            num_units: 240,
            num_pieces: 2,
            irange: 0.005,
            switch_uniform_init: true,
            max_col_norm: 1.9365,
            sparse_init: 10
        };
    }
});

var MaxoutConvModel = BaseModel.extend({
    initLayers: function(layers) {
        this.layers = new MaxoutConvLayersList(layers);
    },

    getComponent: function() {
        return MLPModelComponent({model: this, withDropout: false});
    },


    selectWeightInit: function(params) {
        return params;
    },

    getDefaultLayer: function() {
        return {
            type: this.get('layer_type'),
            num_units: 48,
            num_pieces: 2,
            irange: 0.005,
            pad: 0,
            kernel_shape: 8,
            pool_shape: 4,
            pool_stride: 2,
            max_kernel_norm: 1.9365,
        };
    }
});

module.exports = {
    Base: BaseModel,
    MaxoutConv: MaxoutConvModel,
    Maxout: MaxoutModel
};
