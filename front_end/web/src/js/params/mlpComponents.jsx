/** @jsx React.DOM */
/* global React */

"use strict";

var ParamsComponents = require('./Components.jsx'),
    ParamInput = ParamsComponents.input,
    ParamSlider = ParamsComponents.slider,
    ParamSwitch = ParamsComponents.switch,
    ParamCheckbox = ParamsComponents.checkbox,
    Bootstrap = require('../bootstrap.jsx'),
    Utils = require('../Utils.js'),
    BootstrapButton = Bootstrap.Button;


var MLPLayer = React.createClass({
    render: function() {
        var model = this.props.model,
            errors = this.props.model.validate() || {},
            init = null,
            switch_uniform = null;
        
        if (this.props.model.get('switch_uniform_init')) {
            init = <ParamInput key={"irange"} label={"Range of uniform initialization"} model={model} errors={errors} />;
        } else {
            init = <ParamSlider key={"sparse_init"} label={"Initial sparseness"} help={"This defines the percentage of incoming weights per neuron that are non-zero at initialization. If you're not sure, leave it at 10%."} model={model} errors={errors} />;
        }
        if (this.props.model.get('out_nonlin') != 'LINEARGAUSSIAN')
            switch_uniform = <ParamSwitch key={"switch_uniform_init"} label={"Uniform initialization"} model={model} errors={errors} />;

        return (
            <div>
                <div className="layer-heading clearfix">
                    <BootstrapButton className="btn btn-mini btn-danger pull-right" href="#" onClick={this.props.handleDeleteLayer}>
                       <i className={"icon icon-white icon-remove"} />
                       Delete Layer
                    </BootstrapButton>
                    <h4 className="select-item">MLP Layer: <em>{this.props.key}</em></h4>
                </div>
                <table className="table-params">
                    <tbody>
                        <ParamInput key={"dim"} label={"Number of hidden units"} model={model} errors={errors} placeholder={200} />
                        {switch_uniform}
                        {init}
                    </tbody>
                </table>
            </div>
        );
    }
});

var MaxoutLayer = React.createClass({
    render: function() {
        var model = this.props.model,
            errors = this.props.model.validate() || {},
            init = null;
        if (this.props.model.get('switch_uniform_init')) {
            init = <ParamInput key={"irange"} label={"Range of uniform initialization"} model={model} errors={errors} placeholder={0.005}/>;
        } else {
            init = <ParamSlider key={"sparse_init"} label={"Initial sparseness"} help={"This defines the percentage of incoming weights per neuron that are non-zero at initialization. If you're not sure, leave it at 10%."} model={model} errors={errors} />;
        }
        return (
            <div>
                <div className="layer-heading clearfix">
                    <BootstrapButton className="btn btn-mini btn-danger pull-right" href="#" onClick={this.props.handleDeleteLayer}>
                       <i className={"icon icon-white icon-remove"} />
                       Delete Layer
                    </BootstrapButton>
                    <h4 className="select-item">Maxout Layer: <em>{this.props.key}</em></h4>
                </div>
                <table className="table-params">
                    <tbody>
                        <ParamInput key={"num_units"} label={"Number of hidden units"} model={model} errors={errors} placeholder={240} />
                        <ParamInput key={"num_pieces"} label={"Number of pieces"} model={model} errors={errors} placeholder={2} />
                        <ParamInput key={"max_col_norm"} label={"Max column norm"} model={model} errors={errors} placeholder={1.9365} />
                        <ParamSwitch key={"switch_uniform_init"} label={"Uniform initialization"} model={model} errors={errors} />
                        {init}
                    </tbody>
                </table>
            </div>
        );
    }
});

var MaxoutConvLayer = React.createClass({
    render: function() {
        var model = this.props.model,
            errors = this.props.model.validate() || {};
        return (
            <div>
                <div className="layer-heading clearfix">
                    <BootstrapButton className="btn btn-mini btn-danger pull-right" href="#" onClick={this.props.handleDeleteLayer}>
                       <i className={"icon icon-white icon-remove"} />
                       Delete Layer
                    </BootstrapButton>
                    <h4 className="select-item">Maxout Layer: <em>{this.props.key}</em></h4>
                </div>
                <table className="table-params">
                    <tbody>
                        <ParamInput key={"num_units"} label={"Number of hidden units"} model={model} errors={errors} placeholder={48} />
                        <ParamInput key={"num_pieces"} label={"Number of pieces"} model={model} errors={errors} placeholder={2} />
                        <ParamInput key={"kernel_shape"} label={"Kernel shape"} model={model} errors={errors} placeholder={8} />
                        <ParamInput key={"pool_shape"} label={"Pool shape"} model={model} errors={errors} placeholder={4} />
                        <ParamInput key={"pad"} label={"Padding"} model={model} errors={errors} placeholder={0} />
                        <ParamInput key={"pool_stride"} label={"Pool stride"} model={model} errors={errors} placeholder={2} />
                        <ParamInput key={"max_kernel_norm"} label={"Max kernel norm"} model={model} errors={errors} placeholder={0.9} />
                        <ParamInput key={"irange"} label={"Range of uniform initialization"} model={model} errors={errors} placeholder={0.005} />
                    </tbody>
                </table>
            </div>
        );
    }
});

var LayersList = React.createClass({
    addLayer: function(e) {
        e.preventDefault();
        this.props.layers.add([this.props.model.getDefaultLayer()]);
    },

    deleteLayer: function(i, e) {
        e.preventDefault();
        this.props.layers.remove(this.props.layers.at(i));
    },

    render: function() {
        var modelName = this.props.model.get('model_name'),
            layers = this.props.layers.map(function(layer, i) {
                if (modelName === 'MLP_MAXOUT_CONV') {
                    return <MaxoutConvLayer model={layer} key={'h' + i} handleDeleteLayer={this.deleteLayer.bind(this, i)}/>;
                } else if (modelName === 'MLP_MAXOUT') {
                    return <MaxoutLayer model={layer} key={'h' + i} handleDeleteLayer={this.deleteLayer.bind(this, i)}/>;
                } else {
                    return <MLPLayer model={layer} key={'h' + i} handleDeleteLayer={this.deleteLayer.bind(this, i)}/>;
                }
            }, this);
        if (layers.length === 0) {
            layers = <div className="settings-error"><p>Add at least one layer</p></div>;
        }
        return (
            <div className="layer-params">
                <BootstrapButton className="btn btn-mini btn-success pull-right" href="#" onClick={this.addLayer} >
                   <i className={"icon icon-white icon-plus"} />
                   Add Layer
                </BootstrapButton>
                <h2>Layer params</h2>
                {layers}
            </div>
        );
    }
});

var LearningRateComponent = React.createClass({
    render: function() {
        var model = this.props.model, errors = this.props.model.validate() || {}, component = null;
        if (!model.get('constant')) {
            component = [
                <ParamInput key={"final"} label={"final learning rate"} model={model} errors={errors} placeholder={0.01} />,
                <ParamInput key={"decay_factor"} label={"divide learning rate by this after each GD step"} model={model} errors={errors} placeholder={1.00004} />
            ];
        }
        return (
            <div>
                <table className="table-params">
                    <tbody>
                        <ParamInput key={"init"} label={"initial learning rate"} model={model} errors={errors} placeholder={0.1} />
                        <ParamCheckbox key={"constant"} label={"use constant learning rate"} model={model} errors={errors} />
                        {component}
                    </tbody>
                </table>
            </div>
        );
    }
});

var MomentumComponent = React.createClass({
    render: function() {
        var model = this.props.model, errors = this.props.model.validate() || {}, component = null;
        if (!model.get('constant')) {
            component = [
                <ParamInput key={"final"} label={"final momentum"} model={model} errors={errors} placeholder={0.95} />,
                <ParamInput key={"start"} label={"start increase momentum on this iteration"} model={model} errors={errors} placeholder={1} />,
                <ParamInput key={"stop"} label={"on this iteration momentum will take it's final value"} model={model} errors={errors} placeholder={20} />
            ];
        }
        return (
            <div>
                <table className="table-params">
                    <tbody>
                        <ParamInput key={"init"} label={"initial momentum"} model={model} errors={errors} placeholder={0.5} />
                        <ParamCheckbox key={"constant"} label={"use constant momentum"} model={model} errors={errors} />
                        {component}
                    </tbody>
                </table>
            </div>
        );
    }

});

var MLPComponent = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return [this.props.model];
    },

    render: function() {
        var model = this.props.model,
            errors = this.props.model.validate() || {},
            dropout = null;
        if (this.props.withDropout) {
            dropout = <ParamCheckbox key={"dropout"} label={"use dropout?"} model={model} errors={errors}/>;
        }
        return (
            <div>
                <h4 className="select-item text-center">Model params</h4>
                <div >
                    <table className="table-params">
                        <tbody>
                            <ParamInput key={"maxnum_iter"} label={"number of iterations"} model={model} errors={errors}/>
                            <ParamInput key={"batch_size"} label={"size of batches"} model={model} errors={errors}/>
                            <ParamSlider key={"percent_batches_per_iter"} label={'number of batches to proccess per iteration'} model={model}/>
                            {dropout}
                        </tbody>
                    </table>
                </div>
                <LearningRateComponent model={this.props.model.learningRateModel} />
                <MomentumComponent model={this.props.model.momentumModel} />
                <LayersList layers={this.props.model.layers} model={this.props.model}/>
            </div>
        );
    }
});

module.exports = {
    mlp: MLPComponent
};
