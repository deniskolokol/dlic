/** @jsx React.DOM */
/* global React */
/* global _ */
/* global d3 */

"use strict";
var Utils = require('../Utils');

var humanNames = {
    'train_accuracy': 'Training Accuracy',
    'train_last_10_steps_acc': 'Training Accuracy at Final 10 Steps',
    'test_last_10_steps_acc': 'Testing Accuracy at Final 10 Steps',
    'test_accuracy': 'Test Accuracy',
    'grad1': 'First Gradient',
    'grad2': 'Second Gradient (approx. Hessian)',
    'train_loss': 'Training Loss',
    'test_loss': 'Test Loss',
    'total_num_cg': 'Number of CG iterations',
    'norm_CG_x': 'Norm of CG',
    '1_h_norm': 'Input2Hidden Bias',
    'h_f_norm': 'Hidden2Factored',
    'f_h_norm': 'Factored2Hidden',
    '1_f_norm': 'Input2Factored Bias',
    'v_h_norm': 'Input2Hidden',
    'v_f_norm': 'Input2Factored',
    'h_o_norm': 'Hidden2Output',
    'momentum': 'Momentum',
    'learning_rate': 'Learning Rate',
    'last_layer_row_norms_mean': 'Last Layer Row Norms Mean',
    'last_layer_col_norms_mean': 'Last Layer Column Norms Mean',
    'iteration_time': 'Iterations Time (seconds)'
};

function getHumanName(name) {
    var val = humanNames[name];
    return (val) ? val : name;
}


var XAxis = React.createClass({
    updateAxes: function(options) {
        var svg = d3.select(this.getDOMNode()),
            width = this.props.width - this.props.margin.left - this.props.margin.right,
            xAxis = d3.svg.axis().scale(this.props.x).orient("bottom");
        svg.call(xAxis);
        if (options.isMount) {
            svg.append('text')
                .attr('x', (width / 2 + this.props.margin.left))
                .attr('y', 30)
                .style("text-anchor", "end")
                .text('Iteration');
        }
    },
    componentDidMount: function() {
        this.updateAxes({isMount: true});
    },
    componentDidUpdate: function() {
        this.updateAxes({});
    },
    render: function() {
        var height = this.props.height - this.props.margin.top - this.props.margin.bottom,
            transform = "translate(0," + height + ")";
        return <g className="x axis" transform={transform}></g>;
    }
});

var YAxis = React.createClass({
    updateAxes: function() {
        var orient = (this.props.isRight) ? "right" : "left",
            svg = d3.select(this.getDOMNode()),
            yAxis = d3.svg.axis().scale(this.props.y).orient(orient);
        svg.call(yAxis);
    },
    componentDidMount: function() {
        this.updateAxes();
    },
    componentDidUpdate: function() {
        this.updateAxes();
    },
    render: function() {
        if (this.props.isRight) {
            var width = this.props.width - this.props.margin.right - this.props.margin.left;
            var transform = "translate(" + width + " ,0)";
            return <g className="y axis" transform={transform}></g>;
        }
        return <g className="y axis"></g>;
    }
});

var Chart = React.createClass({
    render: function() {
        var attr = "translate(" + this.props.margin.left + "," + this.props.margin.top + ")";
        var yAxisRight = null;
        if (this.props.yAxisRight) {
            yAxisRight = <YAxis y={this.props.yAxisRight} isRight={true} margin={this.props.margin} width={this.props.width} />;
        }
        return (
            <svg onMouseMove={this.props.handleMouseMove}
                 onMouseLeave={this.props.handleMouseOut}
                 width={this.props.width}
                 height={this.props.height}>
                <g transform={attr} ref="el">
                    {this.props.children}
                    <XAxis x={this.props.xAxis}
                           width={this.props.width}
                           height={this.props.height}
                           margin={this.props.margin} />
                    <YAxis y={this.props.yAxis} />
                    {yAxisRight}
                </g>
            </svg>
        );
    }
});

var Line = React.createClass({
    getDefaultProps: function() {
        return {
            path: '',
            color: 'blue',
            width: 1.5
        };
    },

    render: function() {
        return (
            <path d={this.props.path} stroke={this.props.color} strokeWidth={this.props.width} fill="none" />
        );
    }
});

var DataSeries = React.createClass({
    getDefaultProps: function() {
        return {
            data: [],
            interpolate: 'cardinal'
        };
    },

    render: function() {
        var props = this.props,
            yScale = props.yScale,
            xScale = props.xScale,
            path = d3.svg.line()
                .x(function(d) { return xScale(d.x); })
                .y(function(d) { return yScale(d.y); })
                .interpolate(props.interpolate);

        return (
            <Line path={path(props.data)} color={props.color} />
        );
    }
});

var LineChart = React.createClass({
    getDefaultProps: function() {
        return {
            color: "cornflowerblue",
            width: 800,
            height: 300,
            yPadFactor: 0.1,
            margin: {
                top: 20, right: 50, bottom: 30, left: 70
            }
        };
    },

    handleMouseMove: function(dataFull, x, y, yRight, rightYstatsNames, e) {
        var eventX = e.nativeEvent.offsetX || e.nativeEvent.layerX;
        var eventY = e.nativeEvent.offsetY || e.nativeEvent.layerY;
        var nearestPoint, valueY, valueX;
        _.pairs(dataFull).forEach(function(d) {
            var name = d[0], data = d[1];
            var domainX = x.invert(eventX - this.props.margin.left);
            var domainIndexScale = d3.scale.linear()
                .domain([data[0].x, data.slice(-1)[0].x])
                .range([0, data.length - 1]);

            var approximateIndex = Math.round(domainIndexScale(domainX));
            var dataIndex = Math.min(approximateIndex || 0, data.length - 1);
            if (dataIndex < 0) dataIndex = 0;
            var value = data[dataIndex];

            if (_.contains(rightYstatsNames, name)) {
                valueY = yRight(value.y) + this.props.margin.top;
            } else {
                valueY = y(value.y) + this.props.margin.top;
            }
            var distance = Math.sqrt(
                Math.pow(Math.abs(x(value.x) + this.props.margin.left - eventX), 2) +
                Math.pow(Math.abs(valueY - eventY), 2)
            );
            if (!nearestPoint || distance < nearestPoint.distance) {
                valueX = x(value.x) + this.props.margin.left;
                value.name = name;
                nearestPoint = {
                    distance: distance,
                    x: valueX,
                    y: valueY,
                    value: value
                };
            }
        }, this);
        this.props.drawNearestPoint(nearestPoint);
    },

    calculateAxis: function(minX, maxX, minY, maxY, minYRight, maxYRight) {
        var width = this.props.width - this.props.margin.left - this.props.margin.right,
            height = this.props.height - this.props.margin.top - this.props.margin.bottom,
            x = d3.scale.linear().range([0, width]).domain([minX, maxX]),
            y = d3.scale,
            yRight = d3.scale;
        y = (this.props.withLogScale) ? y.log() : y.linear();
        y.range([height, 0]).domain([minY, maxY]);
        if (minYRight !== undefined && maxYRight !== undefined) {
            yRight = (this.props.withLogScale) ? yRight.log() : yRight.linear();
            yRight.range([height, 0]).domain([minYRight, maxYRight]);
        }
        return {x: x, y: y, yRight: yRight};
    },

    render: function() {
        var data = this.props.data,
            yScale,
            rightYstatsNames = this.props.rightYstatsNames || [],
            props = this.props,
            size = { width: this.props.width, height: this.props.height };
        var maxYRight;
        var minYRight;
        var yScaleRight;
        var dataFilteredYLeft = _.flatten(_.pairs(data).filter(function(d) {
                if (rightYstatsNames && _.contains(rightYstatsNames, d[0])) {
                    return false;
                }
                return true;
            }));
        var dataFilteredYRight = _.flatten(_.pairs(data).filter(function(d) {
                if (rightYstatsNames && _.contains(rightYstatsNames, d[0])) {
                    return true;
                }
                return false;
            }));
        // get min and max values and add some padding in case minY=maxY,
        // and so our data doesn't get hidden by the x-axis
        var maxYLeft = d3.max(dataFilteredYLeft, function(d) { return d.y; });
        maxYLeft *= (1 + this.props.yPadFactor);
        var minYLeft = d3.min(dataFilteredYLeft, function(d) { return d.y; });
        minYLeft *= (1 - this.props.yPadFactor);
        var maxX = d3.max(_.flatten(_.values(data)), function(d) { return d.x; });
        var minX = 0;
        var xScale = d3.scale.linear()
            .domain([minX, maxX])
            .range([0, this.props.width - this.props.margin.left - this.props.margin.right]);

        var yScaleLeft = d3.scale;
        yScaleLeft = (this.props.withLogScale) ? yScaleLeft.log() : yScaleLeft.linear();

        yScaleLeft.domain([minYLeft, maxYLeft])
            .range([this.props.height - this.props.margin.top - this.props.margin.bottom, 0]);

        if (dataFilteredYRight.length > 0) {
            maxYRight = d3.max(dataFilteredYRight, function(d) { return d.y; });
            minYRight *= (1 + this.props.yPadFactor);
            minYRight = d3.min(dataFilteredYRight, function(d) { return d.y; });
            minYRight *= (1 - this.props.yPadFactor);
            yScaleRight = d3.scale;
            yScaleRight = (this.props.withLogScale) ? yScaleRight.log() : yScaleRight.linear();

            yScaleRight.domain([minYRight, maxYRight])
                .range([this.props.height - this.props.margin.top - this.props.margin.bottom, 0]);
        }

        var charts = _.pairs(data).map(function(d) {
            if (_.contains(rightYstatsNames, d[0])) {
                yScale = yScaleRight;
            } else {
                yScale = yScaleLeft;
            }
            return <DataSeries key={d[0]} data={d[1]} size={size}
                               xScale={xScale} yScale={yScale}
                               color={this.props.colors(d[0])} />;
        }, this);
        var axis = this.calculateAxis(minX, maxX, minYLeft, maxYLeft, minYRight, maxYRight);
        return (
            <Chart width={this.props.width}
                   height={this.props.height}
                   maxX={maxX}
                   maxY={maxYLeft}
                   minX={minX}
                   minY={minYLeft}
                   margin={this.props.margin}
                   withLogScale={this.props.withLogScale}
                   handleMouseMove={this.handleMouseMove.bind(this, data, axis.x, axis.y, axis.yRight, rightYstatsNames)}
                   handleMouseOut={this.props.handleMouseOut}
                   xAxis={axis.x}
                   yAxis={axis.y}
                   yAxisRight={(rightYstatsNames.length > 0) ? axis.yRight : undefined} >
                {charts}
            </Chart>
        );
     }
});

var TrainStatChart = React.createClass({
    getInitialState: function() {
        var state = {};
        if (this.props.withLogScale) {
            state.isLogScale = true;
        }
        this.props.statsNames.forEach(function(name) {
            state[name] = true;
        }, this);
        return state;
    },

    toggleScale: function() {
        this.setState({isLogScale: !this.state.isLogScale});
    },

    toggleChart: function(name, e) {
        var update = {};
        update[name] = e.target.checked;
        this.setState(update);
    },

    drawNearestPoint: function(nearestPoint) {
        this.setState({
            isMouseOver: true,
            mousePointX: nearestPoint.x,
            mousePointY: nearestPoint.y,
            mouseValue: nearestPoint.value
        });
    },

    handleMouseOut: function() {
        this.setState({isMouseOver: false});
    },

    render: function() {
        var logScale = null, data = {}, controls = [], line = null, style, mousePoint = null;
        if (this.props.withLogScale) {
            logScale = (
                <label>
                    <input type="checkbox" checked={this.state.isLogScale} onChange={this.toggleScale} />
                    Log scale
                </label>
            );
        }

        this.props.statsNames.forEach(function(name) {
            if (this.state[name]) {
                data[name] = this.props.data
                    .filter(function(d) { return d[name] !== undefined; })
                    .map(function(d) { return {x: d.iteration, y: d[name]}; });
            }
            if (!this.props.noControls) {
                style = {color: this.props.colors(name)};
                controls.push(<label key={name} style={style}><input type="checkbox" checked={this.state[name]} onChange={this.toggleChart.bind(this, name)}/> {getHumanName(name)}</label>);
            }
        }, this);
        if (_.keys(data).length > 0) {
            line = <LineChart
                    width={this.props.width}
                    height={this.props.height}
                    data={data}
                    withLogScale={this.state.isLogScale}
                    colors={this.props.colors}
                    drawNearestPoint={this.drawNearestPoint}
                    handleMouseOut={this.handleMouseOut}
                    rightYstatsNames={this.props.rightYstatsNames}
                    />;
        }
        if (this.state.isMouseOver) {
            mousePoint = (
                <div className="detail" style={{left: this.state.mousePointX}} >
                    <div className="item active" style={{"top": this.state.mousePointY}} >
                        {getHumanName(this.state.mouseValue.name) + ': ' + this.state.mouseValue.y.toFixed(4)}
                    </div>
                    <div className="dot active" style={{"top": this.state.mousePointY}} />
                </div>
            );
        }

        return (
            <div className="chart-box">
                <div className="chart-header">
                    <h4>{this.props.chartName}</h4>
                    {logScale} {controls}
                </div>
                <div className="graph">
                    {line}
                    {mousePoint}
                </div>
            </div>
        );
    }
});

module.exports = TrainStatChart;
