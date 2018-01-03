/** @jsx React.DOM */
/* global React */
/* global Humanize */


"use strict";
var Bootstrap = require('./../bootstrap.jsx');
var BootstrapSlider = Bootstrap.Slider;
var Utils = require('./../Utils.js');

var SplitFilterHead = React.createClass({
    render: function() {
        if(this.props.status){
            var delete_class = "delete_filter";
            var filter_button = 'filter_button_delete';
            var div_class = 'filter_container';
            }
        else{
            var filter_button = this.props.status;
            var delete_class = 'hide_delete';
            var div_class = '';
        }
        if(this.props.select == "disabled")
            div_class = div_class + " disabled";

        if(this.props.status == "update-filter" && this.props.select == "active"){
            filter_button = filter_button + " deleted_disabled";
            delete_class = delete_class + " delete_disabled";
}
        filter_button = filter_button + " " + this.props.select;

        return <div ref='filter_div' className={div_class}>
                <a onClick={this.props.handleClick} className={filter_button} href="#">
                   <i className="icon icon-white icon-resize-full"></i> Split
                   {this.props.message ? <em>{this.props.message}</em> : ''}
               </a>
               <a href="#" className={delete_class} onClick={this.props.removeFilter}>
                   <i className="icon icon-white icon-remove"></i>
                </a>
               </div>;
    }
});

var SplitFilterBody = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return [this.props.filter];
    },
    onSlide: function(value) {
        this.props.filter.set('value', value);
    },
    onChangeFilenameTrain: function(e) {
        this.props.filter.set('filenameFirst', e.target.value);
        this.props.filter.validate();
    },
    onChangeFilenameTest: function(e) {
        this.props.filter.set('filenameSecond', e.target.value);
        this.props.filter.validate();
    },
    render: function() {
        var filter = this.props.filter;
        return (
            <div className="split-filter">
                <h3>Split</h3>
                <em className="note-italic">Use slider to choose range for data split</em>
                <BootstrapSlider min={1} max={99} step={1} value={filter.get('value')} handleSlide={this.onSlide} />

                <div className="data-split clearfix">
                    <div className="dataset_column">
                        <h4>Dataset 1</h4>
                        <div className="data-split-info">
                            <span className="data-split-percentage">{filter.get('value') + "%"}</span>
                            <span className="data-split-samples">{Humanize.intComma(filter.getSamples())} samples</span>
                        </div>
                        <div className="dataset-name">
                            <label><i className="icon icon-white icon-file"></i> Set dataset name</label>
                            <input type="text" onChange={this.onChangeFilenameTrain} value={filter.get('filenameFirst')} className="input-dark" />
                        </div>
                    </div>
                    <div className="dataset_column">
                        <h4>Dataset 2</h4>
                        <div className="data-split-info">
                            <span className="data-split-percentage">{100 - filter.get('value') + "%"}</span>
                            <span className="data-split-samples">{Humanize.intComma(filter.get('totalSamples') - filter.getSamples())} samples</span>
                        </div>
                        <div className="dataset-name">
                            <label><i className="icon icon-white icon-file"></i> Set dataset name</label>
                            <input type="text" onChange={this.onChangeFilenameTest} value={filter.get('filenameSecond')} className="input-dark" />
                        </div>
                    </div>
                </div>
            </div>
        );
    }
});

module.exports = {
    head: SplitFilterHead,
    body: SplitFilterBody
};
