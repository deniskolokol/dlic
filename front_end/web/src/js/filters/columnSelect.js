"use strict";

var Filter = require('./filter.js');
var ColumnSelectComponent = require('./columnSelectComponent.jsx');

var ColumnSelectFilter = Filter.extend({
    initialize: function() {
        this.set('component', ColumnSelectComponent);
        this.file_format = this.get('wizard').get('dataFile').get('file_format');
        var wizard = this.get('wizard');
        this.dsmeta = wizard.get('dataFile').get('meta');
        this.values = this.dsmeta.dtypes;
        this.outputs = [];
        this.type = '';
        },

    name: 'column select',

    dump: function(filters) {
        /********************************************************************************
         * Column Select Filter actually adds two separate elements to the list of      *
         * filters: `ignore`, a list of columns to be ignored, and `permute`, a         *
         * list of categorical columns that are to be binned. Columns not named         *
         * in either list are assumed to be numerical default and will be               *
         * normalized/scaled.                                                           *
         ********************************************************************************/
        // Get existing filters
        filters = this.initDumpFilters(filters);
        // Get list of columns 
        var keys = Object.keys(this.values);
        var ignores = [];
        var permutes = [];
        for (var i=0; i<keys.length; i++) {
            switch (this.values[ keys[i] ]) {
                case 'i':
                    // This array enumerates categorical columns
                    permutes.push(keys[i]);
                    break;
                case '-':
                    // This array enumerates ignored columns
                    ignores.push(keys[i]);
                    break;
                }
            }
        filters.push({name: 'ignore', columns: ignores.sort()});
        filters.push({name: 'permute', columns: permutes.sort()});
        filters.push({name: 'outputs', columns: this.outputs.map(function(object){return object.index})});
        return filters;
        },

    allowedAfterThisFilter: ['normalize', 'shuffle', 'binarize', 'split', 'balance', 'merge'],
    
    isApplicable: function() {
        return (this.file_format === 'GENERAL' && this.dsmeta.uniques_per_col !== undefined);
        },
    });
    

module.exports = ColumnSelectFilter;
