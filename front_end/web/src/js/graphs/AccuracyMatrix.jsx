/** @jsx React.DOM */
/* global React */
/* global _ */
/* global d3 */

"use strict";
var Utils = require('../Utils');


var Rect = React.createClass({
    tooltipCreate: function(e) {
        $(e.target).tooltip({
            placement: 'top',
            container: 'body',
            title: "T" + this.props.key + ": " + (this.props.value * 100).toFixed(4) + "%"
        });
    },

    tooltipDestroy: function(e) {
        $(e.target).tooltip('destroy');
    },

    render: function() {
        return (
            <rect onMouseEnter={this.tooltipCreate}
                  onMouseLeave={this.tooltipDestroy}
                  x={this.props.x}
                  y={this.props.y}
                  width={this.props.width}
                  height={this.props.height}
                  className={this.props.classes}
                  data-toggle="tooltip" />
        );
    }
});

var AccuracyMatrix = React.createClass({
    getAccuracy: function(gridWidth, gridHeight, matrix) {
        var data = [];
        var gridItemWidth = gridWidth / matrix[0].length;
        var gridItemHeight = gridHeight / matrix.length;
        var min_len = Math.min(gridItemHeight, gridItemWidth);
        if ( min_len < 1 ) {
            gridItemWidth = 1;
            gridItemHeight = 1;
        } else if ( min_len > 20 ) {
            gridItemWidth = 20;
            gridItemHeight = 20;
        } else {
            gridItemWidth = min_len;
            gridItemHeight = min_len;
        }
        var startX = 0;
        var startY = 0;
        var stepX = gridItemWidth;
        var stepY = gridItemHeight;
        var xpos = startX;
        var ypos = startY;
        var newValue = 0;
        var count = 0;

        for (var index_a = 0; index_a < matrix.length; index_a++)
        {
            data.push([]);
            for (var index_b = 0; index_b < matrix[0].length; index_b++)
            {
                newValue = matrix[index_a][index_b];
                data[index_a].push({
                    time: index_b,
                    value: newValue,
                    width: gridItemWidth,
                    height: gridItemHeight,
                    x: xpos,
                    y: ypos,
                    count: count
                });
                xpos += stepX;
                count += 1;
            }
            xpos = startX;
            ypos += stepY;
        }
        return data;
    },

    render: function() {
        var data = this.getAccuracy(this.props.width, this.props.height, this.props.stat.get('test_accuracy_matrix')),
            cells = null,
            maxVal = (d3.max(data[0], function(d) { return d.value;}) > 1) ? 100.0 : 1.0,
            color = d3.scale.quantize()
                .domain([0, maxVal])
                .range(d3.range(11).map(function(d) { return 'q' + d + '-11'; }));
        cells = data[0].map(function(d) {
            return <Rect key={d.time} x={d.x} y={d.y} width={d.width} height={d.height} classes={"cell " + color(d.value)} value={d.value}/>;
        });
        return (
            <svg width={this.props.width} height={this.props.height} className="RdYlGn">
                <g className="row">
                    {cells}
                </g>
            </svg>
        );
    }

});

var AccuracyMatrixTableRow = React.createClass({
    getDefaultProps: function() {
        return {
            height: 20,
            width: 600
        };
    },

    render: function() {
        return (
            <tr>
                <td>{this.props.stat.get('iteration')}</td>
                <td><AccuracyMatrix stat={this.props.stat} width={this.props.width} height={this.props.height} /></td>
                <td>{(this.props.stat.get('test_accuracy') * 100).toFixed(4)}%</td>
                <td>{Utils.secondsToStr(this.props.stat.get('time'))}</td>
            </tr>
        );
    }
});

var AccuracyMatrixTable = React.createClass({
    render: function() {
        var charts = this.props.stats.map(function(stat) {
            return <AccuracyMatrixTableRow stat={stat} key={stat.id} />;
        });
        charts.reverse();
        return (
            <table className="table all-accuracy-charts">
                <thead>
                    <tr>
                        <th className="span1">Iteration</th>
                        <th>Accuracy Matrix</th>
                        <th>Test Accuracy</th>
                        <th>Iter. Time</th>
                    </tr>
                </thead>
                <tbody>
                    {charts}
                </tbody>
            </table>
        );
    }
});

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

module.exports = AccuracyMatrixTable;
