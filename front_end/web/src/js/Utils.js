/* global _ */

"use strict";

function isBlank(string) {
    return !/\S/.test(string);
}

var Utils = {
    sum: function(values) {
        return _.reduce(values, function(memo, num) {
            return memo + num;
        }, 0);
    },

    getUrlParam : (function(a) {
        if (a === "") return {};
        var b = {};
        for (var i = 0; i < a.length; ++i)
        {
            var p=a[i].split('=');
            if (p.length != 2) continue;
            b[p[0]] = decodeURIComponent(p[1].replace(/\+/g, " "));
        }
        return b;
    })(window.location.search.substr(1).split('&')),

    showAlert: function(message, state, $block) {
        var $alert;
        $block = typeof $block !== 'undefined' ? $block : $('div.alert-block');
        $alert = $('<div class="alert alert-' + state + ' fade in"></div>')
            .append('<button class="close" data-dismiss="alert" type="button">×</button>')
            .append(message).alert();
        $block.prepend($alert);
        return $alert;
    },

    showFadeAlert: function(message, state, ms, $block) {
        var $alert = this.showAlert(message, state, $block);
        ms = typeof ms !== 'undefined' ? ms : 5000;
        window.setTimeout(function() {
            $alert.fadeTo(500, 0).slideUp(500, function() { $(this).remove(); });
        }, ms);
    },

    secondsToStr: function(delta) {
        var hours, minutes, seconds;
        if ( !delta ) { return '00:00:00'; }
        delta = delta.toFixed(0);
        hours = Math.floor(delta / 3600);
        delta %= 3600;
        minutes = Math.floor(delta / 60);
        seconds = delta % 60;
        if ( seconds < 10 ) { seconds = '0' + seconds; }
        if ( minutes < 10 ) { minutes = '0' + minutes; }
        if ( hours < 10 ) { hours = '0' + hours; }
        return hours + ':' + minutes + ':' + seconds;
    },

    isoDateToHumanize: function(date) {
        var dateNew = new Date(date),
            months = ["January", "February", "March", "April", "May", "June", "July",
                      "August", "September", "October", "November", "December"];
        return months[dateNew.getMonth()] + ' ' + dateNew.getDate() + ', ' + dateNew.getFullYear();
    },

    //TODO remove
    parseErrorResponse: function(xhr) {
        var problem = JSON.parse(xhr.responseText).problem, message;
        if (typeof problem === 'string') {
            message = problem;
        } else if ('__all__' in problem) {
            message = problem.__all__[0];
        } else {
            message = JSON.stringify(problem);
        }
        return message;
    },

    objToPaths: function(obj) {
        var ret = {}, separator = '.';

        for (var key in obj) {
            var val = obj[key];
            if (val && (val.constructor === Object || val.constructor === Array) && !_.isEmpty(val)) {
                var obj2 = this.objToPaths(val);

                for (var key2 in obj2) {
                    var val2 = obj2[key2];
                    ret[key + separator + key2] = val2;
                }
            } else {
                ret[key] = val;
            }
        }

        return ret;
    },

    startsWith: function(str, sub) {
        return str.slice(0, sub.length) === sub;
    },

    uuid: function() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
            return v.toString(16);
        });
    },

    BackboneMixin: {
        componentDidMount: function() {
            // Whenever there may be a change in the Backbone data, trigger a reconcile.
            this.getBackboneModels().forEach(function(model) {
                model.on('add change remove', this.forceUpdate.bind(this, null), this);
            }, this);
        },

        componentWillUnmount: function() {
            // Ensure that we clean up any dangling references when the component is
            // destroyed.
            this.getBackboneModels().forEach(function(model) {
                model.off(null, null, this);
            }, this);
        }
    },

    BackboneEventMixin: {
        componentDidMount: function() {
            // Whenever there may be a change in the Backbone data, trigger a reconcile.
            var eventsModels = this.getBackboneEvents(), model;
            for (var events in eventsModels) {
                model = eventsModels[events];
                model.on(events, this.forceUpdate.bind(this, null), this);
            }
        },

        componentWillUnmount: function() {
            // Ensure that we clean up any dangling references when the component is
            // destroyed.
            _.values(this.getBackboneEvents()).forEach(function(model) {
                model.off(null, null, this);
            }, this);
        }
    },

    TrainTestDatasetMixin: {
        getDefaultTrainDatasetId: function() {
            for (var i=0;i<this.props.datasets.length;i++) {
                if ( this.props.datasets[i][1].indexOf('train')>-1 )
                    return this.props.datasets[i][0];
            }
            var id;
            try { id = this.props.datasets[0][0]; } catch(e) {}
            return id;
        },

        getDefaultTestDatasetId: function() {
            for (var i=0;i<this.props.datasets.length;i++) {
                if ( this.props.datasets[i][1].indexOf('test')>-1 )
                    return this.props.datasets[i][0];
            };
            if (this.props.datasets.length < 2) {
                return this.getDefaultTrainDatasetId();
            };
            return this.props.datasets[1][0];
        }
    },

    compareMetaData: function(meta, cmeta){
        if (meta.data_type === 'TIMESERIES') {
            return (meta.binary_input === cmeta.binary_input &&
                    meta.binary_output === cmeta.binary_output &&
                    meta.input_size === cmeta.input_size &&
                    meta.output_size === cmeta.output_size);
        } else if (meta.data_type == 'GENERAL') {
            return (meta.num_columns === cmeta.num_columns);
        } else if (meta.data_type == 'IMAGES') {
            return true;
        } else {
            console.log("Error");
        }
    },

    ApplyTypesMixin: {
        applyTypes: function(params) {
            for (var key in this.validation) {
                if (isBlank(params[key])) {
                    delete params[key];
                }
                else if (typeof params[key] === "string") {
                    if (this.validation[key].pattern === 'digits') {
                        params[key] = parseInt(params[key], 10);
                    } else if (this.validation[key].pattern === 'number') {
                        params[key] = parseFloat(params[key], 10);
                    }
                }
            }
            return params;
        }
    },

    isBlank: isBlank
};

module.exports = Utils;
