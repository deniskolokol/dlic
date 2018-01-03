"use strict";

var Filter = require('./filter.js');
var BinarizeComponent = require('./binarizeComponent.jsx');

var BinarizeFilter = Filter.extend({
    initialize: function() {
        this.set('component', BinarizeComponent);
    },

    name: 'binarize',

    //allowedAfterThisFilter: ['shuffle', 'split'],
    allowedAfterThisFilter: ['normalize', 'shuffle', 'split', 'balance', 'merge'],

    isApplicable: function() {
        var meta = this.get('wizard').get('dataFile').get('meta');
        return (meta.data_type === 'TIMESERIES' && !meta.binary_input);
    }
});

module.exports = BinarizeFilter;
