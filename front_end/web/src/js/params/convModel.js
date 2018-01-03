/* global Backbone */
/* global _ */

"use strict";


var ConvModelComponent = require('./cudaConvComponents2.jsx'),
    Utils = require('../Utils.js');

_.extend(Backbone.Model.prototype, Backbone.Validation.mixin, Utils.ApplyTypesMixin);
Backbone.Validation.configure({labelFormatter: 'label'});


var ConvSetLayer = Backbone.Model.extend({
    dumpParams: function() {
        var params = _.clone(this.attributes);
        return this.applyTypes(params);
    },

    isParamsValid: function() {
        var params = _.clone(this.attributes);
        this.validate();
        return this.isValid(_.keys(params));
    },
    labels: {
        convChannels: "number of channels",
        convFilters: "number of filters",
        convFilterSize: "filter size",
        convSharedBiases: "shared biases",
        convDropout: "dropout",
        poolStart: "start",
        poolSizeX: "sizeX",
        poolStride: "stride",
        poolOutputsX: "outputsX",
        normSize: "size",
        },

    validation: {
        'convChannels': {
            required: true,
            pattern: 'digits',
            fn: 'validateChannels'
            },
        'convFilters': {
            required: true,
            pattern: 'digits',
            fn: 'validateFilters'
            },
        'convFilterSize': {
            required: true,
            pattern: 'digits',
            },
        'convSharedBiases': {
            required: true,
            pattern: 'digits',
            },
        'convDropout': {
            required: true,
            pattern: 'number',
            range: [0,1]
            },
        'poolStart': {
            required: true,
            pattern: 'number',
            min: 0
            },
        'poolSizeX': {
            required: true,
            pattern: 'number',
            min: 0
            },
        'poolStride': {
            required: true,
            pattern: 'number',
            min: 0
            },
        'poolOutputsX': {
            required: true,
            pattern: 'number',
            min: 0
            },
        'normSize': {
            required: true,
            pattern: 'number',
            min: 0
            }
        },

    validateChannels: function(value, attr, computedState) {
        value = parseInt(value);
        if (value < 4) {
            if ( (value !== 1) && (value !== 2) && (value !== 3) ) {
                return "ConvLayer channels value is invalid.";
            }
        } else {
            if (value % 4) {
                return "ConvLayer channels value is invalid. Channel value greater than 3 must be divisible by 4.";
            }
        }
    },

    validateFilters: function(value, attr, computedState) {
        value = parseInt(value);
        if ( !( (value >= 16) && (value % 16 === 0) ) ) {
            return "ConvLayer filters value is invalid. Must be divisible by 16.";
        }
    }
});

var FCLayer = Backbone.Model.extend({
    dumpParams: function() {
        var params = _.clone(this.attributes);
        return this.applyTypes(params);
    },

    isParamsValid: function() {
        var params = _.clone(this.attributes);
        this.validate();
        return this.isValid(_.keys(params));
    },

    labels: {
        'outputs': 'outputs'
        },

    validation: {
        'outputs': {
            required: true,
            pattern: 'number',
            min: 0
            }
        }
});

var LayersList = Backbone.Collection.extend({
    isParamsValid: function() {
        if (this.length > 0) {
            return this.reduce(function(prev, cur) {
                return prev && cur.isParamsValid();
            }, true);
        }
    },

    dumpParams: function() {
        var params;
        return this.map(function(layer, i) {
            params = layer.dumpParams();
            params.layer_name = 'h' + i;
            return params;
        });
    },

    getDefaultConvSetLayer: function() {
        return {type: 'convSet',
                convChannels: 32,
                convFilters: 32,
                convPadding: 2,
                convStride: 1,
                convFilterSize: 5,
                convSharedBiases: 1,
                convDropout: 0.5,
                poolStart: 0,
                poolSizeX: 3,
                poolStride: 2,
                poolOutputsX: 0,
                normSize: 10
                };
        },

    getDefaultFCLayer: function() {
        return {type: 'fc', outputs: 10};
        },

    model: function(attrs,options) {
        // this model attribute of a Backbone Collection specifies which model gets
        // added to the collection. Instead of naming a single model, we put a function
        // here that will return a different model based on the `type` in the input attrs.
        // Refs:
        // http://stackoverflow.com/questions/7147040/how-to-create-a-collection-with-several-model-types-in-backbone-js
        switch(attrs.type) {
            case "convSet":
                return new ConvSetLayer(attrs,options);
            case "fc":
                return new FCLayer(attrs,options);
            }
        },
});

var ConvModel = Backbone.Model.extend({
    initialize: function() {
        this.initLayers();
    },

    getBackboneModels: function() {
        return [this, this.layers];
    },

    initLayers: function(layers) {
        this.layers = new LayersList(layers);
    },

    createModels: function(layers) {
        return layers.map(function(layer) {
            if (layer.type === 'convSet') {
                return new ConvSetLayer(layer);
            }
            return new FCLayer(layer);
        });
    },

    getComponent: function() {
        return ConvModelComponent({model: this});
    },

    dumpParams: function() {
        var params = _.clone(this.attributes);
        delete params.model_name;
        params.layers = this.layers.dumpParams();
        this.applyTypes(params);
        params.learning_rate = {init: params.learning_rate_init};
        params.momentum = {init: params.momentum_init};
        delete params.learning_rate_init;
        delete params.momentum_init;
        return params;
    },

    isParamsValid: function() {
        return this.isValid(true) && this.layers.isParamsValid();
    },

    populate: function(params) {
        params = _.clone(params);
        this.layers.reset(this.createModels(params.layers));
        this.layers.trigger('add'); //for react update
        delete params.layers;
        this.set(params);
    },

    labels: {
        maxnum_iter: "number of iterations",
        img_size: "image size",
        learning_rate_init: "learning rate",
        momentum_init: "momentum",
        rand_sparse: 'Random sparse'
    },

    validation: {
        'maxnum_iter': {
            required: true,
            pattern: 'digits',
            range: [1, 10000]
        },
        'img_size': {
            required: true,
            pattern: 'digits',
            range: [8, 128],
            fn: 'divByEight'
        },
        'learning_rate_init': {
            required: false,
            pattern: 'number',
            range: [1e-10, 1]
        },
        'dropout': {
            required: false,
            pattern: 'number',
            range: [0, 1]
        },
        'momentum_init': {
            required: false,
            pattern: 'number',
            range: [1e-10, 1]
        }
    },

    divByEight: function(img_size, attr, state) {
        if (img_size % 8 !== 0) {
            return "must be a multiple of 8";
        }
    }
});

module.exports = ConvModel;
