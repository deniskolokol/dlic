/* global require */
/* global React */
/* global Backbone */
/* global SockJS */
/* global wsUrl */
/* global wsToken */
/* global wsSalt */
/* global Humanize */

"use strict";

var DMComponent = require('./DMComponent.jsx');
var DatasetWizard = require('./DatasetWizard.js');
var EnsembleWizard = require('./EnsembleWizard.js');
var Utils = require('./Utils.js');

var ParseLogs = Backbone.Collection.extend({
    comparator: 'timestamp',
});

var DataFile = Backbone.Model.extend({
    constructor: function() {
        this.parseLogs = new ParseLogs();
        Backbone.Model.apply(this, arguments);
    },

    parse: function(response) {
        response.created = new Date(response.created);
        this.parseLogs.add(response.parse_logs, {merge: true});
        delete response.parse_logs;
        return response;
    },

    share: function() {
        if (!window.confirm("Share this datafile?\nYou will not be able to change this datafile or unshare it.\nAll datasets associated with this datafile will be also shared.")) {
            return;
        }
        var df = this;
        $.ajax({
            url: '/api/data/' + df.id + '/share/',
            type: 'POST',
            dataType: 'json',
            contentType: 'application/json'
        }).done(function() {
            df.fetch();
        }).fail(function (xhr) {
            console.log('fail');
        });
    },

    isTimeseriesWithoutOutput: function() {
        return (this.get('file_format') === 'TIMESERIES' && this.get('meta').output_size === 0);
    },

    needReparse: function() {
        return this.get('state') == 'Action required';
    },

    beforeDeleteRequest: function() {
        this.set('delete-request', 'before');
    },

    deleteRequestDone: function() {
        this.set('delete-request', 'done');
    },

    deleteRequestFail: function() {
        this.set('delete-request', 'fail');
    },

    renameRequestDone: function() {
        this.set('rename-request', 'done');
    },

    renameRequestFail: function() {
        this.set('rename-request', 'fail');
    }
});


var DataFileList = Backbone.Collection.extend({
    model: DataFile,

    url: function() {
        return '/api/data/';
    }
});


function connect(url, auth_json, dfs) {
    var sock = new SockJS(url);
    sock.onopen = function() {
        sock.send(JSON.stringify(auth_json));
    };

    sock.onmessage = function(e) {
        var data = JSON.parse(e.data), df;
        switch (data.type) {
            case 'parse_log':
                df = dfs.get(data.df_id);
                if (df) {
                    df.parseLogs.add(data.data, { merge: true });
                }
                break;
            case 'data_file_update':
                data.data.created = new Date(data.data.created);
                df = dfs.get(data.data.id);
                if (df) {
                    df.set(data.data);
                }
                break;
        }
    };
}

function listenUploadData() {
    var form = $("#upload_form"), key = '', filename, percent;
    return form.fileupload({
        dataType: "xml",
        add: function(event, data) {
            var fileSize = (data.files[0].size / 1024 / 1024).toFixed();
            var acceptFileTypes = /(\.|\/)(ts|ts.gz|ts.bz|ts.bz2|csv|csv.gz|csv.bz|csv.bs2|tar.gz|tar.bz|tar.bz2|zip)$/i;
            if (!acceptFileTypes.test(data.originalFiles[0].name)) {
                $('#uploadHelp').modal();
            } else if (fileSize > 1024) {
                $('#uploadSizeError').modal();
            } else {
                $('.btn').attr('disabled', true).on('click', function() {
                    return false;
                });
                data.submit();
            }
        },
        send: function(event, data) {
            $('.progress').show();
        },
        progress: function(event, data) {
            percent = (Math.round((event.loaded / event.total) * 1000) / 10);
            $('.progress .bar').css('width',  percent + "%");
            $('.progress-info-complete').text(Math.round(percent) + "%");
            $('.progress-info-filesize').text(Humanize.fileSize(event.loaded) + ' / ' + Humanize.fileSize(event.total));
        },
        fail: function(event, data) {
            window.location.replace("/dashboard/");
        },
        done: function(event, data) {
            window.location.replace("/dashboard/");
        }
    });
}

$(function() {
    var dfs = new DataFileList(),
        datasetWizard = new DatasetWizard(),
        ensembleWizard = new EnsembleWizard(),
        component, Router, router;
    Router = Backbone.Router.extend({
        routes: {
            "":                                 "home",
            "data-wizard/:id/":                 "dataWizard",
            "ensemble-wizard/:id/step/:name/":  "ensWizard"
        },
        home: function() {
            this.currentRoute = "home";
            datasetWizard.reset();
            ensembleWizard.reset();
            $('#dmHeading').removeClass('hide');
            $('#dataUpload').removeClass('hide').addClass('show');
        },
        dataWizard: function(id) {
            this.currentRoute = "dataWizard";
            datasetWizard.setInitValues(dfs.get(id), dfs);
            $('#dmHeading, #dataUpload').removeClass('show').addClass('hide');
        },
        ensWizard: function(id, name) {
            var df = dfs.get(id);
            if (df === undefined || !(name in ensembleWizard.steps)) {
                router.navigate('', {trigger: true});
                return;
            }
            if (ensembleWizard.get('dataFile') &&
                df.id === ensembleWizard.get('dataFile').id) {
                if (ensembleWizard.steps[name] < ensembleWizard.steps[ensembleWizard.get('currentStep')]) {
                    ensembleWizard.set('currentStep', name);
                    return;
                }
                if (ensembleWizard.get('currentStep') === name) {
                    return;
                }
            }
            this.navigate('ensemble-wizard/' + df.id + '/step/model-select/');
            this.currentRoute = "ensWizard";
            ensembleWizard.setInitValues(df, dfs);
            $('#dmHeading, #dataUpload').removeClass('show').addClass('hide');
        },
    });
    router = new Router();
    datasetWizard.router = router;
    ensembleWizard.router = router;
    dfs.fetch({
        'success': function() {
            Backbone.history.start({pushState: true, root: "/dashboard/"});
            React.renderComponent(
                DMComponent({dfs: dfs, datasetWizard: datasetWizard, ensembleWizard: ensembleWizard, router: router}),
                document.getElementById('df-list')
            );
        }
    });
    connect(wsUrl, {token: wsToken, salt: wsSalt}, dfs);
    listenUploadData();
});
