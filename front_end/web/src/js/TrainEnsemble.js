/* global require */
/* global React */
/* global ensembleId */
/* global runEnsembleURL */
/* global userAdmin */
/* global Backbone */


"use strict";

var Ensemble = require('./Ensemble');
var EnsembleComponent = require('./TrainEnsembleComponents.jsx');

$(function() {
    var ensemble = new Ensemble({
        id: ensembleId,
        userAdmin: userAdmin,
        runEnsembleURL: runEnsembleURL
    });

    //TODO mv this functionality to the ensemble react component?
    var AppView = Backbone.View.extend({
        initialize: function() {
            this.listenTo(ensemble.models, 'add', this.addOne);
            this.listenToOnce(ensemble, 'sync', this.renderEnsemble);
            this.listenTo(ensemble.models, 'add remove', this.updateEnsemble);
            this.listenTo(ensemble.models, 'change:state', this.updateEnsemble);
            this.listenTo(ensemble.models, 'change:model_params', this.modelUpdateParams);
        },

        addOne: function(model) {
            model.statsResetAndFetch();
        },

        renderEnsemble: function() {
            React.renderComponent(EnsembleComponent({ensemble: ensemble}),
                                  document.getElementById('ensemble-view')
            );
        },

        updateEnsemble: function() {
            ensemble.fetch();
        },

        modelUpdateParams: function(model) {
            model.setModelParams();
        }
    });

    new AppView();
    ensemble.fetch();

    // before fetching the models,
    // clear logs subscriptions cookie
    $.removeCookie('models:logs:subscription');

    ensemble.models.fetch({
        remove: false,
        success: function(collection, response, options) {
            // filter models that aren't training,
            // since training models will get their stats pushed
            var models = collection.filter(function(model) {
                return (model.state !== 'TRAIN') ? true : false;
            });

            // then retrieve each model's stats so the graphs will render
            models.forEach(function(model) {
                $.get(model.stats.url(), function(data) {
                    model.stats.set(data);
                });
            });
        }
    });

    // since we can move between different
    // models on an ensemble, its expensive to poll
    // each model individually, so we poll the parent
    // ensemble instead.
    setInterval(function() {
        ensemble.models.fetch({remove: false});
    }, 15000);
});
