"use strict";

var Utils = require('../Utils.js');
var Filter = require('./filter.js');
var MergeComponent = require('./mergeComponent.jsx');

var MergeFilter = Filter.extend({
    initialize: function() {
        var wizard = this.get('wizard'),
            df = wizard.get('dataFile'),
            file_format = df.get('file_format'),
            dfs = wizard.dfs,
            self = this;
        this.file_format = file_format;
        this.set('component', MergeComponent);
        var values = dfs.where({file_format: file_format})
            .filter(function(val) {
                if (val.get('id') === df.get('id')) {
                    return false;
                }
                return Utils.compareMetaData(df.get('meta'), val.get('meta'));
            }).map(function(val) {
                return [val.get('id'), val.get('name')];
            });
        if (values.length > 0) {
            this.set({values: values, value: values[0][0]});
        } else {
            this.unset('values');
            this.unset('value');
        }
    },

    dump: function(filters) {
        filters = this.initDumpFilters(filters);
        filters.push({name: this.name, datas: [parseInt(this.get('value'), 10)]});
        return filters;
    },

    isApplicable: function() {
        return (this.get('values') !== undefined && this.file_format === 'GENERAL');
    },

    name: 'merge',

    //allowedAfterThisFilter: ['normalize', 'shuffle', 'binarize', 'split']
    allowedAfterThisFilter: ['normalize', 'shuffle', 'binarize', 'split', 'balance'],
});

module.exports = MergeFilter;
