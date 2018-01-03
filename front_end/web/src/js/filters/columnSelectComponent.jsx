/** @jsx React.DOM */
/* global React */

"use strict";
var Bootstrap = require('../bootstrap.jsx');
var BarChartComponent = require('./barChartComponent.jsx');

var Select = Bootstrap.SimpleSelect;
var BarChart = BarChartComponent.barchart,
    BootstrapAlert = Bootstrap.AlertList;

var ColumnSelectFilterHead = React.createClass({
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
                   <i className="icon icon-white icon-indent-right"></i> Select Columns
                   {this.props.message ? <em>{this.props.message}</em> : ''}
               </a>
               <a href="#" className={delete_class} onClick={this.props.removeFilter}>
                   <i className="icon icon-white icon-remove"></i>
                </a>
               </div>;
    }
});


var ColumnSelectFilterBody = React.createClass({
    getInitialState: function(e) {
        // get the contents of dtypes for assignment to initial values state.
        // returning `values: this.props.filter.dsmeta.dtypes` directly will
        // overwrite dtypes array on values state update!
        var decoupled = this.props.filter.dsmeta.dtypes.map(function(x) { return x; }); 
        return {
            values: decoupled,
            currentPage: 1,
            pageSize: 15
        };
    },

    componentWillReceiveProps: function(nextProps) {
        this.setState({ currentPage: 1 });
    },

    handleChange: function(colNum, value) {

        var cancel = this.props.status.refs.outputColumns.handleColumnChange(colNum, value);
        if(cancel == false){
            var tempValues = this.state.values;
            tempValues[colNum] = value; // because we can't use `values[colNum]` as key in setState
            this.setState({values: tempValues});
            this.props.filter.values = tempValues;
            //TODO: My nose tells me that there's unnecessary duplication of effort w/ respect
            // to ReactJS state versus props and copying from one to the other for communication
            // w/ the associated Backbone model object. Investigate.
        }
        return cancel;
    },

    getPage: function() {
        var start = this.state.pageSize * (this.state.currentPage - 1),
            end = start + this.state.pageSize;

        return {
            currentPage: this.state.currentPage,
            rows: this.props.filter.dsmeta.uniques_per_col.slice(start, end),
            numPages: this.getNumPages(),

            handleClick: function(pageNum) {
                return function() { this.handlePageChange(pageNum); }.bind(this);
            }.bind(this)
        };
    },

    getNumPages: function() {
        var rowsLength = this.props.filter.dsmeta.uniques_per_col.length;
        var numPages = Math.floor(rowsLength / this.state.pageSize);
        if (rowsLength % this.state.pageSize > 0) {
            numPages++;
        }
        return numPages;
    },

    handlePageChange: function(pageNum) {
        this.setState({ currentPage: pageNum });
    },

    render: function() {
        var page = this.getPage();
        var self = this;
        var selectionRowsList = page.rows.map(function(colUniq, i) {
            return <SelectionRow key={i} colNum={i}
                    numUniques={colUniq}
                    filterValues={this.props.filter.values}
                    dsmeta={this.props.filter.dsmeta}
                    handleChange={this.handleChange.bind(this, i + self.state.pageSize * (self.state.currentPage-1))}
                    pageSize={self.state.pageSize}
                    currentPage={self.state.currentPage}/>;
        }, this);

        var pagination = (this.props.filter.dsmeta.uniques_per_col.length <= this.state.pageSize) ? null : <Pagination page={page} />;

        return (
            <div className='span8'>
                <h3>Select Columns</h3>
                <p>Specify the type of each column in your data and mark any columns that you'd
                like to ignore. In the majority of cases, the intelligent defaults are intelligent.</p>


                <table className="table-filters">
                    <thead>
                        <tr>
                            <th>Column</th>
                            <th>Unique Values</th>
                            <th>Category</th>
                            <th>Histogram</th>
                        </tr>
                    </thead>
                    <tbody>
                        {selectionRowsList}
                    </tbody>
                </table>

                {pagination}

            </div>
        );
    }
});


var SelectionRow = React.createClass({
    getInitialState: function() {
        var i = this.props.colNum;
        return {
            value: this.props.dsmeta.dtypes[i]
        };
    },

    dragStart: function(name, e) {

        // Firefox requires calling dataTransfer.setData
        // for the drag to properly work

        var page_size = this.props.pageSize;
        var current_page = this.props.currentPage;

        var index = page_size * (current_page - 1) + this.props.colNum;

        var data = {
            name: name,
            type: this.state.value,
            index: index,
        };

        e.dataTransfer.setData("text", JSON.stringify(data));
    },

    handleChange: function(e) {
        var cancel = this.props.handleChange(e.target.value);
        if(cancel == false)
            this.setState({value: e.target.value});

    },

    render: function() {
        var i = this.props.colNum;
        var displayVals = {'f': 'numerical',
                           'i': 'categorical',
                           'S': 'text',
                           '-': 'ignore'};

        var key = null, values = null, histogramData, binsData, value = null, columnName = null;

        if (this.props.currentPage > 1) {
            i += (this.props.currentPage - 1) * this.props.pageSize;
        }


        key = this.props.dsmeta.dtypes[i];
        columnName = this.props.dsmeta.names[i];
        binsData = this.props.dsmeta.bins ? this.props.dsmeta.bins[i] : undefined;
        histogramData = this.props.dsmeta.histogram[i];
        value = this.props.filterValues[i] || 'f';

        var tooltipData = [histogramData, binsData];

        // if the column is locked, its only options are itself and ignore
        // if the column is unlocked and it is an integer, it can be categorical, numerical, or ignore
        // if the column is unlocked and is text, it can be text or ignore
        //
        values = [ [key,displayVals[key]] ];
        if (!this.props.dsmeta.locked[i]) {
            if (key=='i')
                values = values.concat([ ['f', displayVals.f] ]);
        }
        values = values.concat([ ['-',displayVals['-']] ]);

        return (
            <tr draggable='true'  onDragStart={this.dragStart.bind(this, columnName)}>
                <td>{columnName}</td>
                <td><strong>{this.props.numUniques}</strong></td>
                <td><Select values={values} handleChange={this.handleChange} value={value}/></td>
                <td><BarChart width={120} height={30}
                              data={histogramData}
                              colors={["#1f77b4","#038d03","#9a3334"]}
                              tooltip={true} tooltipData={tooltipData} />
                </td>
            </tr>
        );
    }
});

var Pagination = React.createClass({
    render: function() {
        var page = this.props.page,
            start = null, end = null,
            prev = null, next = null, info = null;

        if (page.currentPage > 1) {
            if (page.currentPage > 2) {
                start = (
                    <span className="pagination-link" key="start" onClick={page.handleClick(1)}>«</span>
                );
            }
            prev = (
                <span className="pagination-link" key="prev" onClick={page.handleClick(page.currentPage - 1)}>‹</span>
            );
        }

        info = (
            <span className="pagination-current">Page <strong>{page.currentPage}</strong> of <strong>{page.numPages}</strong></span>
        );

        if (page.currentPage < page.numPages) {
            next = (
                <span className="pagination-link" key="next" onClick={page.handleClick(page.currentPage + 1)}>›</span>
            );
            if (page.currentPage < page.numPages - 1) {
                end = (
                    <span className="pagination-link" key="end" onClick={page.handleClick(page.numPages)}>»</span>
                );
            }
        }

        return (
            <div className="pagination">
                {start} {prev} {info} {next} {end}
            </div>
        );
    }
});

var TrOutput = React.createClass({

    removeColumn: function(e){
        this.props.removeColumn(this.props.order);
    },

    dragOver: function(e) {
        e.preventDefault();
    },

    render: function(){
        return(
            <tr data-id={this.props.order} draggable="true" onDragStart={this.props.dragStart} onDragEnd={this.props.dragEnd} onDragOver={this.props.dragOver} onDrop={this.props.drop}>
                <td>{this.props.text}</td>
                <td><button className='btn btn-mini btn-danger' onClick={this.removeColumn}>remove</button></td>
            </tr>
        );
    },

})

var OutputColumns = React.createClass({

    getInitialState: function() {
        var type = '';
        if(this.props.filter.outputs.length > 0)
            type = this.props.filter.type;
        return {
            columns:this.props.filter.outputs,
            type: type,
            change: [],
        };
    },

    removeColumn: function(column){

        var columns = this.state.columns;
        var type = this.state.type;

        columns.splice(column, 1);
        if(columns.length == 0){
            type = '';
            this.props.wizard.outputs = false;
            this.props.filter.type = '';
        }
        this.props.filter.outputs = columns;
        this.setState({columns:columns, type: type});
    },

    preventDefault: function (event) {
        event.preventDefault();
    },

    drop: function(e) {
        e.preventDefault();

        try {
            var data = JSON.parse(e.dataTransfer.getData('text'));
        } catch (e) {
            // If the text data isn't parsable we'll just ignore it.
            return;
        }

        var data_type = {f:'regression', i:'categorical', S:'categorical'};
        data_type = data_type[data.type];

        var type = this.state.type;
        if (type === '') {
            type = data_type;
        } else if (type != data_type) {
            if (data.type == '-') {
                this.refs.alert.addAlert("You can't add an ignored column!", 'error', 8000);
            } else {
                this.refs.alert.addAlert("You can't add an different types of columns!", 'error', 8000);
            }
            return;
        }

        var new_output = this.state.columns.concat({name:data.name, index:data.index});
        var repeated = false;
        this.state.columns.map(function(object, i) {
            if (object.index == data.index) repeated = true;
        });

        if (repeated) return false;
        var newState = {columns:new_output, type:type};
        this.props.filter.outputs = new_output;
        this.props.filter.type = type;
        this.setState(newState);
    },

    dragStart: function(id, e) {
        this.dragged = id;
        e.dataTransfer.effectAllowed = 'move';

        // Firefox requires calling dataTransfer.setData
        // for the drag to properly work
        e.dataTransfer.setData("text/html", e.currentTarget);
    },

    dragEnd: function(e) {
        var dragged = this.dragged;
        var over = this.over.dataset.id;

        var columns = this.state.columns;

        columns.map(function(object, i){
            if(object.name == dragged)
                dragged = i;
            else if(i == parseInt(over))
                over = i;
        });

        columns.move(dragged, over);
        this.props.filter.outputs = columns;

        this.setState({columns:columns});
    },

    dragOver: function(e){
        this.over = e.currentTarget;

    },

    handleColumnChange: function(column, value){
        var self = this;
        var cancel = false;
        var data_type = {f:'regression', i:'categorical', S:'categorical'};

        var columns = this.state.columns;;
        this.state.columns.map(function(object, i){
            if(object.index == column){
                if(value == '-'){
                    self.refs.alert.addAlert("You can't ignore a selected column, please remove the column first.", 'error', 8000);
                    cancel = true;
                }
                else if(self.state.type != data_type[value]){
                    self.refs.alert.addAlert("You can't change to this type of column, previous columns have a different type.", 'error', 8000);
                    cancel = true;
                }
            }

        });
        return(cancel);
    },

    render: function() {
        var columns = this.state.columns;
        var self = this;
        if(this.state.columns.length > 0)
            this.props.wizard.outputs = true;

        return(
        <div className='output'>
            <BootstrapAlert
                ref="alert"
                models={[]}>
            </BootstrapAlert>

            <p>Drag the columns from the table and drop it here to select them as output columns.</p>
            <p>You can reorder by draging the rows.</p>
            <table className="table-filters outputs" >
                <thead>
                    <tr>
                        <th colSpan="2">Column</th>
                    </tr>
                </thead>
                <tbody>

                    {columns.map(function(data, i) {
                        return <TrOutput text={data.name} key={data.index} order={i}  removeColumn={self.removeColumn}  drop={self.drop} dragStart={self.dragStart.bind(self, data.name)} dragEnd={self.dragEnd} dragOver={self.dragOver} />;
                    })}
                </tbody>
            </table>

        </div>)
    },
});

module.exports = {
    head: ColumnSelectFilterHead,
    body: ColumnSelectFilterBody,
    outputColumns: OutputColumns,
};
