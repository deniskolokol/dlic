/* global Backbone */

"use strict";

var ParamsModels = require('./params/Models.js');

var Wizard = Backbone.Model.extend({
    steps: {
        'model-select': 1,
        'model-setup': 2,
        'model-params': 3
    },

    setInitValues: function(df, dfs) {
        this.reset();
        this.set({currentStep: 'model-select', dataFile: df});
        this.dfs = dfs;
        this.trigger('change');
    },

    reset: function() {
        var id = this.id;
        this.clear();
        this.set({id: id});
        this.dfs = undefined;
    },

    selectModel: function(model) {
        this.set({currentModel: model, currentStep: 'model-setup'});
        this.router.navigate('ensemble-wizard/' + this.get('dataFile').id + '/step/model-setup/', {trigger: true});
    },

    selectModelSetup: function() {
        var name = this.getModelName(),
            model = ParamsModels.getModel(name);
        if (this.get('currentOutputNonlin') == 'LINEARGAUSSIAN') {
            model.attributes.out_nonlin = 'LINEARGAUSSIAN';
            for (var i=0; i<model.layers.length; i++) {
                model.layers.models[i].switch_uniform_init = true;
                model.layers.models[i].out_nonlin = 'LINEARGAUSSIAN';
            }
        }
        this.set('model', model);
        this.set({currentStep: 'model-params'});
        this.router.navigate('ensemble-wizard/' + this.get('dataFile').id + '/step/model-params/', {trigger: true});
    },

    finish: function(options) {
        var trainDatasetId = this.get('currentTrainDataset') || null,
            testDatasetId = this.get('currentTestDataset') || null,
            self = this;
        $.ajax({
            url: '/api/ensemble/',
            data: JSON.stringify({train_dataset: trainDatasetId, 
                                  test_dataset: testDatasetId,
                                  net_type: this.getModelName()}, null, 2),
            type: 'POST',
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            self.createModel(data.id, options);
        }).fail(function (xhr) {
            //debugger;
        });
    },

    getModelName: function() {
        var name = this.get('currentModel'), nonlin = this.get('currentNonlin');
        if (name === "DEEPNET") {
            return nonlin;
        }
        return name;
    },

    createModel: function(ensembleId, options) {
        var model = this.get('model'), outputNonlin = this.get('currentOutputNonlin'); 
        var name = this.getModelName(), self = this,
            model_params = model.dumpParams();
        if (outputNonlin === 'LINEARGAUSSIAN') {
            for (var i=0; i<model_params.layers.length; i++)
                delete model_params.layers[i].out_nonlin;
        }
        var data = {ensemble: ensembleId, model_params: model_params, model_name: name,
                    out_nonlin: outputNonlin};
        //debugger;
        $.ajax({
            url: '/api/model/',
            data: JSON.stringify(data, null, 2),
            type: 'POST',
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            self.set({currentStep: 'finished'}); //for change trigger
            if (options && options.start) {
                $.ajax({
                    url: '/api/ensemble/' + ensembleId + '/resume/',
                    type: 'POST',
                    dataType: 'json',
                    contentType: 'application/json'
                }).always(function (data) {
                    window.location.href = '/train-ensemble/' + ensembleId + '/';
                });
            } else {
                window.location.href = '/train-ensemble/' + ensembleId + '/';
            }
        }).fail(function (xhr) {
            //debugger;
        });
    }
});

module.exports = Wizard;
