/** @jsx React.DOM */
/* global React */
/* global _ */
/* global d3 */

"use strict";
var Utils = require('../Utils');

var BarXaxis = React.createClass({
    updateAxes: function() {
        var svg = d3.select(this.getDOMNode());
        var xAxis = d3.svg.axis()
                        .scale(this.props.x)
                        .orient("bottom");
        svg.call(xAxis);
    },

    componentDidMount: function() {
        this.updateAxes();
    },

    componentDidUpdate: function() {
        this.updateAxes();
    },

    render: function() {
        return <g className="x axis" transform={"translate(0," + this.props.height + ")"} />;
    }
});

var BarYaxis = React.createClass({
    updateAxes: function() {
        var formatPercent = d3.format(".0%");
        var svg = d3.select(this.getDOMNode());
        var yAxis = d3.svg.axis()
                        .scale(this.props.y)
                        .orient("left")
                        .tickFormat(formatPercent);
        svg.call(yAxis);
    },
    componentDidMount: function() {
        this.updateAxes();
    },

    componentDidUpdate: function() {
        this.updateAxes();
    },

    render: function() {
        return <g className="y axis" />;
    }
});

var CMBarChart = React.createClass({
    getDefaultProps: function() {
        return {
            margin: {
                top: 20, right: 20, bottom: 30, left: 60
            }
        };
    },

    handleSelectClass: function(classNum, e) {
        this.props.handleSelectClass(classNum);
    },

    render: function() {
        var bars = null, props = this.props, data = props.data;
        var newWidth = 85 * props.data.length,
            margin = props.margin;
        var width = ( newWidth > props.width ) ? props.width : newWidth;
        width = width - margin.left - margin.right;
        var height = props.height - margin.top - margin.bottom;
        var x = d3.scale.ordinal()
                        .rangeRoundBands([0, width], 0.3);
        var y = d3.scale.linear()
                        .range([height, 0]);
        data.forEach(function(d) {
            d.percent = +d.percent;
        });

        x.domain(data.map(function(d) { return d.class; }));
        y.domain([0, 1]);
        bars = data.map(function(d) {
            return <rect onMouseEnter={this.handleSelectClass.bind(this, d.class)}
                        onMouseLeave={this.props.handleUnselectClass}
                        className="bar"
                        key={d.class}
                        x={x(d.class)}
                        width={x.rangeBand()}
                        y={y(d.percent)}
                        height={height - y(d.percent)} />;
        }, this);
        return (
            <svg width={width + margin.left + margin.right}
                 height={height + margin.top + margin.bottom}>
                <g transform={"translate(" + margin.left + "," + margin.top + ")"} >
                    {bars}
                    <BarXaxis x={x} height={height} />
                    <BarYaxis y={y} />
                </g>
            </svg>
        );
    }
});

var ConfusionMatrixChart = React.createClass({
    predictValues: function(matrix, predicted) {
        return _.values(matrix).map(function(d) {
            return d[predicted] || 0;
        });
    },

    getInitialState: function() {
        return {selectedCol: undefined, selectedRow: undefined};
    },

    handleSelectRow: function(rowNum) {
        this.setState({selectedRow: rowNum});
    },

    handleSelectCol: function(colNum) {
        this.setState({selectedCol: colNum});
    },

    handleUnselectClass: function() {
        this.setState({selectedCol: undefined, selectedRow: undefined});
    },

    render: function() {
        var barChartName,
            props = this.props,
            rows = null, header = null, firstTd = null,
            msize = _.size(props.matrix),
            sum = {}, total = {}, classes =_.keys(props.matrix);

        classes.forEach(function(actual) {
            total[actual] = Utils.sum(_.values(props.matrix[actual]));
        });
        if (props.groupByPredict) {
            barChartName = "Distribution of model predictions (" + this.props.name + ")";
            for (var predicted=0; predicted<msize; predicted++) {
                sum[predicted] = Utils.sum(this.predictValues(props.matrix, predicted));
            }
        } else {
            barChartName = "Distribution of correct classifications (" + this.props.name + ")";
            sum = total;
        }
        header = classes.map(function(actual) {
            return <td key={actual}><b>class {actual}</b></td>;
        });
        var data = [];
        rows = classes.map(function(actual, i) {
            var row = classes.map(function(predicted) {
                var summa = (props.groupByPredict) ? sum[predicted] : sum[actual];
                var value = props.matrix[actual][predicted] || 0,
                    percent = (summa) ? value / summa : 0,
                    color = 1 - percent;
                if ( actual === predicted ) {
                    if (total[actual] === 0) {
                        color = 1; // if 0 samples in class then 0% is 100% accuracy
                    } else {
                        color = percent;
                    }
                    data.push({class: actual, percent: percent});
                }
                color = (color * 10).toFixed(0);
                var cls = "conf-matrix-cell q" + color + "-11";
                if (predicted === this.state.selectedCol) {
                    cls += " confusion-col";
                }
                return <td key={predicted} className={cls}>{value}<br /> {(percent * 100).toFixed(1).replace(/\.?0+$/, '')}%</td>;
            }, this);
            firstTd = null;
            if (!i) {
                firstTd = <td rowSpan={msize} className="span1"><strong dangerouslySetInnerHTML={{__html: 'ACTUAL'.split('').join('<br />')}} /></td>;
            }
            var cls = "";
            if (actual === this.state.selectedRow) {
                cls += " confusion-row";
            }
            return (
                <tr key={actual} className={cls}>
                    {firstTd}
                    <td className="span2"><b>class {actual}</b><br /> total: {total[actual]}</td>
                    {row}
                </tr>
            );
        }, this);
        sum = Utils.sum(total);
        var adata = [];
        for (var key in total) {
            if (total.hasOwnProperty(key)) {
                adata.push({class: key, percent: total[key] / sum});
            }
        }
        return (
            <div className="train-sets">
                <h4>{props.name}</h4>
                <table className="table conf-matrix">
                    <tbody>
                        <tr>
                            <td colSpan="2" rowSpan="2">Iteration {props.stat.get('iteration')}</td>
                            <td colSpan={classes.length}><strong>PREDICTED</strong></td>
                        </tr>
                        {header}
                        {rows}
                    </tbody>
                </table>
                <div className="bar-chart">
                    <h4>Class membership histogram ({props.name})</h4>
                    <CMBarChart width={props.width} height={props.height/2} data={adata}
                                handleSelectClass={this.handleSelectCol}
                                handleUnselectClass={this.handleUnselectClass} />
                </div>
                <div className="bar-chart bar-chart-distribution">
                    <h4>{barChartName}</h4>
                    <CMBarChart width={props.width} height={props.height/2} data={data}
                                handleSelectClass={(props.groupByPredict) ? this.handleSelectCol : this.handleSelectRow}
                                handleUnselectClass={this.handleUnselectClass} />
                </div>
            </div>
        );
    }
});


var Rect = React.createClass({
    tooltipCreate: function(e) {
        $(e.target).tooltip({
            placement: 'top',
            container: 'body',
            title: this.props.title
        });
    },

    tooltipDestroy: function(e) {
        $(e.target).tooltip('destroy');
    },

    render: function() {
        //we use data-rect-color instead of class because of bug in
        //react.js https://github.com/facebook/react/pull/1264
        var props = this.props;
        return <rect
                onMouseEnter={this.tooltipCreate}
                onMouseLeave={this.tooltipDestroy}
                width={props.width}
                height={props.height}
                x={props.x}
                y={props.y}
                data-rect-color={"q" + props.color + "-11"} />;
    }
});

var SmallConfusionMatrix = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return [this.props.stats];
    },

    predictValues: function(matrix, predicted) {
        return _.values(matrix).map(function(d) {
            return d[predicted] || 0;
        });
    },

    render: function() {
        var matrix = this.props.stats.last().get('confusion_matrix');
        var props = this.props,
            rows = null,
            msize = _.size(matrix),
            cellsize = (300 / msize > 20) ? 20 : (300 / msize),
            sum = {}, total = {}, classes =_.keys(matrix);
        classes.forEach(function(actual) {
            total[actual] = Utils.sum(_.values(matrix[actual]));
        });
        for (var predicted=0; predicted<msize; predicted++) {
            sum[predicted] = Utils.sum(this.predictValues(matrix, predicted));
        }
        rows = classes.map(function(actual, i) {
            var row = classes.map(function(predicted, j) {
                var summa = sum[predicted];
                var value = matrix[actual][predicted] || 0,
                    percent = (summa) ? value / summa : 0,
                    color = 1 - percent;
                if (actual === predicted) {
                    if (total[actual] === 0) {
                        color = 1; // if 0 samples in class then 0% is 100% accuracy
                    } else {
                        color = percent;
                    }
                }
                color = (color * 10).toFixed(0);
                return <Rect
                        width={cellsize}
                        height={cellsize}
                        x={cellsize*j}
                        y={cellsize*i}
                        key={j}
                        title={"Actual: " + actual + ", Predicted: " + predicted + ", Percent: " + (percent * 100).toFixed(4) + "%"}
                        color={color} />;

            });
            return (
                <g key={i}>
                    {row}
                </g>
            );
        });
        return (
            <svg className="RdYlGn" width={300} height={300}>
                {rows}
            </svg>
        );
    }
});

module.exports = {
    ConfusionMatrixChart: ConfusionMatrixChart,
    SmallConfusionMatrix: SmallConfusionMatrix
};
