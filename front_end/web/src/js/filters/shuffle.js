"use strict";

var Filter = require('./filter.js');
var ShuffleComponent = require('./shuffleComponent.jsx');

var ShuffleFilter = Filter.extend({
    initialize: function() {
        this.set('component', ShuffleComponent);
        this.file_format = this.get('wizard').get('dataFile').get('file_format');
    },

    isApplicable: function() {
        return (this.file_format === 'GENERAL');
    },

    name: 'shuffle',

    //allowedAfterThisFilter: ['merge', 'normalize', 'binarize', 'split']
    allowedAfterThisFilter: ['normalize', 'binarize', 'split', 'balance', 'merge', "column select"],
});

module.exports = ShuffleFilter;
