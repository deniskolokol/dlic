/* global Backbone */
/* global require */
/* global module */
/* global _ */
/* global socket */

"use strict";

var ParamsModels = require('./params/Models.js');


var Stat = Backbone.Model.extend({
    getTestAccuracy: function() {
        return (this.get('test_accuracy') * 100).toFixed(4);
    },
    getTrainAccuracy: function() {
        return (this.get('train_accuracy') * 100).toFixed(4);
    }
});

var AutoencoderStat = Backbone.Model.extend({
    getCost: function() {
        var outputs = this.get('train_outputs');
        return outputs[outputs.length - 1][1].toFixed(4);
    }
});

var TSNEStat = Backbone.Model.extend({
    getError: function() {
        var outputs = this.get('train_outputs');
        return parseFloat( outputs[outputs.length - 1]['error'] ).toFixed(4);
    },
    getGradNorm: function() {
        var outputs = this.get('train_outputs');
        return parseFloat( outputs[outputs.length - 1]['gradient'] ).toFixed(4);
    }
});

var MLPStatList = Backbone.Collection.extend({
    sync: Backbone.socketSync,
    model: Stat,
    comparator: 'iteration',
    getDataForCharts: function() {
        var stat = this.last(), outputs = stat.get('train_outputs'),
            headers = stat.get('outputs_header'), result = [], iter, mult;
        outputs.forEach(function(output) {
            iter = {};
            headers.forEach(function(header, i) {
                if (header === 'train_accuracy' || header === 'test_accuracy') {
                    mult = 100;
                } else {
                    mult = 1;
                }
                iter[header] = output[i] * mult;
            });
            result.push(iter);
        });
        return result;
    }
});

var MRNNStatList = Backbone.Collection.extend({
    sync: Backbone.socketSync,
    model: Stat,
    comparator: 'iteration',
    getDataForCharts: function() {
        var statsJson = this.toJSON(), stat;
        for (var i=0; i<statsJson.length; i++) {
            stat = statsJson[i];
            stat.train_accuracy *= 100;
            stat.test_accuracy *= 100;
            stat.train_last_10_steps_acc *= 100;
            stat.test_last_10_steps_acc *= 100;
        }
        return statsJson;
    }
});

var AutoencoderStatList = Backbone.Collection.extend({
    sync: Backbone.socketSync,
    model: AutoencoderStat,
    comparator: 'iteration',
    getDataForCharts: function() {
        return this.last().get('train_outputs').map(function(v) {
            return {iteration: v[0], train_cost: v[1]};
        });
    }
});

var TSNEStatList = Backbone.Collection.extend({
    sync: Backbone.socketSync,
    model: TSNEStat,
    comparator: 'iteration',
    getDataForCharts: function() {
        return this.last().get('train_outputs').map(function(v) {
            //return {iteration: v['iteration'], train_cost: v[1]};
            return v; //already a dictionary
        });
    }
});

var ConvStatList = Backbone.Collection.extend({
    sync: Backbone.socketSync,
    model: Stat,
    comparator: 'iteration',
    getDataForCharts: function() {
        var test_outputs = {}, output = {}, data = [];
        this.last().get('test_outputs').forEach(function(v) {
            test_outputs[v[2]] = [v[0], v[1]];
        });

        this.last().get('train_outputs').forEach(function(v, i) {
            output = {iteration: i + 1, train_loss: v[0], train_accuracy: v[1] * 100};
            if ( i in test_outputs ) {
                output.test_loss = test_outputs[i][0];
                output.test_accuracy = test_outputs[i][1] * 100;
            }
            data.push(output);
        });
        return data;
    }
});

var Model = Backbone.Model.extend({
    stateNames: {
        'NEW': 'New',
        'QUEUE': 'In queue',
        'TRAIN': 'Training',
        'FINISHED': 'Finished',
        'CANCELED': 'Stopped',
        'ERROR': 'Error'
    },

    initialize: function() {
        var model = this, StatList;
        switch (this.get('model_name')) {
            case 'AUTOENCODER':
                StatList = AutoencoderStatList;
                break;
            case 'TSNE':
                StatList = TSNEStatList;
                break;
            case 'MRNN':
                StatList = MRNNStatList;
                break;
            case 'CONV':
                StatList = ConvStatList;
                break;
            default:
                StatList = MLPStatList;
        }
        this.stats = new StatList();
        this.stats.url = function() {
            var url = '/api/model/' + model.id + '/stats/';
            if (model.stats.length && model.stats.last().id) {
                return url + '?stat_id__gt=' + model.stats.last().id;
            }
            return url;
        };
        this.paramModel = ParamsModels.getModel(this.get('model_name'), this.get('model_params'));

        // listen for state changes so we know when
        // to unsubscribe from logs subscription
        this.on('change:state', this.stateChanged);

        // if by default the status is QUEUE or TRAIN and not yet
        // subscribed to logs, subscribe immediately
        if ($.inArray(this.get('state'), ['QUEUE', 'TRAIN']) !== -1 && !this.isLogsSubscribed()) {
            this.trainingLogsSubscribe();
            this.logsSubscribe();
        }
    },

    params: function() {
        return this.get('model_params');
    },

    parse: function(attrs) {
        this.setModelParams();
        return attrs;
    },

    setModelParams: function() {
        if (this.paramModel !== undefined) {
            this.paramModel.populate(this.get('model_params'));
        }
    },

    statsResetAndFetch: function() {
        var model = this;
        this.trigger('init-stats');
        this.stats.reset();

        // this will just subscribe to incoming via websocket
        this.stats.fetch({remove: false});

        // to actually retrieve persisted stats, we fetch those manually
        $.get(this.stats.url(), function(data) {
            model.stats.set(data);
        });
    },

    applyModelSettings: function() {
        var model_params = this.paramModel.dumpParams(), model = this;
        $.ajax({
            url: '/api/model/' + this.id + '/',
            type: 'PATCH',
            data: JSON.stringify({model_params: model_params}, null, 2),
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            model.set(data);
            console.log('success');
        }).fail(function (xhr) {
            console.log('fail');
        });
    },

    rename: function(newName) {
        var model = this;
        $.ajax({
            url: '/api/model/' + this.id + '/',
            type: 'PATCH',
            data: JSON.stringify({name: newName}, null, 2),
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            model.set(data);
            console.log('success');
        }).fail(function (xhr) {
            console.log('fail');
        });
    },

    isProgressBarVisible: function() {
        var state = this.get('state');
        return (state === 'CANCELED' || state === 'TRAIN' || state === 'ERROR' || state === 'QUEUE');
    },

    allowResume: function() {
        var state = this.get('state'), maxItersNotReached;
        if (this.stats.length > 0) {
            maxItersNotReached = this.stats.last().get('iteration') < this.get('model_params').maxnum_iter;
        }
        return (this.stats.length > 0 && _.contains(['ERROR', 'CANCELED'], state)) || (maxItersNotReached && state === 'FINISHED');
    },

    allowRestart: function() {
        var state = this.get('state');
        return _.contains(['ERROR', 'CANCELED', 'FINISHED'], state);
    },

    allowStart: function() {
        var state = this.get('state');
        return state === 'NEW';
    },

    allowFinalize: function() {
        var state = this.get('state');
        return state === 'CANCELED' && this.stats.length > 0;
    },

    allowStop: function() {
        var state = this.get('state');
        return false;
        //return _.contains(['TRAIN', 'QUEUE'], state);
    },

    allowDelete: function() {
        var state = this.get('state');
        return _.contains(['CANCELED', 'ERROR', 'NEW', 'FINISHED'], state);
    },

    resume: function(iter) {
        var model = this;
        $.ajax({
            url: '/api/model/' + this.id + '/resume/',
            type: 'POST',
            data: JSON.stringify({iteration: iter}, null, 2),
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            model.statsResetAndFetch();
            model.set(data);
            console.log('success');
        }).fail(function (xhr) {
            console.log('fail');
        });
    },

    // called by ensemble's resume all
    miniResume: function() {
        var model = this;

        // you don't resume a finished model, you restart it
        if (model.get('state') === 'FINISHED') return;

        model.trainingLogsSubscribe(function() {
            model.statsResetAndFetch();
        });
    },

    restart: function() {
        var model = this;
        $.ajax({
            url: '/api/model/' + this.id + '/restart/',
            type: 'POST',
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            model.statsResetAndFetch();
            model.set(data);
            console.log('success');
        }).fail(function (xhr) {
            console.log('fail');
        });
    },

    finalize: function() {
        var model = this;
        $.ajax({
            url: '/api/model/' + this.id + '/finalize/',
            type: 'POST',
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            model.set(data);
            console.log('success');
        }).fail(function (xhr) {
            console.log('fail');
        });
    },

    hasConfusionMatrix: function() {
        return !_.contains(['CONV', 'AUTOENCODER', 'TSNE'], this.get('model_name'));
    },

    logsSubscriptionKey: function() {
        return 'models:logs:subscription';
    },

    isLogsSubscribed: function() {
        var subscriptions = JSON.parse($.cookie(this.logsSubscriptionKey()) || '[]');
        return (subscriptions.indexOf(this.get('id')) === -1) ?  false : true;
    },

    logsSubscribe: function() {
        var subscriptions = JSON.parse($.cookie(this.logsSubscriptionKey()) || '[]');
        if (subscriptions.indexOf(this.get('id')) !== -1) return;
        subscriptions.push(this.get('id'));
        $.cookie(this.logsSubscriptionKey(), JSON.stringify(subscriptions));
    },

    logsUnsubscribe: function() {
        var subscriptions = JSON.parse($.cookie(this.logsSubscriptionKey()) || '[]');
        var index = subscriptions.indexOf(this.get('id'));
        if (index === -1) return;
        subscriptions.splice(index, 1);
        $.cookie(this.logsSubscriptionKey(), JSON.stringify(subscriptions));
    },

    stateChanged: function(model, newState) {
        if ($.inArray(newState, ['FINISHED', 'CANCELED']) !== -1 && this.isLogsSubscribed()) {
            this.trainingLogsUnsubscribe();
            model.logsUnsubscribe();
        } else if (!this.isLogsSubscribed()) {
            this.trainingLogsSubscribe();
            model.logsSubscribe();
        }
    },

    trainingLogsSubscribe: function(callback) {
        console.log('subscribing to logs...');
        var model = this;

        // send subscribe request to this model's logs
        var payload = {
            modelId: this.get('id'),
            ensembleId: this.get('ensemble')
        };
        socket.send("model:logs:subscribe", payload, function(subscribed) {
            if (!subscribed) return;

            // once subscribed, listen for incoming logs
            socket.bind('model:' + model.get('id') + ':training:logs', model.logsAppender.bind(model));
            if (callback) callback();
        });
    },

    trainingLogsUnsubscribe: function() {
        console.log('unsubscribing to logs...');
        socket.unbind('models:' + this.get('id') + ':training:logs', this.logsAppender.bind(this));
    },

    logsAppender: function(data) {
        this.set('training_logs', (this.get('training_logs') || '') + data);
    }
});

var ModelList = Backbone.Collection.extend({
    model: Model,
    comparator: function(model) { return -model.id; },
    addModel: function(model) {
        var newModels = this.add(model, {merge: true});
        newModels.forEach(function(m) {
            m.setModelParams();
        });
    }
});

module.exports = ModelList;
