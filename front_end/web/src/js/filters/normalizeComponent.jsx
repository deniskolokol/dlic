/** @jsx React.DOM */
/* global React */

"use strict";

var NormalizeFilterHead = React.createClass({
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
                   <i className="icon icon-white icon-signal"></i> Normalize
                   {this.props.message ? <em>{this.props.message}</em> : ''}
               </a>
               <a href="#" className={delete_class} onClick={this.props.removeFilter}>
                   <i className="icon icon-white icon-remove"></i>
                </a>
               </div>;
    }
});

var NormalizeFilterBody = React.createClass({
    render: function() {
        return (
            <div>
                <h3>Normalize</h3>
                <p>When Ersatz "normalizes" your data, it is scaling it to a 0-1 range. For instance, if you have a column with values of 0-255, this routine will scale those values back down to a 0-1 range. It does this for each column in your dataset.</p>
            </div>
        );
    }
});

module.exports = {
    head: NormalizeFilterHead,
    body: NormalizeFilterBody
};
