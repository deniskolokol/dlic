/* global Backbone */
/* global _ */

"use strict";


var ParamsComponents = require('./Components.jsx'),
    TSNEComponent = ParamsComponents.TSNE,
    AutoencoderComponent = ParamsComponents.Autoencoder,
    CONVComponent = ParamsComponents.CONV,
    MRNNComponent = ParamsComponents.MRNN,
    MLPModels = require('./mlpModels.js'),
    Utils = require('../Utils.js'),
    ConvModel = require('./convModel.js');


_.extend(Backbone.Model.prototype, Backbone.Validation.mixin, Utils.ApplyTypesMixin);
Backbone.Validation.configure({labelFormatter: 'label'});

var BaseModel = Backbone.Model.extend({
    getBackboneModels: function() {
        return [this];
    },

    populate: function(params) {
        this.set(params);
    },

    dumpParams: function() {
        return this.applyTypes(this.attributes);
    },

    isParamsValid: function() {
        return this.isValid(true);
    }
});

var AutoencoderModel = BaseModel.extend({
    getComponent: function() {
        return AutoencoderComponent({model: this});
    },

    labels: {
        maxnum_iter: "number of iterations",
        batch_size: "size of batches",
        hidden_outputs: "size of hidden layer",
        noise_level: "noise level",
        learning_rate_init: "learning rate",
        irange: "range of uniform initialization"
    },

    dumpParams: function() {
        var params = _.clone(this.attributes);
        params = this.applyTypes(params);
        params.learning_rate = {init: params.learning_rate_init};
        delete params.learning_rate_init;
        return params;
    },

    populate: function(params) {
        params = _.clone(params);
        try {
            params.learning_rate_init = params.learning_rate.init;
            delete params.learning_rate;
        } catch(e) {
        }
        this.set(params);
    },

    validation: {
        'batch_size': {
            required: true,
            pattern: 'digits',
            range: [1, 10000]
        },
        'maxnum_iter': {
            required: true,
            pattern: 'digits',
            range: [1, 1000]
        },
        'hidden_outputs': {
            required: false,
            pattern: 'digits',
            range: [1, 1000]
        },
        'noise_level': {
            required: false,
            pattern: 'number',
            range: [1e-10, 1]
        },
        'learning_rate_init': {
            required: false,
            pattern: 'number',
            range: [1e-10, 1]
        },
        'irange': {
            required: false,
            pattern: 'number',
            range: [1e-10, 1]
        }
    }
});

var TSNEModel = BaseModel.extend({
    getComponent: function() {
        return TSNEComponent({model: this});
    },

    labels: {
        n_components: "target dimensionality",
        maxnum_iter: "numer of iterations",
        perplexity: "perplexity",
        early_exaggeration: "early exaggeration",
        learning_rate: "learning rate",
        init: "initialization"
    },

    dumpParams: function() {
        var params = _.clone(this.attributes);
        params = this.applyTypes(params);
        delete params.tsne_output;
        return params;
    },

    populate: function(params) {
        params = _.clone(params);
        this.set(params);
    },

    validation: {
        'n_components': {
            required: false,
            pattern: 'digits',
            range: [2,3]
        },
        'maxnum_iter': {
            required: false,
            pattern: 'digits',
            range: [200,10000]
        },
        'perplexity': {
            required: false,
            pattern: 'number',
            range: [1,100]
        },
        'early_exaggeration': {
            required: false,
            pattern: 'number',
            range: [1,100]
        },
        'learning_rate': {
            required: false,
            pattern: 'number',
            range: [100,1000]
        }
    }
    /*  Not bothering to validate init at this time. It's either 'random' or 'pca'
     *  and users set it through a dropdown selector.
     */
});

//var ConvModel = BaseModel.extend({
    //getComponent: function() {
        //return CONVComponent({model: this});
    //},

    //dumpParams: function() {
        //var params = _.clone(this.attributes);
        //params = this.applyTypes(params);
        //params.learning_rate = {init: params.learning_rate_init};
        //params.momentum = {init: params.momentum_init};
        //delete params.learning_rate_init;
        //delete params.momentum_init;
        //return params;
    //},

    //populate: function(params) {
        //params = _.clone(params);
        //try {
            //params.learning_rate_init = params.learning_rate.init;
            //delete params.learning_rate;
        //} catch(e) { }
        //try {
            //params.momentum_init = params.momentum.init;
            //delete params.momentum;
        //} catch(e) { }
        //this.set(params);
    //},


    //labels: {
        //maxnum_iter: "number of iterations",
        //img_size: "image size",
        //learning_rate_init: "learning rate",
        //momentum_init: "momentum",
        //rand_sparse: 'Random sparse'
    //},

    //validation: {
        //'maxnum_iter': {
            //required: true,
            //pattern: 'digits',
            //range: [1, 10000]
        //},
        //'img_size': {
            //required: true,
            //pattern: 'digits',
            //range: [8, 128],
            //fn: 'divByEight'
        //},
        //'learning_rate_init': {
            //required: false,
            //pattern: 'number',
            //range: [1e-10, 1]
        //},
        //'dropout': {
            //required: false,
            //pattern: 'number',
            //range: [0, 1]
        //},
        //'momentum_init': {
            //required: false,
            //pattern: 'number',
            //range: [1e-10, 1]
        //}
    //},

    //divByEight: function(img_size, attr, state) {
        //if (img_size % 8 !== 0) {
            //return "must be a multiple of 8";
        //}
    //}
//});

var MRNNModel = BaseModel.extend({
    getComponent: function() {
        return MRNNComponent({model: this});
    },

    labels: {
        maxnum_iter: "number of iterations",
        h: "number of hidden units",
        f: "number of factored units",
        cg_min_cg: "minimum number of conjugate gradient iterations",
        cg_max_cg: "maximum number of conjugate gradient iterations",
        lambda: "damping parameter lambda",
        mu: "damping parameter mu"
    },

    validation: {
        'maxnum_iter': {
            required: true,
            pattern: 'digits',
            range: [1, 1000]
        },
        'h': {
            required: false,
            pattern: 'digits',
            range: [1, 1000]
        },
        'f': {
            required: false,
            pattern: 'digits',
            range: [1, 1000]
        },
        'cg_min_cg': {
            required: false,
            pattern: 'digits',
            range: [1, 1000],
            fn: 'ltMaxCg'
        },
        'cg_max_cg': {
            required: false,
            pattern: 'digits',
            range: [1, 1000],
            fn: 'gtMinCg'
        },
        'lambda': {
            required: false,
            pattern: 'number',
            range: [1e-6, 1]
        },
        'mu': {
            required: false,
            pattern: 'number',
            range: [1e-6, 1]
        }
    },

    gtMinCg: function(cgMaxCg, attr, state) {
        if (state.cg_min_cg !== undefined && cgMaxCg !== undefined &&
            parseFloat(state.cg_min_cg) > parseFloat(cgMaxCg)) {
            return "maximum # of CG iterations should be greater than minimum";
        }
    },

    ltMaxCg: function(cgMinCg, attr, state) {
        if (state.cg_min_cg !== undefined && cgMinCg !== undefined &&
            parseFloat(state.cg_max_cg) < parseFloat(cgMinCg)) {
            return "minimum # of CG iterations should be lower than maximum";
        }
    }
});

var defaultModelParams = {
    TSNE: {
        n_components: 2, maxnum_iter: 1000, perplexity: 30,
        early_exaggeration: 4.0, learning_rate: 1000, init: 'random'
    },
    AUTOENCODER: {batch_size: 128, maxnum_iter: 100},
    CONV: {
        maxnum_iter: 100, img_size: 32, random_sparse: false,
        dropout: 0.5, learning_rate_init: 0.01, momentum_init: 0.9,
        layers: [
            {type: 'convSet',
            convChannels: 3,
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
            normSize: 3},
            {type: 'convSet',
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
            normSize: 3},
            {type: 'convSet',
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
            normSize: 10},
            {type: 'fc', outputs: 3}
        ]
    },
    MRNN: {maxnum_iter: 20},
    MLP_RECTIFIED: {
        batch_size: 128, maxnum_iter: 100,
        percent_batches_per_iter: 100, dropout: true,
        layers: [
            {type: 'rectified_linear', dim: 200, sparse_init: 10, irange: 0.005, switch_uniform_init: false},
            {type: 'rectified_linear', dim: 200, sparse_init: 10, irange: 0.005, switch_uniform_init: false}
        ]
    },
    MLP_SIGMOID: {
        batch_size: 128, maxnum_iter: 100,
        percent_batches_per_iter: 100, dropout: true,
        layers: [
            {type: 'sigmoid', dim: 200, sparse_init: 10, irange: 0.005, switch_uniform_init: false},
            {type: 'sigmoid', dim: 200, sparse_init: 10, irange: 0.005, switch_uniform_init: false}
        ]
    },
    MLP_MAXOUT: {
        batch_size: 128, maxnum_iter: 100,
        percent_batches_per_iter: 100,
        layers: [
            {
                type: 'maxout',
                num_units: 240,
                num_pieces: 2,
                irange: 0.005,
                switch_uniform_init: true,
                max_col_norm: 1.9365,
                sparse_init: 10
            }, {
                type: 'maxout',
                num_units: 240,
                num_pieces: 2,
                irange: 0.005,
                switch_uniform_init: true,
                max_col_norm: 1.9365,
                sparse_init: 10
            }, {
                type: 'maxout',
                num_units: 240,
                num_pieces: 2,
                irange: 0.005,
                switch_uniform_init: true,
                max_col_norm: 1.9365,
                sparse_init: 10
            }
        ]
    },
    MLP_MAXOUT_CONV: {
        batch_size: 128, maxnum_iter: 100,
        percent_batches_per_iter: 100,
        layers: [
            {
                type: 'maxout_convolution', num_units: 48, num_pieces: 2,
                irange: 0.005, pad: 0, kernel_shape: 8,
                pool_shape: 4, pool_stride: 2, max_kernel_norm: 0.9
            }, {
                type: 'maxout_convolution', num_units: 48, num_pieces: 2,
                irange: 0.005, pad: 3, kernel_shape: 8,
                pool_shape: 4, pool_stride: 2, max_kernel_norm: 1.9365
            }, {
                type: 'maxout_convolution', num_units: 24, num_pieces: 4,
                irange: 0.005, pad: 3, kernel_shape: 5,
                pool_shape: 2, pool_stride: 2, max_kernel_norm: 1.9365
            }
        ]
    }
};

function getModel(name, params) {
    var model;
    switch(name) {
        case "TSNE":
            model = new TSNEModel();
            break;
        case "AUTOENCODER":
            model = new AutoencoderModel();
            break;
        case "CONV":
            model = new ConvModel();
            break;
        case "MRNN":
            model = new MRNNModel();
            break;
        case "MLP_RECTIFIED":
            model = new MLPModels.Base({model_name: name});
            break;
        case "MLP_SIGMOID":
            model = new MLPModels.Base({model_name: name});
            break;
        case "MLP_MAXOUT":
            model = new MLPModels.Maxout({model_name: name});
            break;
        case "MLP_MAXOUT_CONV":
            model = new MLPModels.MaxoutConv({model_name: name});
            break;
        default:
            console.log('Error, invalid model name: ' + name);
    }
    if (params) {
        model.populate(params);
    } else {
        model.populate(defaultModelParams[name]);
    }
    return model;
}


module.exports = {
    getModel: getModel
};
