/* global Backbone */
/* global _ */

"use strict";

var Filter = Backbone.Model.extend({
    dump: function(filters) {
        filters = this.initDumpFilters(filters);
        filters.push({name: this.name});
        return filters;
    },

    initDumpFilters: function(filters) {
        if (filters === undefined || filters.length === 0) {
            filters = [];
        }
        return filters;
    },

    getHeadComponent: function() {
        var Component = this.get('component').head;
        return Component({handleClick: this.onSelect.bind(this), key: this.name});
    },

    getAppliedComponent: function(state) {
        var Component = this.get('component').head;
        var filterState = this.get('wizard').get('state'), status = '', message = '';
        switch (state) {
            case 'update':
                status = 'active';
                break;
            case 'dismiss':
                status = 'warning disabled';
                message = 'Will be dropped on update';
                break;
            case 'applied':
                status = 'disabled';
                break;
            default:
                break;
        }
        return Component({handleClick: this.onAppliedSelect.bind(this),
                          key: this.name, status: filterState, select: status, message: message, removeFilter:this.deleteFilter.bind(this)});
    },

    onSelect: function(e) {
        e.preventDefault();
        this.get('wizard').selectFilter(this);
    },

    onAppliedSelect: function(e) {
        e.preventDefault();
        this.get('wizard').selectFilterForUpdate(this);
    },

    getBodyComponent: function(status) {
        var Component = this.get('component').body;
        return Component({key: this.name, filter: this, status:status});
    },

    isApplicable: function() {
        return true;
    },

    deleteFilter: function(e){
        e.preventDefault();
        this.get('wizard').resetFilter(this);
    },

});

module.exports = Filter;
