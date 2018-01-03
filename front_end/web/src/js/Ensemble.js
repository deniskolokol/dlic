/* global _ */
/* global Backbone */
/* global require */
/* global module */

"use strict";


var Utils = require('./Utils');
var Alerts = require('./alerts');
var Api = require('./api');
var ModelList = require('./Model');
var ParamsModels = require('./params/Models');
_.extend(Backbone.Model.prototype, Backbone.Validation.mixin);
Backbone.Validation.configure( {labelFormatter: 'label'} );

var Ensemble = Backbone.Model.extend({
    initialize: function() {
        this.models = new ModelList();
        this.models.url = '/api/model/?ensemble=' + this.id;
        this.models.ensemble = this;
    },

    url: function() { return '/api/ensemble/' + this.id + '/'; },

    parse: function(response) {
        this.models.fetch();
        return response;
    },

    modelNames: {
        'MRNN': 'MRNN',
        'CONV': 'Convolutional net',
        'MLP_SIGMOID': 'Deep Neural net. Sigmoid Units',
        'MLP_RECTIFIED': 'Deep Neural net. Linear Rectified Units',
        'MLP_MAXOUT': 'Deep Neural net. Maxout Units',
        'MLP_MAXOUT_CONV': 'Deep Neural net. Maxout Convolution Units',
        'AUTOENCODER': 'Autoencoder',
        'TSNE': 'T-Distributed Stochastic Neighbor Embedding'
    },

    generalModelNames: ['TSNE', 'AUTOENCODER', 'MLP_SIGMOID', 'MLP_RECTIFIED',
                        'MLP_MAXOUT', 'MLP_MAXOUT_CONV'],

    modelsWithPredict: ['MRNN', 'CONV', 'MLP_SIGMOID', 'MLP_RECTIFIED',
                        'MLP_MAXOUT', 'MLP_MAXOUT_CONV'],

    loadPossibleDatasets: function(options) {
        var self = this, url;
        if (options && options.equal_input) {
            url = '/api/dataset/?for_ensemble=' + self.id + '&equal_input=1';
        } else {
            url = '/api/dataset/?for_ensemble=' + self.id;
        }
        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function (data) {
            self.set('possibleDatasets', data);
            self.set('possibleDatasetsLoaded', true);
        }).fail(function (xhr) {
            self.set('possibleDatasetsLoaded', false);
        });
    },

    allowApplySettings: function() {
        var shared = this.get('shared'),
            state = this.get('state'),
            allowedStates = ['new', 'empty', 'stopped', 'error', 'finished'];
        return (!shared && ($.inArray(state, allowedStates) !== -1));
    },

    allowPredict: function() {
        var state = this.get('state'), modelName;
        if (!this.validateDatasets()) {
            return false;
        }
        if (state === 'finished' && this.models.length) {
            modelName = this.models.at(0).get('model_name');
            return (_.indexOf(this.modelsWithPredict, modelName) !== -1);
        }
        return false;
    },

    allowShare: function() {
        var shared = this.get('shared'), state = this.get('state');
        return (state === 'finished' && !shared && this.get('userAdmin')) && this.validateDatasets();
    },

    allowStop: function() {
        var state = this.get('state');
        return (state === 'in queue' || state === 'training');
    },

    allowStartResume: function() {
        var state = this.get('state');
        return (state === 'stopped' || state === 'error' || state === 'new') && this.validateDatasets();
    },

    allowAddNewModel: function() {
        return !this.allowStop() && !this.get('shared') && this.validateDatasets();
    },

    resume: function() {
        var ensemble = this;
        $.ajax({
            url: '/api/ensemble/' + ensemble.id + '/resume/',
            type: 'POST',
            dataType: 'json',
            contentType: 'application/json'
        }).done(function() {
            Alerts.ensembleResumed(ensemble, {id: ensemble.id});
            ensemble.fetch();
            for (var i=0; i<ensemble.models.length; i++) {
                ensemble.models.at(i).miniResume();
            }
        }).error(Alerts.getXhrErrorParser(ensemble));
    },

    stop: function() {
        var ensemble = this;
        $.ajax({
            url: '/api/ensemble/' + ensemble.id + '/stop/',
            type: 'POST',
            dataType: 'json',
            contentType: 'application/json'
        }).done(function() {
            Alerts.ensembleStopped(ensemble, {id: ensemble.id});
            ensemble.fetch();
        }).error(Alerts.getXhrErrorParser(ensemble));
    },

    share: function() {
        if (!window.confirm("Share this ensemble?\nYou will not be able to change this ensemble or unshare it.\nAll datasets associated with this ensemble will be also shared.")) {
            return;
        }
        var ensemble = this;
        $.ajax({
            url: '/api/ensemble/' + ensemble.id + '/share/',
            type: 'POST',
            dataType: 'json',
            contentType: 'application/json'
        }).done(function() {
            Alerts.ensembleShared(ensemble);
            ensemble.fetch();
        }).error(Alerts.getXhrErrorParser(ensemble));
    },

    goToPredict: function() {
        window.location = this.get('runEnsembleURL');
    },

    applySettings: function() {
        var ensemble = this, data, done, error;
        data = {
            train_dataset: ensemble.get('train_dataset'),
            test_dataset: ensemble.get('test_dataset'),
            send_email_on_change: this.get('send_email_on_change')
        };
        $.ajax({
            url: '/api/ensemble/' + ensemble.id + '/',
            type: 'PUT',
            data: JSON.stringify(data, null, 2),
            dataType: 'json',
            contentType: 'application/json'
        }).done(function() {
            //ensemble.fetch();
            //Alerts.ensembleSettingsSaved(ensemble);
            //TODO replace with trigger
            //model.set('isChanged', false);
        }).error(function() {
            //error = Alerts.getXhrErrorParser(model);
            //Api.post.ensembleSettings(data, done, error);
        });
    },


    getNewModelName: function() {
        var dataType = this.get('data_type');
        if (dataType === 'TIMESERIES') {
            return 'MRNN';
        } else if (dataType === 'IMAGES') {
            return 'CONV';
        } else if (this.models.length) {
            return this.models.at(0).get('model_name');
        } else {
            return _.pairs(_.pick(this.modelNames, this.generalModelNames));
        }
    },

    addOneMoreModel: function(name) {
        var model = ParamsModels.getModel(name), ensemble = this, data;
        data = {ensemble: ensemble.id, model_name: name, model_params: model.dumpParams()};
        $.ajax({
            url: '/api/model/',
            data: JSON.stringify(data, null, 2),
            type: 'POST',
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            ensemble.models.addModel(data);
            Alerts.oneMoreModelAdded(model);
        }).fail(function (xhr) {
            Alerts.getXhrErrorParser(model)();
        });
    },

    toggleSendEmail: function(value) {
        this.set('send_email_on_change', value);
    },

    getFinishedJobs: function() {
        return this.models.where({state: 'FINISHED'}).length + '/' + this.models.length;
    },

    getTrainingTime: function() {
        var time = this.models.pluck('training_time');
        time.push(0);
        return Utils.sum(time);
    },

    isTestless: function() {
        //var model_name = this.models.at(0).get('model_name');
        return this.models.length > 0 && (this.models.at(0).get('model_name') === 'AUTOENCODER' || this.models.at(0).get('model_name') === 'TSNE');
    },

    validateDatasets: function() {
        if (this.isTestless() && this.get('train_dataset')) {
            return true;
        } else if (this.get('train_dataset'), this.get('test_dataset')) {
            return true;
        } else {
            return false;
        }
    },

    deleteModel: function(model) {
        var ensemble = this;
        $.ajax({
            url: '/api/model/' + model.id + '/',
            type: 'DELETE',
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            ensemble.models.remove(model);
        }).fail(function (xhr) {
            console.log('fail');
        });
    },

    onWorker: function() {
        return _.contains(['in queue', 'training'], this.get('state'));
    }

});

module.exports = Ensemble;
