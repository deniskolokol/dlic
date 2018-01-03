/** @jsx React.DOM */
/* global React */

"use strict";

var Utils = require('../Utils.js'),
    Bootstrap = require('../bootstrap.jsx'),
    BootstrapSlider = Bootstrap.Slider;


var ParamSlider = React.createClass({
    onSlide: function(value) {
        this.props.model.set(this.props.key, value);
    },

    render: function() {
        var name = this.props.key;
        return (
            <tr>
                <td><strong>{this.props.label}</strong><br /><span dangerouslySetInnerHTML={{__html: this.props.help}} /></td>
                <td>
                    <BootstrapSlider percentage="true" suffix="%" min={this.props.min} max={this.props.max} step={this.props.step} value={this.props.model.get(name)} handleSlide={this.onSlide} />
                </td>
            </tr>
        );
    }
});


//TODO: use Switch from bootstrap.jsx
var ParamSwitch = React.createClass({
    componentDidMount: function() {
        var rootNode = $(this.getDOMNode()).find('.param-switch');
        rootNode.bootstrapSwitch();
        rootNode.bootstrapSwitch('setState', this.props.model.get(this.props.key), true);
        rootNode.on('switch-change', $.proxy(function(_, data) {
            this.props.model.set(this.props.key, data.value);
        }, this));
    },

    componentWillUnmount: function() {
        $(this.getDOMNode()).find('.param-switch').off('switch-change');
    },

    render: function() {
        return (
            <tr>
                <td>
                    <strong>{this.props.label}</strong><br />
                    <span dangerouslySetInnerHTML={{__html: this.props.help}} />
                </td>
                <td>
                    <div className="switch-mini param-switch" data-on="success" data-off="default">
                        <input type="checkbox" />
                    </div>
                </td>
            </tr>
        );
    }
});


var ParamCheckbox = React.createClass({
    handleChange: function(e) {
        this.props.model.set(this.props.key, e.target.checked);
    },

    render: function() {
        var name = this.props.key, error = this.props.errors[name];
        return (
            <tr>
                <td><strong>{this.props.label}</strong><br /><span dangerouslySetInnerHTML={{__html: this.props.help}} /></td>
                <td>
                    <input type="checkbox" className="input-mini" checked={this.props.model.get(name)} onChange={this.handleChange} />
                    {(error) ? <div className="settings-error">{error}</div> : ''}
                </td>
            </tr>
        );
    }
});

var ParamInput = React.createClass({
    handleChange: function(e) {
        if (Utils.isBlank(e.target.value)) {
            this.props.model.set(this.props.key, '');
        } else {
            this.props.model.set(this.props.key, e.target.value);
        }
    },

    render: function() {
        var name = this.props.key, error = this.props.errors[name],
            labels = this.props.model.labels;
        return (
            <tr>
                <td><strong>{(this.props.label) ? this.props.label : labels[name]}</strong><br /><span dangerouslySetInnerHTML={{__html: this.props.help}} /> </td>
                <td>
                    <input type="text" className="input-dark input-mini" value={this.props.model.get(name)} onChange={this.handleChange} placeholder={this.props.placeholder} />
                    {(error) ? <div className="settings-error">{error}</div> : ''}
                </td>
            </tr>
        );
    }
});

var AutoencoderComponent = React.createClass({
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
                            <ParamInput key={"batch_size"} label={"size of batches"} model={model} errors={errors}/>
                            <ParamInput key={"hidden_outputs"} label={"size of hidden layer"} model={model} errors={errors} placeholder={20}/>
                            <ParamInput key={"noise_level"} label={"noise level"} model={model} errors={errors} placeholder={0.2}/>
                            <ParamInput key={"learning_rate_init"} label={"learning rate"} model={model} errors={errors} placeholder={0.001}/>
                            <ParamInput key={"irange"} label={"Range of uniform initialization"} model={model} errors={errors} placeholder={0.05}/>
                        </tbody>
                    </table>
                </div>
            </div>
        );
    }
});

var TSNEComponent = React.createClass({
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
                            <ParamInput key={"n_components"} label={"target dimensionality"} model={model} errors={errors}/>
                            <ParamInput key={"maxnum_iter"} label={"number of iterations"} model={model} errors={errors}/>
                            <ParamInput key={"perplexity"} label={"perplexity"} model={model} errors={errors}/>
                            <ParamInput key={"early_exaggeration"} label={"early exaggeration"} model={model} errors={errors}/>
                            <ParamInput key={"learning_rate"} label={"learning rate"} model={model} errors={errors}/>
                            <ParamInput key={"init"} label={"initialization"} model={model} errors={errors}/>
                        </tbody>
                    </table>
                </div>
            </div>
        );
    }
});

var MRNNComponent = React.createClass({
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
                            <ParamInput key={"maxnum_iter"} label={"number of iterations"} model={model} errors={errors} placeholder={20}/>
                            <ParamInput key={"h"} label={"number of hidden units"} model={model} errors={errors} placeholder={2}/>
                            <ParamInput key={"f"} label={"number of factored units"} model={model} errors={errors} placeholder={2}/>
                            <ParamInput key={"cg_min_cg"} label={"minimum number of conjugate gradient iterations"} model={model} errors={errors} placeholder={1}/>
                            <ParamInput key={"cg_max_cg"} label={"maximum number of conjugate gradient iterations"} model={model} errors={errors} placeholder={40}/>
                            <ParamInput key={"lambda"} label={"damping parameter lambda"} model={model} errors={errors} placeholder={0.01}/>
                            <ParamInput key={"mu"} label={"damping parameter mu"} model={model} errors={errors} placeholder={0.001}/>
                        </tbody>
                    </table>
                </div>
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
            </div>
        );
    }
});

module.exports = {
    input: ParamInput,
    checkbox: ParamCheckbox,
    slider: ParamSlider,
    switch: ParamSwitch,
    TSNE: TSNEComponent,
    Autoencoder: AutoencoderComponent,
    MRNN: MRNNComponent,
    CONV: CONVComponent
};
