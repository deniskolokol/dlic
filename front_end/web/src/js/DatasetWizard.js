/* global _ */
/* global Backbone */

"use strict";

var SplitFilter = require('./filters/split.js');
var MergeFilter = require('./filters/merge.js');
var NormalizeFilter = require('./filters/normalize.js');
var ShuffleFilter = require('./filters/shuffle.js');
var BinarizeFilter = require('./filters/binarize.js');
var ColumnSelectFilter = require('./filters/columnSelect.js');
var BalanceFilter = require('./filters/balance.js');

var register = [
    ColumnSelectFilter,
    NormalizeFilter,
    ShuffleFilter,
    MergeFilter,
    BalanceFilter,
    BinarizeFilter,
    SplitFilter,
];

Array.prototype.move = function(from, to) {
    this.splice(to, 0, this.splice(from, 1)[0]);
};

var Wizard = Backbone.Model.extend({
    setInitValues: function(df, dfs) {
        var Model, self = this, filter,
            lastColumnIsOutput = ((df.get('file_format') === 'GENERAL') && (df.get('meta').last_column_info.classes !== null));
        this.reset();
        this.set({state: 'select-filter', dataFile: df});
        this.dfs = dfs;
        this.filtersForDismiss = [];
        this.set('lastColumnIsOutput', lastColumnIsOutput);
        for (var i=0; i<register.length; i++) {
            Model = register[i];
            filter = new Model({wizard: self});
            if (filter.isApplicable()) {
                this.filterRegister[filter.name] = filter;
                this.filtersAllowed.push(filter.name);
            }
        }
        if (df.get('file_format') === 'GENERAL')
            this.selectFilter(this.filterRegister['column select']);
        this.trigger('change');
    },

    reset: function() {
        var id = this.id;
        this.clear();
        this.set({id: id});
        this.filterRegister = [];
        this.filtersAllowed = [];
        this.filtersApplied = [];
        this.dfs = undefined;
    },

    filterRegister: {},

    filtersAllowed: [],

    filtersApplied: [],

    filtersForDismiss: [],

    states: [
        'select-filter',
        'setup-filter',
        'update-filter'
    ],

    getNextFilters: function() {
        var self = this, Filter;
        return this.filtersAllowed.map(function(name) {
            return self.filterRegister[name];
        });
    },

    getCurrentFilter: function() {
        return this.get('currentFilter');
    },

    selectFilter: function(filter) {
        this.set({currentFilter: filter, state: 'setup-filter'});
    },

    showOutputFilter: function(filter) {
        var state = 'setup-filter';
        for (var i=0; i<this.filtersApplied.length; i++) {
            if (this.filtersApplied[i] === 'column select') {
                this.filtersApplied.splice(i, 1);
                state = "update-filter";
            }
        }
        this.set({currentFilter: this.filterRegister['column select'], state: state});
    },



    applyFilter: function(filter) {
        var allFilters = [_.keys(this.filterRegister)], self = this, temp;
        this.filtersApplied.push(filter.name);
        this.filtersApplied.move(this.filtersApplied.length -1, this.get('currentFilterPos'));

        var filter_pos = this.filtersApplied.indexOf("column select");
        if(filter_pos > -1)
            this.filtersApplied.move(filter_pos, this.filtersApplied.length - 1);

        filter_pos = this.filtersApplied.indexOf("balance");
        if(filter_pos > -1 )
            this.filtersApplied.move(filter_pos, 0);

        filter_pos = this.filtersApplied.indexOf("split");
        if(filter_pos > -1)
            this.filtersApplied.move(filter_pos, 0);

        for (var i=0; i<this.filtersApplied.length; i++) {
            allFilters.push(self.filterRegister[self.filtersApplied[i]].allowedAfterThisFilter);
        }
        temp = _.intersection.apply(null, allFilters);
        this.filtersAllowed = _.difference(temp, this.filtersApplied);
        this.set({state: 'select-filter', currentFilter: undefined});
        this.set('finish-request', '');
    },

    selectFilterForUpdate: function(filter) {
        var filter_pos;
        for (var i=0; i<this.filtersApplied.length; i++) {
            if (this.filtersApplied[i] === filter.name) {
                this.filtersApplied.splice(i, 1);
                filter_pos = i;
            }
        }
        this.set({currentFilter: filter, state: 'update-filter', currentFilterPos: filter_pos});
        this.set('finish-request', '');
    },

    cancelUpdate: function(filter) {
        this.filtersApplied.push(this.getCurrentFilter().name);
        var filter_pos = this.filtersApplied.indexOf("column select");
        if(filter_pos > -1)
            this.filtersApplied.move(filter_pos, this.filtersApplied.length - 1);

        filter_pos = this.filtersApplied.indexOf("balance");
        if(filter_pos > -1 )
            this.filtersApplied.move(filter_pos, 0);

        filter_pos = this.filtersApplied.indexOf("split");
        if(filter_pos > -1)
            this.filtersApplied.move(filter_pos, 0);

        this.set({state: 'select-filter', currentFilter: undefined});
        this.set('finish-request', '');
    },

    cancelSelect: function(filter) {
        this.set({state: 'select-filter', currentFilter: undefined});
        this.set('finish-request', '');
    },

    resetFilter: function(filter){
        this.filtersApplied.splice(this.filtersApplied.indexOf(filter.name), 1);
        this.filtersAllowed.push(filter.name);

        if(filter.name == 'column select')
            this.outputs = false;

        if(!this.getCurrentFilter() || this.getCurrentFilter() == filter){
            this.set({state: 'select-filter', currentFilter: undefined});
            this.set('finish-request', '');
            }
        this.trigger('change');
    },

    resetAllFilters: function() {
        this.filtersAllowed = _.keys(this.filterRegister);
        this.filtersApplied = [];
        this.set({state: 'select-filter', currentFilter: undefined});
        this.set('finish-request', '');
        this.trigger('change');
    },

    beforeFinish: function() {
        this.set('finish-request', 'before');
    },

    doneFinish: function(data) {
        var df = this.get('dataFile'), datasets = df.get('datasets');
        if ($.isArray(data)) {
            for (var i=0; i<data.length; i++) {
                datasets.push({id: data[i].id, name: data[i].name, last_column_is_output: data[i].last_column_is_output, filters: data[i].filters});
            }
        } else {
            datasets.push({id: data.id, name: data.name, last_column_is_output: data.last_column_is_output, filters: JSON.stringify(data.filters)});
        }
        df.set('datasets', datasets);
        df.set('isNewDatasetCreated', true); // jTour will check this and cookie
        this.router.navigate('', {trigger: true});
        this.set('finish-request', 'done');
    },

    failFinish: function() {
        this.set('finish-request', 'fail');
    },

    finish: function() {
        var data = [], self = this;
        for (var i=0; i<this.filtersApplied.length; i++) {
            data = self.filterRegister[self.filtersApplied[i]].dump(data);
        }
        //XXX: should be fixed
        //we should use name select as last filter and always
        //return ready to post data
        if (data.length === 0 || data[0].filters === undefined) {
            console.log('length 0 ');
            data = {
                name: self.get('firstDatasetName'),
                filters: data,
                data: self.get('dataFile').id
            };
            if (self.get('dataFile').get('file_format') === 'GENERAL') {
                data.last_column_is_output = self.get('lastColumnIsOutput');
            }
        } else {
            if (self.get('dataFile').get('file_format') === 'GENERAL') {
                data[0].last_column_is_output = self.get('lastColumnIsOutput');
                data[1].last_column_is_output = self.get('lastColumnIsOutput');
            }

            data[0]['filters'] = data[0]['filters'].concat(data.slice(2));
            data[1]['filters'] = data[1]['filters'].concat(data.slice(2));
            data = data.slice(0,2);
        }
        console.log(JSON.stringify(data, null, 2));
        this.beforeFinish();
        $.ajax({
            url: '/api/dataset/',
            type: 'POST',
            data: JSON.stringify(data, null, 2),
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            self.doneFinish(data);
        }).fail(function (xhr) {
            self.failFinish(xhr);
        });
    }
});

module.exports = Wizard;
