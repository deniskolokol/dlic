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
        var svg = d3.select(this.getDOMNode());
        var yAxis = d3.svg.axis()
                        .scale(this.props.y)
                        .orient("left");
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


function makeColorMap(classes) {
    var defaultcolors = [ 
                            '#5599ff',
                            '#feba55',
                            '#55fe65',
                            '#fe55ed',
                            '#55d1fe',
                            '#fe8254',
                            '#7cfe54',
                            '#d654fe',
                            '#54fef2',
                            '#fd5460',
                            '#b5fd54',
                            '#9c54fd',
                        ];
    var set = _.uniq(classes);
    var colormap = [];
    var usedcolors = [];
    var randcolor = defaultcolors[0];
    var red = '';
    var green = '';
    var blue = '';
    for (var i=0; i<set.length; i++) {
        if (i  < defaultcolors.length) {
            colormap[ set[i] ] = defaultcolors[i];
            // If we run out of default colors, randomly generate more
        } else {
            while ( (usedcolors.indexOf(randcolor)!=-1) || (defaultcolors.indexOf(randcolor)!=-1) ) {
                red = (Math.floor(Math.random() * 155) + 100).toString(16);
                green = (Math.floor(Math.random() * 155) + 100).toString(16);
                blue = (Math.floor(Math.random() * 155) + 100).toString(16);
                randcolor = '#' + red + green + blue;
            }
            colormap[ set[i] ] = randcolor;
            usedcolors.push(randcolor);
        }
    }
    return colormap;
}
    

var VisualizationScatterplot2 = React.createClass({
    getDefaultProps: function() {
        return {
            margin: { top: 20, right: 15, bottom: 60, left: 60 },
            //width: { 0.9 * $('.tabs-pane').width() },
            //height: { 500 - 
        };
    },

    handleSelectPoint: function(e) {
        this.props.handleSelectPoint();
    },

    render: function() {
        //this.props;
        var points = null, props = this.props;
        var datastr = this.props.model.attributes.model_params.tsne_output;
        var data = datastr ? JSON.parse(datastr) : [];
        var xdata = data.map(function(triple) { return triple[0]; });
        var ydata = data.map(function(triple) { return triple[1]; });
        var outputClasses = data.map(function(triple) { return triple[2]; });
        var colorMap = makeColorMap(outputClasses);
        //var newWidth = 85 * props.data.length,
        var margin = props.margin;
        //var width = ( newWidth > props.width ) ? props.width : newWidth;
        //width = width - margin.left - margin.right;
        //var height = props.height - margin.top - margin.bttom;
        var width = 0.8 * $('.tabs-pane').width();
        //var height = 0.8 * $('.tabs-pane').height() - margin.top - margin.bottom;
        var height = 600 - margin.top - margin.bottom;
        //var x = d3.scale.ordinal().rangeRoundBands([0,width], 0.3);
        //var y = d3.scale.linear().range([height,0]);
        var x = d3.scale.linear()
                  .domain([d3.min(xdata), d3.max(xdata)])  // the range of the values to plot
                  .range([ 0, width ]);        // the pixel range of the x-axis
   
        var y = d3.scale.linear()
                  .domain([d3.min(ydata), d3.max(ydata)])
                  .range([ height, 0 ]);

        points = data.map(function(d) {
            return <circle cy={y(d[1])}
                           cx={x(d[0])}
                           r="2" 
                           opacity="1.0"
                           fill={colorMap[d[2]]} />;
        }, this);
        
        return (
            <svg width={width + margin.left + margin.right}
                 height={height + margin.top + margin.bottom}
                 fill="white">
                <g transform={"translate(" + margin.left + "," + margin.top + ")"} >
                    {points}
                    <BarXaxis x={x} height={height} />
                    <BarYaxis y={y} />
                </g>
            </svg>
        );
    }
});

            


        

module.exports = VisualizationScatterplot2;
