/** @jsx React.DOM */
/* global React */
/* global d3 */

"use strict";


var Chart = React.createClass({
    render: function() {
        return (
            <svg width={this.props.width} height={this.props.height}>
                {this.props.children}
            </svg>
            );
        }
    });


var Bar = React.createClass({
    getDefaultProps: function() {
        return {
            width: 0,
            height: 0,
            offset: 0
            };
        },

    tooltipCreate: function(e) {
        var samples = this.props.tooltipData[0] !== undefined ? 'Samples: ' + this.props.tooltipData[0] : '',
            bins = this.props.tooltipData[1] ? 'Bin: ' + this.props.tooltipData[1] : '';

        if (this.props.tooltip) {
            $(e.target).tooltip({
                placement: 'bottom',
                container: 'body',
                title: samples + '<br>' + bins
            });
        }
    },

    tooltipDestroy: function(e) {
        if (this.props.tooltip) {
            $(e.target).tooltip('destroy');
        }
    },

    render: function() {
        return (
            <rect fill={this.props.color}
                  width={this.props.width} height={this.props.height}
                  x={this.props.offset} y={this.props.availableHeight - this.props.height}
                  tooltip={this.props.tooltip}
                  tooltipData={this.props.tooltipData}
                  onMouseEnter={this.tooltipCreate}
                  onMouseLeave={this.tooltipDestroy}
                  data-html={this.props.tooltip ? 'true' : ''}
                  data-toggle={this.props.tooltip ? 'tooltip' : ''} />
            );
        }
    });


var DataSeries = React.createClass({
    getDefaultProps: function() {
        return {
            title: '',
            data: []
            };
        },

    render: function() {
        var props = this.props;
        var colorLen = this.props.colors.length;

        var yScale = d3.scale.linear()
          .domain([0, d3.max(this.props.data)])
          .range([0, this.props.height]);

        var xScale = d3.scale.ordinal()
          .domain(d3.range(this.props.data.length))
          .rangeRoundBands([0, this.props.width], 0.05);

        // maybe this mapping works, maybe we have to require underscore library
        var bars = this.props.data.map(function(point, i) {
            var samples = props.tooltipData[0] ? props.tooltipData[0][i] : undefined,
                bins = props.tooltipData[1] ? props.tooltipData[1] : undefined,
                binsInterval = bins ? bins[i] + ' - ' + bins[i+1] : '';
            return (
                <Bar height={yScale(point)} width={xScale.rangeBand()} offset={xScale(i)}
                     availableHeight={props.height} color={props.colors[i % colorLen]} key={i}
                     tooltip={props.tooltip} tooltipData={[samples, binsInterval]} />
                );
            });

        return (
            <g>{bars}</g>
            );
        }
    });


var BarChart = React.createClass({
    render: function() {
        return (
            <Chart width={this.props.width} height={this.props.height}>
                <DataSeries data={this.props.data} width={this.props.width}
                            height={this.props.height} colors={this.props.colors}
                            tooltip={this.props.tooltip} tooltipData={this.props.tooltipData} />
            </Chart>
            );
        }
    });


module.exports = {
    barchart: BarChart
};
