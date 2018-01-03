/** @jsx React.DOM */
/* global React */

"use strict";

var Bootstrap = require('../bootstrap.jsx');
var Select = Bootstrap.SimpleSelect;

var BalanceFilterHead = React.createClass({
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
                   <i className="icon icon-white icon-tasks"></i> Balance
                   {this.props.message ? <em>{this.props.message}</em> : ''}
               </a>
               <a href="#" className={delete_class} onClick={this.props.removeFilter}>
                   <i className="icon icon-white icon-remove"></i>
                </a>
               </div>;
    }
});

var BalanceFilterBody = React.createClass({
    handleChange: function(e) {
        this.props.filter.sample = e.target.value;
        this.forceUpdate();
    },

    render: function() {
        var dsmeta = this.props.filter.dsmeta;
        var numClasses = Object.keys(dsmeta.last_column_info.distrib).length;
        var classRowsList = [];
        var values = [['uniform', 'uniform'],
                      ['oversampling','oversampling'],
                      ['undersampling','undersampling']];
        var value = this.props.filter.sample || 'uniform';
        for (var k in dsmeta.last_column_info.distrib) {
            classRowsList.push(<ClassRow className={k} bFilter={this.props.filter} numClasses={numClasses}/>);
        }
        return (
            <div>
                <h3>Balance</h3>
                <p>Select a sampling method to balance the number of sampled elements per class.</p>
                <div>
                    <table className="table-filters">
                        <tr>
                            <th width="40%">Class</th>
                            <th width="20%">Real</th>
                            <th width="40%">Adjusted</th>
                        </tr>
                        {classRowsList}
                    </table>
                </div>
                <div className="balance-technique">
                    <strong>Technique:</strong> <Select values={values} handleChange={this.handleChange} value={value}/>
                </div>
            </div>
            );
        }
    });

var ClassRow = React.createClass({
    handleChange: function() {
        /***********************************************************************
         * Placeholder. If we choose to allow users to manually select         *
         * percentages per row one day, this function will update this.adjust  *
         * array with the user selected value and do consistency checks to     *
         * ensure that the percentages for all classes sum to 100.             *
         ***********************************************************************/
        },

    render: function() {
        var percent = Math.round(this.props.bFilter.dsmeta.last_column_info.distrib[this.props.className] * 100);
        return (
            <tr>
                <td width="40%">{this.props.className}</td>
                <td width="20%">{percent}%</td>
                <td width="40%">{Math.round(1 / this.props.numClasses * 100)}%</td>
            </tr>
            );
        }
    });

module.exports = {
    head: BalanceFilterHead,
    body: BalanceFilterBody
    };
