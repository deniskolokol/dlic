/** @jsx React.DOM */
/* global React */
/* global _ */

"use strict";
var Utils = require('../Utils');
var DataProjector = require('data-projector-integrated');

var toolbarStyle = {
   position: "absolute",
   paddingTop: "15px",
   paddingLeft: "10px",
   top: "10px",
   left: "10px",
   width: "100%",
   textAlign: "left",
   zIndex: "100",
   display: "block"
}

var menuWrapperStyle = {
   position: "absolute",
   marginLeft: "10px",
   padding: "6px",
   top: "100px",
   left: "10px",
   width: "auto",
   //backgroundColor: "rgba(127,127,127,0.35)",
   //border: "1px solid #7f7f7f",
   //borderRadius: "4px",
   //WebkitBorderRadius: "4px",
   //MozBorderRadius: "4px",
   textAlign: "left",
   zIndex: "101",
}

var menuStyle = {
   display:"block",
   color: "#808080",
   fontWeight: "bold",
   cursor: "pointer",
}

var infoStyle = {
   "position": "absolute",
   //"padding": "5px",
   top: "20px",
   padding: "6px",
   marginRight: "10px",
   right: "10px",
   width: "20%",
   //backgroundColor: "rgba(127,127,127,0.35)",
   //border: "1px solid #7f7f7f",
   //borderRadius: "4px",
   //WebkitBorderRadius: "4px",
   //MozBorderRadius: "4px",
   textAlign: "left",
   zIndex: "100",
   display:"block"
}

var buttonStyle = {
    color: "#808080",
    fontWeight: "bold",
    cursor: "pointer",
    paddingLeft: "0.6em"
}


var appStyle = {
   "color": "#909090",
   "font-family": "monospace",
   fontSize: "0.9em",
   "text-align": "center",
   //padding: "2px",
   //"overflow": "hidden"
}

var containerStyle = {
    background: "#000000",
    border: "2px solid #000000",
    borderRadius: "8px",
    WebkitBorderRadius: "10px",
    MozBorderRadius: "10px",
}

var noWebglModalStyle = {
    display: "none",
    position: "absolute",
    top: "40%",
    left: "50%",
}

var noWebglModalTextStyle = {
    position: "relative",
    left: "-50%",
    zIndex: "10000",
    background: "rgba(50,50,50,0.9)",
    border: "1px solid white",
    color: "#bbbbbb",
    lineHeight: "1.4em",
    padding: "0.5em",
    paddingLeft: "1.5em",
    paddingRight: "1.5em",
    fontSize: "1.5em",
}

var toolbarHeader = {
    textAlign: "right"
}


var VisualizationScatterplot3 = React.createClass({
    getDefaultProps: function() {
        return {
            margin: { top: 20, right: 15, bottom: 60, left: 60 },
            //width: { 0.9 * $('.tabs-pane').width() },
            //height: { 500 -
        };
    },

    render: function() {
        var points = null, props = this.props;
        var margin = props.margin;
        var width = 0.8 * $('.tabs-pane').width();
        var height = 600 - margin.top - margin.bottom;
        containerStyle = containerStyle || {};
        containerStyle.height = height;
        return (
            <div id="dataprojector" style={appStyle}>
                <div id="toolbar" style={toolbarStyle}>
                    <table>
                        <tr>
                            <td style={toolbarHeader}>
                               Camera:
                            </td>
                            <td>
                               <span style={buttonStyle} class="button" id="perspectiveButton">Perspective</span>
                               <span style={buttonStyle} class="button" id="orthographicButton">Orthographic</span>
                            </td>
                        </tr>
                        <tr>
                            <td style={toolbarHeader}>
                               View:
                            </td>
                            <td>
                                <span style={buttonStyle} class="button" id="viewTopButton">Top</span>
                                <span style={buttonStyle} class="button" id="viewFrontButton">Front</span>
                                <span style={buttonStyle} class="button" id="viewSideButton">Side</span>
                            </td>
                        </tr>
                        <tr>
                            <td style={toolbarHeader}>
                               Animate:
                            </td>
                            <td>
                               <span style={buttonStyle} class="button" id="spinRightButton">Rotate</span>
                               <span style={buttonStyle} class="button" id="animateButton">Classes</span>
                            </td>
                        </tr>
                    </table>
                </div>

                <div id="menuwrapper" style={menuWrapperStyle}>
                    -- Data --<br/>
                    <div id="menu" style={menuStyle}>
                        <span class="toggle" id="toggleAll">[+]</span><span class="button" id="buttonAll"> All</span><br/>
                    </div>
                </div>

                <div id="info" style={infoStyle}>
                   -- Console --<br/><br/>
                   <span id="message"></span><br/>
                </div>

                <div id="no-webgl-modal" style={noWebglModalStyle}>
                    <div id="no-webgl-modal-text" style={noWebglModalTextStyle}>
                        <p>This browser / device does not support WebGL which is required to visualize 3D data.</p>
                    </div>
                </div>

                <div id="container" style={containerStyle}>

                </div>

                <div id="screenshots">
                </div>

            </div>
        );
    },

    componentDidMount: function() {
        //this.props;
        var points = null, props = this.props;
        var datastr = this.props.model.attributes.model_params.tsne_output;
        var data = datastr ? JSON.parse(datastr) : [];
        data.forEach(function(item) {
            if (item.length == 3) { item.splice(2,0,0.0) };
        });
        var dataProjector = new DataProjector();
        dataProjector.storage.injectCSV(data);

    }
});






module.exports = VisualizationScatterplot3;
