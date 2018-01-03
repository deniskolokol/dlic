/** @jsx React.DOM */
/* global Humanize */
/* global React */
/* global initTour */
/* global flexboxHack */
/* global _ */

"use strict";


var Utils = require('./Utils.js'),
    DatasetWizard = require('./DatasetWizardComponents.jsx'),
    Bootstrap = require('./bootstrap.jsx'),
    FileInfo = DatasetWizard.FileInfo,
    MetaData = DatasetWizard.MetaData,
    BootstrapSelect = Bootstrap.SimpleSelect,
    BootstrapAlert = Bootstrap.Alert;

var StatusPanel = React.createClass({
    render: function() {
        var df = this.props.df;
        return (
            <div className="panel panel-secondary">
                <div className="panel-heading">
                    <h2>Data information</h2>
                </div>
                <div className="panel-body">
                    <FileInfo df={df} status={df.get('state')} />
                    <MetaData df={df} />
                </div>
            </div>
        );
    }
});

var TimeseriesModels = React.createClass({
    tooltipCreate: function(e) {
        $(e.target).tooltip({
            placement: 'bottom',
            container: 'body',
            delay: 200,
            title: this.props.title
        });
    },

    tooltipDestroy: function(e) {
        $(e.target).tooltip('destroy');
    },

    render: function() {
        return (
            <div className="filters">
                <a href="#" onClick={this.props.handleClick.bind(null, 'MRNN')}
                            onMouseEnter={this.tooltipCreate}
                            onMouseLeave={this.tooltipDestroy}
                            data-toggle="tooltip"
                            title='An MRNN is a special type of Recurrent Neural
                                   Network that has "Multiplicative" units. It
                                   is optimized using a method called Hessian Free
                                   Optimization as opposed to the more normally used
                                   Stochastic Gradient Descent. This particular model
                                   is very useful for time series problems &ndash; In fact,
                                   it is only used for time series problems. If you have
                                   time series data, this is the model you should choose.'>MRNN</a>
            </div>
        );
    }
});

var GeneralModels = React.createClass({
    tooltipCreate: function(e) {
        $(e.target).tooltip({
            placement: 'bottom',
            container: 'body',
            delay: 200,
            title: this.props.title
        });
    },

    tooltipDestroy: function(e) {
        $(e.target).tooltip('destroy');
    },

    render: function() {
        return (
            <div className="filters">
                <a href="#" onClick={this.props.handleClick.bind(null, 'DEEPNET')}
                            onMouseEnter={this.tooltipCreate}
                            onMouseLeave={this.tooltipDestroy}
                            data-toggle="tooltip"
                            title="This is a standard feed forward neural network,
                                   also known as a Multilayer Perceptron (MLP) and
                                   a Deep Neural Network (DNN). If your data has
                                   labels and you are going to predict values with
                                   your model, you should choose this one.">DeepNet</a>
                <a href="#" onClick={this.props.handleClick.bind(null, 'AUTOENCODER')}
                            onMouseEnter={this.tooltipCreate}
                            onMouseLeave={this.tooltipDestroy}
                            data-toggle="tooltip"
                            title="An autoencoder is a type of unsupervised neural network.
                                   If your data is unlabeled and you are looking to perform
                                   dimensionality reduction or feature extraction, you should
                                   use this. You can think of it as a more powerful PCA">Autoencoder</a>
                <a href="#" onClick={this.props.handleClick.bind(null, 'TSNE')}
                            onMouseEnter={this.tooltipCreate}
                            onMouseLeave={this.tooltipDestroy}
                            data-toggle="tooltip"
                            title="t-Distributed Stochastic Neighbor Embedding is a nonlinear
                                   dimensionality reduction technique useful for visualizing
                                   high-dimensional data in two or three dimensions.">T-SNE</a>
            </div>
        );
    }
});

var ImagesModels = React.createClass({
    tooltipCreate: function(e) {
        $(e.target).tooltip({
            placement: 'bottom',
            container: 'body',
            delay: 200,
            title: this.props.title
        });
    },

    tooltipDestroy: function(e) {
        $(e.target).tooltip('destroy');
    },

    render: function() {
        return (
            <div className="filters">
                <a href="#" onClick={this.props.handleClick.bind(null, 'CONV')}
                            onMouseEnter={this.tooltipCreate}
                            onMouseLeave={this.tooltipDestroy}
                            data-toggle="tooltip"
                            title='A Convolutional Neural Network (CNN) is a special
                                   type of neural network used specifically for image
                                   problems. It differs from normal neural networks in several
                                   ways. Specifically: it consists of an input (your images),
                                   a set of "convolutional/pooling/normalization" block layers,
                                   a set of standard neural network layers, and an output layer.
                                   Bottom line: If you have image problems, try the convolutional
                                   neural network. They are state of the art.'>Convolutional</a>
            </div>
        );
    }
});

var SelectModelStep = React.createClass({
    handleClick: function(modelName, e) {
        e.preventDefault();
        this.props.wizard.selectModel(modelName);
    },

    render: function() {
        var df = this.props.df,
            file_format = df.get('file_format'),
            component = null;
        switch(file_format) {
            case 'TIMESERIES':
                component = <TimeseriesModels handleClick={this.handleClick} />;
                break;
            case 'GENERAL':
                component = <GeneralModels handleClick={this.handleClick} />;
                break;
            case 'IMAGES':
                component = <ImagesModels handleClick={this.handleClick} />;
                break;
            default:
                component = <div></div>;
        }
        return (
            <div className="panel-body-step">
                <div className="panel-body-step1">
                    <p className="intro-text">
                        Based on the dataset you&rsquo;ve selected, the following models are available to you:
                    </p>
                    {component}
                    <div className="filters-apply">
                        <div>Choose model</div>
                    </div>
                </div>
            </div>
        );
    }
});

var MrnnSetup = React.createClass({
    mixins: [Utils.TrainTestDatasetMixin],

    getInitialState: function() {
        return {
            numTimesteps: '',
            nonlinVal: 0,
            trainDataset: this.getDefaultTrainDatasetId(),
            testDataset: this.getDefaultTestDatasetId()
        };
    },
    handleOnChangeNonlin: function(e) {
        this.setState({nonlinVal: e.target.value});
    },
    handleOnChangeTestDataset: function(e) {
        this.setState({testDataset: e.target.value});
    },
    handleOnChangeTrainDataset: function(e) {
        this.setState({trainDataset: e.target.value});
    },
    handleOnChangeNumTimesteps: function(e) {
        this.setState({numTimesteps: e.target.value});
    },
    render: function() {
        var datasets = this.props.datasets,
            nonlin = [
                [0, 'Softmax'],
                [1, 'Sigmoid'],
                [2, 'Sigmoid w/ MSE loss'],
                [3, 'Linear w/ MSE loss']
            ];
        return (
            <div>
                <div className="row-fluid">
                    <div className="span6">
                        <h4 className="select-item">Train set</h4>
                        <BootstrapSelect value={this.state.trainDataset} values={datasets} handleChange={this.handleOnChangeTrainDataset}/>
                    </div>
                    <div className="span6">
                        <h4 className="select-item">Test set</h4>
                        <BootstrapSelect value={this.state.testDataset} values={datasets} handleChange={this.handleOnChangeTestDataset}/>
                    </div>
                </div>
                <div className="divider"></div>
                <h4 className="select-item">Nonlinearity</h4>
                <BootstrapSelect value={this.state.nonlinVal} values={nonlin} handleChange={this.handleOnChangeNonlin}/>
                <div className="divider"></div>
                <h4 className="select-item">Number of timesteps to use</h4>
                <input value={this.state.numTimesteps} onChange={this.handleOnChangeNumTimesteps} placeholder={"Leave blank for all timesteps"} className="input-dark input-center" />
            </div>
        );
    }
});

var ConvSetup = React.createClass({
    mixins: [Utils.TrainTestDatasetMixin],

    getInitialState: function() {
        return {
            trainDataset: this.getDefaultTrainDatasetId(),
            testDataset: this.getDefaultTestDatasetId()
        };
    },
    handleOnChangeTestDataset: function(e) {
        this.setState({testDataset: e.target.value});
    },
    handleOnChangeTrainDataset: function(e) {
        this.setState({trainDataset: e.target.value});
    },
    render: function() {
        var datasets = this.props.datasets;
        return (
            <div>
                <div className="row-fluid">
                    <div className="span6">
                        <h4 className="select-item">Train set</h4>
                        <BootstrapSelect value={this.state.trainDataset} values={datasets} handleChange={this.handleOnChangeTrainDataset}/>
                    </div>
                    <div className="span6">
                        <h4 className="select-item">Test set</h4>
                        <BootstrapSelect value={this.state.testDataset} values={datasets} handleChange={this.handleOnChangeTestDataset}/>
                    </div>
                </div>
            </div>
        );
    }
});

var AutoencoderSetup = React.createClass({
    mixins: [Utils.TrainTestDatasetMixin],

    getInitialState: function() {
        return {
            trainDataset: this.getDefaultTrainDatasetId(),
        };
    },
    handleOnChangeTrainDataset: function(e) {
        this.setState({trainDataset: e.target.value});
    },
    render: function() {
        var datasets = this.props.datasets;
        return (
            <div>
                <h4 className="select-item">Train set</h4>
                <BootstrapSelect value={this.state.trainDataset} values={datasets} handleChange={this.handleOnChangeTrainDataset}/>
            </div>
        );
    }
});

var TSNESetup = React.createClass({
    mixins: [Utils.TrainTestDatasetMixin],

    getInitialState: function() {
        return {
            trainDataset: this.getDefaultTrainDatasetId(),
        };
    },
    handleOnChangeTrainDataset: function(e) {
        this.setState({trainDataset: e.target.value});
    },
    render: function() {
        var datasets = this.props.datasets;
        return (
            <div>
                <h4 className="select-item">Select train set</h4>
                <BootstrapSelect value={this.state.trainDataset} values={datasets} handleChange={this.handleOnChangeTrainDataset}/>
            </div>
        );
    }
});

var DeepnetSetup = React.createClass({
    mixins: [Utils.TrainTestDatasetMixin],

    getInitialState: function() {
        var outputNonlinOptions = this.getOutputNonlinOptions();
        return {
            nonlinVal: "MLP_RECTIFIED",
            outputNonlinVal: outputNonlinOptions[0] && outputNonlinOptions[0][0],
            trainDataset: this.getDefaultTrainDatasetId(),
            testDataset: this.getDefaultTestDatasetId()
        };
    },
    handleOnChangeNonlin: function(e) {
        this.setState({nonlinVal: e.target.value});
    },
    handleOnChangeTasks: function(e) {
        this.setState({outputNonlinVal: e.target.value});
    },
    handleOnChangeTestDataset: function(e) {
        this.setState({testDataset: e.target.value});
    },
    handleOnChangeTrainDataset: function(e) {
        this.setState({trainDataset: e.target.value});
    },
    getOutputNonlinOptions: function() {
        var meta = this.props.df.get('meta'),
            options = [];
        if (meta.last_column_info.unique > 200) {
            options = [
                ['LINEARGAUSSIAN', 'Regression']
            ];
        } else if (meta.dtypes[meta.dtypes.length - 1] === 's') {
            options = [
                ['SOFTMAX', 'Classification']
            ];
        } else {
            options = [
                ['SOFTMAX', 'Classification'],
                ['LINEARGAUSSIAN', 'Regression']
            ];
        }
        return options;
    },
    render: function() {
        var datasets = this.props.datasets,
            outputNonlinOptions = this.getOutputNonlinOptions(),
            nonlin = [
                ['MLP_RECTIFIED', 'Rectified Linear'],
                ['MLP_SIGMOID', 'Sigmoid'],
                ['MLP_MAXOUT', 'Maxout'],
                ['MLP_MAXOUT_CONV', 'Maxout Convolutional']
            ];

        return (
            <div>
                <div className="row-fluid">
                    <div className="span6">
                        <h4 className="select-item">Train set</h4>
                        <BootstrapSelect value={this.state.trainDataset} values={datasets} handleChange={this.handleOnChangeTrainDataset}/>
                    </div>
                    <div className="span6">
                        <h4 className="select-item">Test set</h4>
                        <BootstrapSelect value={this.state.testDataset} values={datasets} handleChange={this.handleOnChangeTestDataset}/>
                    </div>
                </div>
                <div className="divider"></div>
                <div className="row-fluid">
                    <div className="span6">
                        <h4 className="select-item">Activation function</h4>
                        <BootstrapSelect value={this.state.nonlinVal} values={nonlin} handleChange={this.handleOnChangeNonlin}/>
                    </div>
                    <div className="span6">
                        <h4 className="select-item">Task</h4>
                        <BootstrapSelect value={this.state.outputNonlinVal} values={outputNonlinOptions} handleChange={this.handleOnChangeTasks}/>
                    </div>
                </div>
            </div>
        );
    }
});

var SetupModelStep = React.createClass({
    handleClick: function(e) {
        e.preventDefault();
        var wizard = this.props.wizard;
        wizard.set({'currentNonlin': this.refs.setup.state.nonlinVal, 'currentNumTimesteps': this.refs.setup.state.numTimesteps, 'currentTestDataset': this.refs.setup.state.testDataset, 'currentTrainDataset': this.refs.setup.state.trainDataset, 'currentOutputNonlin': this.refs.setup.state.outputNonlinVal});
        wizard.selectModelSetup();
    },

    handleBackClick: function(e) {
        e.preventDefault();
        var datasetId = this.props.wizard.get('dataFile').id,
            url = "ensemble-wizard/" + datasetId + '/step/model-select/';
        this.props.wizard.router.navigate(url, {trigger: true});
        flexboxHack();
    },

    render: function() {
        var wizard = this.props.wizard, dfs = this.props.dfs,
            df = this.props.df, component = null, datasets,
            currentModel = wizard.get('currentModel'),
            cmp, next = null, back = null;
        datasets = dfs.where({file_format: df.get('file_format')})
            .filter(function(val) {
                cmp = Utils.compareMetaData(df.get('meta'), val.get('meta'));
                return cmp && !val.isTimeseriesWithoutOutput() && df.id != val.id;
            }).map(function(val) {
                return val.get('datasets');
            });
        datasets.unshift(df.get('datasets'));
        datasets = _.flatten(datasets)
            .filter(function(d) {
               if (currentModel === 'DEEPNET') {
                   return d.last_column_is_output;
               }
               return true;
            }).map(function(d) { return [d.id, d.name]; });
        if (datasets.length > 0) {
            switch(currentModel) {
                case 'MRNN':
                    component = <MrnnSetup ref="setup" datasets={datasets} />;
                    break;
                case 'CONV':
                    component = <ConvSetup ref="setup" datasets={datasets} />;
                    break;
                case 'DEEPNET':
                    component = <DeepnetSetup ref="setup" datasets={datasets} df={df} />;
                    break;
                case 'TSNE':
                    component = <TSNESetup ref="setup" datasets={datasets} />;
                    break;
                case 'AUTOENCODER':
                    component = <AutoencoderSetup ref="setup" datasets={datasets} />;
                    break;
            }
            back = (
                <a href="#" className="filter-finish" onClick={this.handleBackClick}>
                    <i className="icon icon-white icon-chevron-left"></i>
                    Back
                </a>
            );
            next = (
                <a href="#" className="filter-finish" onClick={this.handleClick}>
                    Next step
                    <i className="icon icon-white icon-chevron-right"></i>
                </a>
            );
        } else {
            next = <div>{"You need a test dataset. Create it first."}</div>;
        }
        return (
            <div className="panel-body-step">
                <div className="panel-body-step1">
                    <div className="text-center">
                        {component}
                        {back} {next}
                    </div>
                </div>
            </div>
        );
    }
});

var ParamsStep = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return this.props.wizard.get('model').getBackboneModels();
    },

    getInitialState: function() {
        return {advanced: false};
    },
    handleBackClick: function(e) {
        e.preventDefault();
        var datasetId = this.props.wizard.get('dataFile').id,
            url = "ensemble-wizard/" + datasetId + '/step/model-setup/';
        this.props.wizard.router.navigate(url, {trigger: true});
        flexboxHack();
    },
    handleAdvanced: function(e) {
        e.preventDefault();
        this.setState({advanced: true});
    },
    handleFinish: function(options, e) {
        this.props.wizard.finish(options);
    },
    render: function() {
        var paramsComponent, finish = null;
        var back = (
            <a href="#" className="filter-finish" onClick={this.handleBackClick}>
                <i className="icon icon-white icon-chevron-left"></i>
                Back
            </a>
        );

        if (this.state.advanced) {
            paramsComponent = this.props.wizard.get('model').getComponent();
            var isValid = this.props.wizard.get('model').isParamsValid();
            if (isValid) {
                finish = (
                    <a href="#" className="filter-finish" onClick={this.handleFinish}>
                        <i className="icon icon-white icon-flag"></i>
                        Finish
                    </a>
                );
            }
            return (
                <div>
                    {paramsComponent}
                    <div className="simple-finish">
                        {back} {finish}
                    </div>
                </div>
            );
        } else {
            return (
                <div>
                    <div className="hyperparams-step">
                        <h4>Time to choose your model hyperparameters...</h4>
                        <p>Would you like us to intelligently choose them for you?</p>
                        <p>Or would you like to choose them yourself? (advanced)</p>
                        <a href="#" className="filter-finish" onClick={this.handleFinish.bind(this, {start: true})}>
                            CHOOSE FOR ME
                        </a>
                        <a href="#" className="filter-finish" onClick={this.handleAdvanced}>
                            LET ME DO IT <small>(I&rsquo;m a professional...)</small>
                        </a>
                        <div className="clear">{back}</div>
                    </div>
                </div>
            );
        }
    }
});

var ActionPanel = React.createClass({
    render: function() {
        var wizard = this.props.wizard, component = null, header = null;
        switch(wizard.get('currentStep')) {
            case 'model-select':
                component = <SelectModelStep df={this.props.df} wizard={this.props.wizard}/>;
                header = <h2>Select Model</h2>;
                break;
            case 'model-setup':
                component = <SetupModelStep df={this.props.df} wizard={this.props.wizard} dfs={this.props.dfs}/>;
                header = <h2>Setup {Humanize.capitalize(wizard.get('currentModel').toLowerCase())}</h2>;
                break;
            case 'model-params':
                component = <ParamsStep df={this.props.df} wizard={this.props.wizard} />;
                header = <h2>Setup {Humanize.capitalize(wizard.get('currentModel').toLowerCase())}</h2>;
                break;
        }
        return (
            <div className="panel panel-primary panel-blue">
                <div className="panel-heading">
                    {header}
                </div>
                <div className="panel-body">
                    {component}
                </div>
            </div>
        );
    }
});

var ResultPanel = React.createClass({
    resetClick: function() {
        this.props.wizard.resetAllFilters();
    },
    render: function() {
        var wizard = this.props.wizard, stepsClasses = '';
        if (wizard.get('currentStep') === 'model-select') {
            stepsClasses = 'step step1';
        } else if (wizard.get('currentStep') === 'model-setup') {
            stepsClasses = 'step step2';
        } else if (wizard.get('currentStep') === 'model-params') {
            stepsClasses = 'step step3';
        }

        return (
            <div className="panel panel-secondary panel-blue">
                <div className="panel-heading">
                    <h2>Steps</h2>
                </div>
                <div className="panel-body">
                    <ul className="steps-completed">
                        <li>Completed wizard steps:</li>
                        <li className={stepsClasses}>
                            <i className="icon icon-white"></i>
                            <strong>Step #1:</strong> Select a model
                        </li>
                        <li className={stepsClasses}>
                            <i className="icon icon-white"></i>
                            <strong>Step #2:</strong> Select data sets for training
                        </li>
                        <li className={stepsClasses}>
                            <i className="icon icon-white"></i>
                            <strong>Step #3:</strong> Set params for your model
                        </li>
                    </ul>
                </div>
            </div>
        );
    }
});

var WizardNotes = React.createClass({
    getInitialState: function() {
        return {show: true};
    },
    showAlert: function() {
        this.setState({show: true});
    },
    closeAlert: function() {
        $(this).hide();
        this.setState({show: false});
    },
    render: function() {
        var wizard = this.props.wizard, message = '', alert = null;

        /*jshint multistr: true */
        if (wizard.get('currentStep') === 'model-select') {
            message = "In order to train a model, you'll need to select a model \
                        architecture that's compatible with the data you've provided. \
                        If you're not sure, it's OK to click on any of them &mdash; they are \
                        all compatible with your data.";
        } else if (wizard.get('currentStep') === 'model-setup') {
            message = "It's important to set aside some of your data for \"testing\" \
                        and \"validation\". These are both used to test the reliability of your \
                        results &mdash; even though a model might learn your data perfectly, \
                        it doesn't matter if it doesn't work on unseen examples.";
        } else if (wizard.get('currentStep') === 'model-params') {
            message = "Hyperparameters are settings that must be set for a model to train \
                        correctly. For instance, \"learning rate\" is a common parameter that \
                        controls the \"speed of learning\" &mdash; note, faster is not always better... \
                        <br><br> \
                        To make things less complicated, we provide functionality that chooses \
                        good parameters for you by training several different models. \
                        <br><br> \
                        If you are not familiar with deep learning, we suggest letting us pick \
                        them for you...";
        }

        if (this.state.show) {
            alert = <BootstrapAlert message={message} type="wizard" handleClose={this.closeAlert} />;
        } else {
            alert = (
                <a href="#" className="show-wizard-help" onClick={this.showAlert}>
                    <i className="icon icon-white icon-info-sign"></i> Show help messages
                </a>
            );
        }

        return (
            <div>{alert}</div>
        );
    }
});

var WizardRoot = React.createClass({
    componentDidMount: function() {
        initTour();
    },

    render: function() {
        var df = this.props.wizard.get('dataFile');
        return (
            <div>
                <a href="/dashboard/" className="btn btn-mini btn-info btn-wizard-back">
                    <i className="icon icon-white icon-chevron-left"></i>
                    Back to Dashboard
                </a>
                <div className="wizad-messages">
                    <WizardNotes df={df} wizard={this.props.wizard} />
                </div>
                <div className="wizard wizard-ensembles clearfix">
                    <StatusPanel df={df} />
                    <ActionPanel df={df} wizard={this.props.wizard} dfs={this.props.dfs}/>
                    <ResultPanel df={df} wizard={this.props.wizard} />
                </div>
            </div>
        );
    }
});

module.exports = {
    WizardRoot: WizardRoot,
};
