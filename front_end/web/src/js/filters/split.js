/* global _ */

"use strict";

var Filter = require('./filter.js');
var Utils = require('../Utils.js');
var SplitComponent = require('./splitComponent.jsx');


var SplitFilter = Filter.extend({
    initialize: function() {
        var wizard = this.get('wizard'),
            name = wizard.get('dataFile').get('name').split('.')[0];
        this.set('component', SplitComponent);
        if (wizard.get('dataFile').get('file_format') === 'IMAGES') {
            this.set('totalSamples', Utils.sum(_.values(wizard.get('dataFile').get('meta').classes)));
        } else {
            this.set('totalSamples', wizard.get('dataFile').get('meta').data_rows);
        }
        this.set('filenameFirst', name + '_train');
        this.set('filenameSecond', name + '_test');
        this.set('value', 70);
    },

    dump: function(filters) {
        var self = this, wizard = this.get('wizard'),
            filters1 = this.initDumpFilters(filters),
            filters2 = filters1.slice();
        filters1.push({
            name: this.name,
            start: 0,
            end: self.get('value')
        });
        filters2.push({
            name: this.name,
            start: self.get('value'),
            end: 100
        });
        return [{
            name: this.get('filenameFirst'),
            filters: filters1,
            data: wizard.get('dataFile').id
        }, {
            name: this.get('filenameSecond'),
            filters: filters2,
            data: wizard.get('dataFile').id
        }];
    },

    getSamples: function() {
        return this.get('value') * this.get('totalSamples') / 100;
    },

    validate: function() {
        var valid = (this.get('filenameFirst') && this.get('filenameSecond'));
        this.get('wizard').set('filterInvalid', !valid);
    },

    name: 'split',

    //allowedAfterThisFilter: []
    allowedAfterThisFilter: ['normalize', 'shuffle', 'binarize', 'balance', 'merge', "column select"],
});

module.exports = SplitFilter;
