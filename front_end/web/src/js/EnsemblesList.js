/* global require */
/* global React */
/* global Backbone */

"use strict";
var ELComponent = require('./ELComponent.jsx');

var EnsemblesItem = Backbone.Model.extend({
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


var EnsemblesList = Backbone.Collection.extend({
    model: EnsemblesItem,

    url: function() {
        return '/api/ensemble/';
    }
});



$(function() {
    var ensembles = new EnsemblesList();
    ensembles.fetch({
        'success': function() {
            React.renderComponent(
                ELComponent({ens: ensembles}),
                document.getElementById('en-list')
            );
        }
    });
});
