/** @jsx React.DOM */
/* global React */

"use strict";

var ParamsComponents = require('./Components.jsx');
var ParamInput = ParamsComponents.input;
var ParamSlider = ParamsComponents.slider;
var ParamSwitch = ParamsComponents.switch;
var ParamCheckbox = ParamsComponents.checkbox;
var Bootstrap = require('../bootstrap.jsx');
var BootstrapButton = Bootstrap.Button;
var Utils = require('../Utils.js');


var ConvLayerComponent = React.createClass({
    render: function() {
        var model = this.props.model;
        var errors = this.props.model.validate() || {};
        // Styling Note: Instead of having delete buttons inside of h4 tag, should probably set h4 elems to inline-block. Goal is to get delete button
        // on the same line.
        return (
            <div>
                <div>
                    <div className="layer-heading clearfix">
                        <h4 className="select-item">Convolutional Layer: <em>{this.props.key}</em>
                            <BootstrapButton className="btn btn-mini btn-danger pull-right" href="#" onClick={this.props.handleDelete}>Delete</BootstrapButton>
                        </h4>

                    </div>
                    <table className="table-params">
                        <tbody>
                            <ParamInput key={"convChannels"} label={this.props.model.labels.convChannels} model={model} errors={errors} placeholder={3}/>
                            <ParamInput key={"convFilters"} label={this.props.model.labels.convFilters} model={model} errors={errors} placeholder={32}/>
                            <ParamInput key={"convFilterSize"} label={this.props.model.labels.convFilterSize} model={model} errors={errors} placeholder={5}/>
                            <ParamInput key={"convSharedBiases"} label={this.props.model.labels.convSharedBiases} model={model} errors={errors} placeholder={1}/>
                            <ParamInput key={"convDropout"} label={this.props.model.labels.convDropout} model={model} errors={errors} placeholder={0.5}/>
                        </tbody>
                    </table>
                </div>
                <div>
                    <div className="layer-heading clearfix">
                        <h4 className="select-item">Pool Layer: <em>{this.props.key}</em></h4>
                    </div>
                    <table className="table-params">
                        <tbody>
                            <ParamInput key={"poolStart"} label={this.props.model.labels.poolStart} model={model} errors={errors} placeholder={0}/>
                            <ParamInput key={"poolSizeX"} label={this.props.model.labels.poolSizeX} model={model} errors={errors} placeholder={3}/>
                            <ParamInput key={"poolStride"} label={this.props.model.labels.poolStride} model={model} errors={errors} placeholder={2}/>
                            <ParamInput key={"poolOutputsX"} label={this.props.model.labels.poolOutputsX} model={model} errors={errors} placeholder={0}/>
                        </tbody>
                    </table>
                </div>
                <div>
                    <div className="layer-heading clearfix">
                        <h4 className="select-item">Normalization Layer: <em>{this.props.key}</em></h4>
                    </div>
                    <table className="table-params">
                        <tbody>
                            <ParamInput key={"normSize"} label={this.props.model.labels.normSize} model={model} errors={errors} placeholder={3}/>
                        </tbody>
                    </table>
                </div>
            </div>
        );
    }
});


var FCLayerComponent = React.createClass({
    render: function() {
        var model = this.props.model;
        var errors = this.props.model.validate() || {};
        return (
            <div>
                <div className="layer-heading clearfix">
                    <h4 className="select-item">FC Layer: <em>{this.props.key}</em>
                <BootstrapButton className="btn btn-mini btn-danger pull-right" href="#" onClick={this.props.handleDelete}>Delete</BootstrapButton>
                    </h4>
                </div>
                <table className="table-params">
                    <tbody>
                    </tbody>
                </table>
            </div>
        );
    }
});


var LayersComponent = React.createClass({
    clickDelete: function(model) {
        this.props.layers.remove(model);
    },

    addConvSetLayer: function(e) {
        e.preventDefault();
        var defaultConv = this.props.layers.getDefaultConvSetLayer();
        this.props.layers.add([defaultConv]);
        //this.props.layers.add([this.props.layers.getDefaultConvSetLayer()]);
    },

    addFCLayer: function(e) {
        e.preventDefault();
        var defaultFC = this.props.layers.getDefaultFCLayer();
        this.props.layers.add([defaultFC]);
        //this.props.layers.add([this.props.layers.getDefaultFCLayer()]);
    },

    render: function() {
        var layersList = this.props.layers.map(function(layer, i) {
            if (layer.get('type') === 'convSet') {
                return <ConvLayerComponent model={layer} key={'layer' + i} handleDelete={this.clickDelete.bind(this, layer)}/>;
            }
            return <FCLayerComponent model={layer}  key={'layer' + i} handleDelete={this.clickDelete.bind(this, layer)}/>;
        }, this);
        return (
            <div className="layer-params">
                <BootstrapButton className="btn btn-mini btn-success pull-right" href="#" onClick={this.addConvSetLayer}>
                    <i className={"icon icon-white icon-plus"}/>
                    Add Conv Layer
                </BootstrapButton>
                <BootstrapButton className="btn btn-mini btn-sccess pull-right" href="#" onClick={this.addFCLayer}>
                    <i className={"icon icon-white icon-plus"}/>
                    Add FC Layer
                </BootstrapButton>
                <h2>Layer params</h2>
                {layersList}
            </div>
        );
    }
});

var CONVComponent = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return [this.props.model];
    },

    render: function() {
        var model = this.props.model, errors = this.props.model.validate() || {};
        return (
            <div>
                <h4 className="select-item text-center">Model params </h4>
                <div >
                    <table className="table-params">
                        <tbody>
                            <ParamInput key={"maxnum_iter"} label={"number of iterations"} model={model} errors={errors}/>
                            <ParamInput key={"img_size"} label={"image size"} help={"must be a multiple of 8"} model={model} errors={errors}/>
                            <ParamInput key={"dropout"} label={"dropout"} model={model} errors={errors} placeholder={0.5}/>
                            <ParamInput key={"learning_rate_init"} label={"learning rate"} model={model} errors={errors} placeholder={0.001}/>
                            <ParamInput key={"momentum_init"} label={"momentum"} model={model} errors={errors} placeholder={0.5}/>
                            <ParamCheckbox key={"random_sparse"} label={"Use random sparse layers"} model={model} errors={errors}/>
                        </tbody>
                    </table>
                </div>
                <LayersComponent layers={this.props.model.layers} />
            </div>
        );
    }
});

module.exports = CONVComponent;
