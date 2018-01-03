"use strict";

var Filter = require('./filter.js');
var BalanceComponent = require('./balanceComponent.jsx');

var BalanceFilter = Filter.extend({
    initialize: function() {
        this.set('component', BalanceComponent);
        this.file_format = this.get('wizard').get('dataFile').get('file_format');
        var wizard = this.get('wizard');
        this.dsmeta = wizard.get('dataFile').get('meta');
        //this.sample created on demand
        },

    name: 'balance',

    dump: function(filters) {
        filters = this.initDumpFilters(filters);
        // The current scheme *equalizes* classes. If this should change, delete
        // this.adjust assignment below  and fill-in ClassRow.handleChange
        // in the file balanceComponent.jsx 
        this.sample = this.sample ? this.sample : 'uniform';
        filters.push({
            name: this.name,
            sample: this.sample
            });
        return filters;
        },

    isApplicable: function() {
        return (this.file_format === 'GENERAL' && this.dsmeta.last_column_info.distrib !== undefined);
        },

    // Filters allowed after this one. NOT filters that this is allowed after.
    //allowedAfterThisFilter: ['split']
    allowedAfterThisFilter: ['normalize', 'shuffle', 'binarize', 'split', 'merge', "column select"],
    });

module.exports = BalanceFilter;
