/* global require */
/* global React */
/* global Backbone */
/* global ensembleId */
/* global _ */

"use strict";
var PredictComponent = require('./PredictComponent.jsx'),
    Ensemble = require('./Ensemble.js'),
    isEnsembleLoaded = false,
    isModelsLoaded = false,
    isDOMLoaded = false,
    ensemble;


var Predict = Backbone.Model.extend({
    url: function() {
        return '/api/predict/' + this.id + '/';
    },

    beforeDeleteRequest: function() {
        this.set('delete-request', 'before');
    },

    deleteRequestDone: function() {
        this.set('delete-request', 'done');
    },

    deleteRequestFail: function() {
        this.set('delete-request', 'fail');
    }
});

var PredictList = Backbone.Collection.extend({
    model: Predict,
    comparator: function(model) { return -model.id; }
});

var ExtEnsemble = Ensemble.extend({
    initialize: function() {
        Ensemble.prototype.initialize.apply(this);
        this.predicts = new PredictList();
        this.predicts.url = '/api/predict/?ensemble=' + this.id;
        this.predicts.ensemble = this;
        this.set('fileSet', []);
    },

    getDatasetsPredicts: function() {
        return this.predicts.filter(function(predict) {
            return predict.get('dataset');
        });
    },

    getInputDataPredicts: function() {
        return this.predicts.filter(function(predict) {
            return !predict.get('dataset');
        });
    },

    getIterationsForPredict: function() {
        return this.models.filter(function(model) {
            return model.get('isSelected');
        }).map(function(model) {
            var stat = model.get('selectedIter') || model.stats.last();
            return stat.id;
        });
    },

    loadPreviousPredictions: function() {
        var ensemble = this;
        if (!ensemble.get('previousDatasetsIsLoaded')) {
            this.predicts.fetch({'success': function() {
                ensemble.set('previousDatasetsIsLoaded', true);
            }});
        }
    }
});


ensemble = new ExtEnsemble({id: ensembleId});

function updateLoaded() {
    if (isDOMLoaded) {
        React.renderComponent(PredictComponent({ensemble: ensemble, loaded: isEnsembleLoaded && isModelsLoaded}),
                              document.getElementById('predict'));
    }
}

ensemble.fetch({
    'success': function() {
        isEnsembleLoaded = true;
        updateLoaded();
    }
});

ensemble.models.fetch({
    'success': function() {
        var isSelected = true;
        ensemble.models.forEach(function(model) {
            model.set('isSelected', isSelected);
            if (ensemble.get('data_type') === 'IMAGES') {
                isSelected = false;
            }
            model.statsResetAndFetch();
        });
        isModelsLoaded = true;
        updateLoaded();
        ensemble.loadPossibleDatasets({equal_input: true});
    }
});

$(function() {
    isDOMLoaded = true;
    updateLoaded();
    setInterval(function() {
        ensemble.predicts.forEach(function(predict) {
            if (_.contains(['PREDICT', 'QUEUE'], predict.get('state'))) {
                predict.fetch();
            }
        });
    }, 10000);
});
