/** @jsx React.DOM */
/* global React */

"use strict";

var ShuffleFilterHead = React.createClass({
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
                   <i className="icon icon-white icon-random"></i> Shuffle
                   {this.props.message ? <em>{this.props.message}</em> : ''}
               </a>
               <a href="#" className={delete_class} onClick={this.props.removeFilter}>
                   <i className="icon icon-white icon-remove"></i>
                </a>
               </div>;
    }
});

var ShuffleFilterBody = React.createClass({
    render: function() {
        return (
            <div>
                <h3>Shuffle</h3>
                <p>This routine simply shuffles your dataset.<br />This might be helpful if you'd like to get a new independent split for training/testing purposes.</p>
            </div>
        );
    }
});

module.exports = {
    head: ShuffleFilterHead,
    body: ShuffleFilterBody
};
