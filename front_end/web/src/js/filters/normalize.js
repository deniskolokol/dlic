"use strict";

var Filter = require('./filter.js');
var NormalizeComponent = require('./normalizeComponent.jsx');

var NormalizeFilter = Filter.extend({
    initialize: function() {
        this.set('component', NormalizeComponent);
    },

    name: 'normalize',

    //allowedAfterThisFilter: ['shuffle', 'split'],
    allowedAfterThisFilter: ['shuffle', 'binarize', 'split', 'balance', 'merge', "column select"],

    isApplicable: function() {
        var meta = this.get('wizard').get('dataFile').get('meta');
        if (meta.data_type === 'GENERAL') {
            return true;
        }
        return false;
    },
});

module.exports = NormalizeFilter;