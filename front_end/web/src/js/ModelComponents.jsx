/** @jsx React.DOM */
/* global React */
/* global d3 */

"use strict";

var Utils = require('./Utils'),
    TrainStatChart = require('./graphs/StatCharts.jsx'),
    AccuracyMatrixTable = require('./graphs/AccuracyMatrix.jsx'),
    VisualizationScatterplot2D = require('./graphs/TSNEVis_2D.jsx'),
    VisualizationScatterplot3D = require('./graphs/TSNEVis_3D.jsx'),
    CM = require('./graphs/ConfusionMatrix.jsx'),
    ConfusionMatrixChart = CM.ConfusionMatrixChart,
    SmallConfusionMatrix = CM.SmallConfusionMatrix,
    cx = React.addons.classSet,
    Bootstrap = require('./bootstrap.jsx'),
    BootstrapModal = Bootstrap.Modal,
    BootstrapAlert = Bootstrap.AlertList;


var ModelHyperparamsTab = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return this.props.params.getBackboneModels();
    },


    handleFinish: function(e) {
        e.preventDefault();
        this.props.model.applyModelSettings();
        this.refs.alert.addAlert("Parameters were successfully applied for this model", 'success', 8000);
    },

    render: function() {
        var paramsComponent = this.props.params.getComponent(),
    isValid = this.props.params.isParamsValid(),
    finish = null;
    if (isValid) {
        finish = (
            <div className="simple-finish">
                <a href="#" className="filter-finish filter-finish-blue" onClick={this.handleFinish}>
                    <i className="icon icon-white icon-flag"></i>
                    Apply
                </a>
            </div>
            );
    }

    var applied = (
            <BootstrapAlert
                ref="alert"
                models={[]}>
            </BootstrapAlert>);

    return (
            <div>
                {paramsComponent}
                <div className="params-alert"></div>
                {applied}
                {finish}
            </div>
           );
    }
});


var ModelHead = React.createClass({
    mixins: [Utils.BackboneEventMixin],
    getBackboneEvents: function() {
        var props = this.props;
        return {
            "change": props.model,
            "change remove add": props.model.stats
        };
    },

    render: function() {
        var iters = null, accuracy = null, model = this.props.model, stat;
        if (model.stats.length > 0) {
            stat = model.stats.last();
            iters = <div><strong>Iterations:</strong> {stat.get('iteration')}</div>;
            if (model.get('model_name') === 'AUTOENCODER') {
                accuracy = <div><strong>Cost:</strong> {stat.getCost()}</div>;
            } else if (model.get('model_name') === 'TSNE') {
                accuracy = <div><strong>Error:</strong> {stat.getError()}</div>;
            } else {
                accuracy = <div><strong>Test/Train:</strong> {stat.getTestAccuracy()}% / {stat.getTrainAccuracy()}%</div>;
            }
        } else {
            iters = <div><strong>Iterations:</strong> 0</div>;
        }
        var modelID = (
            <div>
                <strong>Model ID:</strong> {model.id}
            </div>
        );
        return (
            <li onClick={this.props.handleClick} className={(this.props.isSelected) ? "active" : ""}>
                {this.props.isSelected ? <i className="icon icon-white icon-chevron-right"></i> : ''}
                <h4 className="model-list-item">{(model.get('name')) ? model.get('name') : "Model " + model.id }</h4>
                {(model.get('name')) ? modelID : null }
                <div><strong>Net:</strong> {this.props.ensemble.modelNames[this.props.model.get('model_name')]}</div>
                {iters}
                {accuracy}
            </li>
        );
    }
});

var ModelTitle = React.createClass({
    getInitialState: function() {
        return { inputText: this.props.model.get('name') };
    },

    openDeleteModal: function(e) {
        e.preventDefault();
        this.refs.deleteModal.open();
    },

    closeDeleteModal: function() {
        this.refs.deleteModal.close();
    },

    handleDelete: function(model) {
        this.props.ensemble.deleteModel(model);
        this.closeDeleteModal();
    },

    openRenameModal: function(e) {
        e.preventDefault();
        this.refs.renameModal.open();
    },

    closeRenameModal: function() {
        this.refs.renameModal.close();
    },

    handleRename: function(newName) {
        this.props.model.rename(newName);
        this.closeRenameModal();
    },

    onChange: function(e) {
        this.setState({inputText: e.target.value});
    },

    handlePrevNextBtn: function(model, e) {
        e.preventDefault();
        this.props.handleSelectModel(model);
    },

    render: function() {
        var model = this.props.model,
            renameBtn = null,
            deleteBtn = null,
            prevBtn = null,
            nextBtn = null,
            hasPrev = this.props.previousModel !== undefined,
            hasNext = this.props.nextModel !== undefined;
        if (model.allowDelete()) {
            deleteBtn = (
                <button onClick={this.openDeleteModal} className="btn btn-mini btn-danger btn-delete">
                    <i className="icon icon-white icon-remove"></i> Delete
                </button>
            );
        }

        prevBtn = (
            <a href="#" className="btn btn-info"
               onClick={(hasPrev) ? this.handlePrevNextBtn.bind(this, this.props.previousModel) : ""}
               disabled={!hasPrev}>
                <i className="icon icon-white icon-chevron-left"></i> Previous
            </a>
        );
        nextBtn = (
            <a href="#" className="btn btn-info"
               onClick={(hasNext) ? this.handlePrevNextBtn.bind(this, this.props.nextModel) : ""}
               disabled={!hasNext}>
                 Next <i className="icon icon-white icon-chevron-right"></i>
            </a>
        );
        renameBtn = (
            <a href="#" onClick={this.openRenameModal} className="btn btn-mini btn-info btn-rename">
                <i className="icon icon-white icon-pencil"></i> Rename
            </a>
        );
        return (
            <div className="model-title clearfix">
                <div className="pull-left">
                    <h2>{(model.get('name')) ? model.get('name') : "Model " + this.props.id }</h2>
                    {renameBtn} {deleteBtn}
                </div>
                <div className="model-paging">
                    {prevBtn} {nextBtn}
                </div>
                <BootstrapModal
                  ref="deleteModal"
                  confirm="Delete"
                  cancel="Cancel"
                  confirmButtonClass="btn-danger"
                  onCancel={this.closeDeleteModal}
                  onConfirm={this.handleDelete.bind(this, model)}
                  title={"Delete model #" + this.props.id} >
                      <p>If you delete this model, you will no longer have access to it and it will be removed permanently.</p>
                </BootstrapModal>
                <BootstrapModal
                  ref="renameModal"
                  classes="modal-mini"
                  confirm="Rename"
                  cancel="Cancel"
                  confirmButtonClass="btn-success"
                  onCancel={this.closeRenameModal}
                  onConfirm={this.handleRename.bind(this, this.state.inputText)}
                  title={"Rename model #" + this.props.id} >
                      <p>Please provide new model name:</p>
                      <input type="text" onChange={this.onChange} value={this.state.inputText} className="rename-input" />
                </BootstrapModal>
            </div>
        );
    }
});

var ModelActions = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return [this.props.model.stats];
    },

    getInitialState: function() {
        return {selectedIter: undefined};
    },

    handleIterChange: function(e) {
        this.setState({selectedIter: e.target.value});
    },

    handleResume: function() {
        this.props.model.resume(this.state.selectedIter);
    },

    handleRestart: function() {
        this.props.model.restart();
    },

    handleFinalize: function() {
        this.props.model.finalize();
    },

    render: function() {
        var select = null, options, iter, selectedIter,
            model = this.props.model, resumeBtn = null, restartBtn = null,
            finalizeBtn = null, stopBtn = null, startBtn = null;
        if (this.props.ensemble.onWorker()) {
            return <div className="model-actions"></div>;
        }
        if (model.get('model_name') === "MRNN" && model.allowResume()) {
            options = this.props.model.stats.map(function(stat) {
                iter = stat.get('iteration');
                return <option key={iter} value={iter}>{iter}</option>;
            });
            options.reverse();
            selectedIter = (this.state.selectedIter) ? this.state.selectedIter : this.props.model.stats.last().get('iteration');
            select = <select onChange={this.handleIterChange} value={selectedIter}>{options}</select>;
        }
        if (model.allowStart()) {
            startBtn = (
                <button onClick={this.handleRestart} className="btn btn-info">
                    <i className="icon icon-white icon-play"></i> Start
                </button>
            );
        }
        if (model.allowResume()) {
            resumeBtn = (
                <button onClick={this.handleResume} className="btn btn-info">
                    <i className="icon icon-white icon-play"></i> Resume
                </button>
            );
        }
        if (model.allowRestart()) {
            restartBtn = (
                <button onClick={this.handleRestart} className="btn btn-info">
                    <i className="icon icon-white icon-refresh"></i> Restart
                </button>
            );
        }
        if (model.allowStop()) {
            stopBtn = (
                <button className="btn btn-info">
                    <i className="icon icon-white icon-stop"></i> Stop
                </button>
            );
        }
        if (model.allowFinalize()) {
            finalizeBtn = (
                <button onClick={this.handleFinalize} className="btn btn-info">
                    <i className="icon icon-white icon-flag"></i> Finalize
                </button>
            );
        }

        return (
            <div className="model-actions">
                <div className="input-append">
                    {select}{resumeBtn}{startBtn}{stopBtn}{restartBtn}{finalizeBtn}
                </div>
            </div>
        );
    }
});

var ModelProgress = React.createClass({
    mixins: [Utils.BackboneEventMixin],

    getBackboneEvents: function() {
        return {
            'add change remove': this.props.stats,
            'change': this.props.params
        };
    },

    render: function() {
        var props = this.props,
            classes = cx({
                "progress": true,
                "progress-striped": true,
                "active": props.isActive
            });
        var currentIter = 0;
        if (props.stats.length > 0) {
            currentIter = props.stats.last().get('iteration');
        }
        var maxIter = props.params.get('maxnum_iter');
        return (
            <div className="model-progress">
                <strong className="upper">Progress:</strong>
                <div className={classes}>
                    <div className="bar" style={{width: (currentIter / maxIter * 100) + "%"}}>
                        <p>{currentIter}/{maxIter}</p>
                    </div>
                </div>
            </div>
        );
    }
});

var ModelMainTab = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return [this.props.stats];
    },

    render: function() {
        var stats = this.props.stats,
            smallConfMatrix = null,
            props = this.props,
            classes = cx({
                'label': true,
                'label-info': props.modelState === 'TRAIN',
                'label-success': props.modelState === 'FINISHED',
                'label-warning': props.modelState === 'CANCELED',
                'label-important': props.modelState === 'ERROR'
            }),
            stateName = props.humanStateNames[props.modelState],
            lastIterInfo = null, chartTrain = null, chartTest = null,
            stat, data, colors, statsNames;
	    var logstab = <LogsTab logs={this.props.model.get('training_logs')} />;
        if (stats.length > 0) {
            stat = stats.last();
            colors = d3.scale.category20();
            data = stats.getDataForCharts();
            if (props.showSmallConfusionMatrix) {
                smallConfMatrix = (
                    <div>
                        <h4>Confusion Matrix (test)</h4>
                        <SmallConfusionMatrix stats={stats}/>
                    </div>
                );
            }
            if (props.modelName === 'AUTOENCODER') {
                statsNames = ['train_cost'];
                colors.domain(statsNames);
                chartTrain = <TrainStatChart chartName={"Cost"} data={data} statsNames={statsNames} colors={colors} noControls={true} width={500} height={200}/>;
                lastIterInfo = (
                    <div>
                        <b>Last iteration:</b> {stat.get('iteration')}
                        <br /><b>Cost:</b> {stat.getCost()}
                    </div>
                );
            } else if (props.modelName === 'TSNE') {
                statsNames = ['error', 'gradient_norm'];
                colors.domain(statsNames);
                chartTrain = <TrainStatChart key={1} chartName={"Error"} data={data} statsNames={['error']} colors={colors} noControls={true} width={500} height={200}/>;
                chartTest = <TrainStatChart key={2} chartName={"Gradient Norm"} data={data} statsNames={['gradient_norm']} colors={colors} noControls={true} width={500} height={200}/>;
                lastIterInfo = (
                    <div>
                        <b>Last iteration:</b> {stat.get('iteration')}
                        <br/><b>Error:</b> {stat.getError()}
                    </div>
                );
            } else {
                statsNames = ['train_accuracy', 'test_accuracy'];
                colors.domain(statsNames);
                chartTrain = <TrainStatChart chartName={"Train/Test Accuracy"} data={data} statsNames={['train_accuracy', 'test_accuracy']} colors={colors} noControls={true} width={500} height={200}/>;
                chartTest = <TrainStatChart chartName={"Train/Test Loss"} data={data} statsNames={['test_loss', 'train_loss']} colors={colors} noControls={true} width={500} height={200}/>;
                lastIterInfo = (
                    <div>
                        <b>Last iteration:</b> {stat.get('iteration')}
                        <br /><b>Test accuracy:</b> {stat.getTestAccuracy()}%
                        <br /><b>Train accuracy:</b> {stat.getTrainAccuracy()}%
                    </div>
                );
            }
        }
        return (
            <div className="row-fluid">
                <div className="model-status span5">
                    <strong>Model name:</strong> {props.humanModelNames[props.modelName]}
                    <br /><strong>Training time:</strong> {Utils.secondsToStr(props.trainingTime)}
                    <br /><strong>Job status:</strong> <span className={classes}> {stateName}</span>
                    {lastIterInfo}
                    <div className="model-conf-matrix">
                        {smallConfMatrix}
                    </div>
                </div>
                <div className="model-charts span7">
                    {chartTrain}
                    {chartTest}
                </div>
                <div className="clearboth"></div>
                {logstab}
            </div>
        );
    }
});

var ModelChartsTab = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return [this.props.stats];
    },

    render: function() {
        var colors = d3.scale.category20(),
            props = this.props,
            stats = this.props.stats,
            data, statsNames, charts = [];
        if (stats.length === 0) {
            return <div>No stats</div>;
        }
        data = stats.getDataForCharts();
        if (props.modelName === 'AUTOENCODER') {
            statsNames = ['train_cost'];
            colors.domain(statsNames);
            charts = [
                <TrainStatChart key={1} chartName={"Cost"} data={data} statsNames={statsNames} colors={colors} withLogScale={true}/>
            ];
        } else if (props.modelName === 'TSNE') {
            statsNames = ['error', 'gradient_norm'];
            colors.domain(statsNames);
            charts = [
                <TrainStatChart key={1} chartName={"Error"} data={data} statsNames={['error']} colors={colors}/>,
                <TrainStatChart key={2} chartName={"Gradient Norm"} data={data} statsNames={['gradient_norm']} colors={colors}/>
            ];
        } else if (props.modelName === 'CONV') {
            statsNames = ['train_accuracy', 'test_accuracy', 'train_loss', 'test_loss'];
            colors.domain(statsNames);
            charts = [
                <TrainStatChart key={1} chartName={"Accuracy"} data={data} statsNames={['train_accuracy', 'test_accuracy']} colors={colors}/>,
                <TrainStatChart key={2} chartName={"Loss"} data={data} statsNames={['train_loss', 'test_loss']} colors={colors} withLogScale={true}/>
            ];
        } else if (props.modelName === 'MRNN') {
            statsNames = ['train_accuracy', 'test_accuracy', 'train_loss', 'test_loss', 'grad1', 'grad2', 'mu', 'lambda', '1_h_norm', 'h_f_norm', 'f_h_norm', '1_f_norm', 'v_h_norm', 'v_f_norm', 'h_o_norm'];
            colors.domain(statsNames);
            charts = [
                <TrainStatChart key={1} chartName={"Accuracy"} data={data} statsNames={['train_accuracy', 'test_accuracy']} colors={colors}/>,
                <TrainStatChart key={2} chartName={"Loss"} data={data} statsNames={['train_loss', 'test_loss']} colors={colors} withLogScale={true}/>,
                <TrainStatChart key={3} chartName={"Gradients"} data={data} statsNames={['grad1', 'grad2']} colors={colors} withLogScale={true}/>,
                <TrainStatChart key={4} chartName={"Damping Values"} data={data} statsNames={['mu', 'lambda']} colors={colors} withLogScale={true}/>,
                <TrainStatChart key={5} chartName={"Conjugate Gradient Statistics"} data={data} statsNames={['total_num_cg', 'rho', 'norm_CG_x']} colors={colors} rightYstatsNames={['total_num_cg']} withLogScale={true}/>,
                <TrainStatChart key={6} chartName={"Weights Norm"} data={data} statsNames={['1_h_norm', 'h_f_norm', 'f_h_norm', '1_f_norm', 'v_h_norm', 'v_f_norm', 'h_o_norm']} colors={colors}/>,
            ];
        } else {
            statsNames = ['train_accuracy', 'test_accuracy', 'train_loss', 'test_loss', 'learning_rate', 'momentum', 'last_layer_row_norms_mean', 'last_layer_col_norms_mean', 'iteration_time'];
            colors.domain(statsNames);
            charts = [
                <TrainStatChart key={1} chartName={"Accuracy"} data={data} statsNames={['train_accuracy', 'test_accuracy']} colors={colors}/>,
                <TrainStatChart key={2} chartName={"Loss"} data={data} statsNames={['train_loss', 'test_loss']} colors={colors} withLogScale={true}/>,
                <TrainStatChart key={3} chartName={"Hyperparams"} data={data} statsNames={['learning_rate', 'momentum']} colors={colors}/>,
                <TrainStatChart key={4} chartName={"Weights Norm"} data={data} statsNames={['last_layer_row_norms_mean', 'last_layer_col_norms_mean']} colors={colors}/>,
                <TrainStatChart key={5} chartName={"Time"} data={data} statsNames={['iteration_time']} colors={colors}/>
            ];
        }
        return (
            <div>
                {charts}
            </div>
        );
    }
});

var ModelConfusionMatrixTab = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return [this.props.stats];
    },


    getInitialState: function() {
        return {groupByPredict: true};
    },

    handleChangeGroupBy: function(e) {
        this.setState({groupByPredict: e.target.checked});
    },

    handleChangeIteration: function(e) {
        this.setState({selectedIter: parseInt(e.target.value, 10)});
    },

    getSelectedIteration: function(stats) {
        if (this.state.selectedIter !== undefined) {
            return this.state.selectedIter;
        }
        return stats.last().get('iteration');
    },

    render: function() {
        var select = null, options = null,
            props = this.props,
            stats = props.stats,
            stat, selectedIter, testMatrix, trainMatrix,
            testChart = null, trainChart = null;
        if (stats.length === 0) {
            return <div>No data</div>;
        }
        selectedIter = this.getSelectedIteration(stats);
        stat = stats.findWhere({'iteration': selectedIter});
        testMatrix = stat.get('confusion_matrix');
        testChart = <ConfusionMatrixChart
                        stat={stat}
                        matrix={testMatrix}
                        groupByPredict={this.state.groupByPredict}
                        name='Test set'
                        width={800}
                        height={600} />;
        trainMatrix = stat.get('confusion_matrix_train');
        if (trainMatrix !== undefined) {
            trainChart = <ConfusionMatrixChart
                            stat={stat}
                            matrix={trainMatrix}
                            groupByPredict={this.state.groupByPredict}
                            name='Training set'
                            width={800}
                            height={600} />;
        }
        if (props.modelName === 'MRNN') {
            options = stats.map(function(stat) {
                return <option key={stat.get('iteration')}
                               value={stat.get('iteration')}>
                           {stat.get('iteration')}
                       </option>;
            });
            options.reverse();
            select = (
                <select value={selectedIter}
                        onChange={this.handleChangeIteration}>
                    {options}
                </select>
            );
        }
        return (
            <div>
            {select}
                <label>
                    <input type="checkbox"
                           checked={this.state.groupByPredict}
                           onChange={this.handleChangeGroupBy} />
                    group by predict
                </label>
                {testChart}
                {trainChart}
            </div>
        );
    }
});

var ModelAccuracyMatrixTab = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return [this.props.stats];
    },

    render: function() {
        return <AccuracyMatrixTable stats={this.props.stats} />;
    }
});

var LogsTab = React.createClass({
    shouldComponentUpdate: function(nextProps, nextState) {
        // only update the logs if the incoming is longer
        // than the existing, this happens because while logs
        // are being pushed via websocket, the model also gets polled
        // which might contain shorter logs due to polling delay.
        return (nextProps.logs || '').length > (this.props.logs || '').length;
    },

    componentDidUpdate: function() {
        var logstab = this.getDOMNode();
        //var newScrollHeight = logstab.scrollHeight;
        //logstab.scrollTop = logstab.scrollHeight;
        $(logstab).animate({scrollTop: logstab.scrollHeight}, 1500);
    },

    render: function() {
        return (
            <div ref="modelLogs" className="model-logs">
                <pre ref="logsBody">{this.props.logs}</pre>
            </div>
        )
    }
});

var ModelVisualizationTab = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return [this.props.model.stats];
    },

    render: function() {
        var tsne_output = [];
        if (this.props.model.attributes.model_params.tsne_output) {
            tsne_output = JSON.parse(this.props.model.attributes.model_params.tsne_output);
        };
        var dimension = (tsne_output && tsne_output[0] && tsne_output[0].length) - 1;
        if (dimension === 2) {
            return <VisualizationScatterplot2D model={this.props.model}/>;
        } else if (dimension === 3) {
            return <VisualizationScatterplot3D model={this.props.model}/>;
        } else {
            return <p>Press "Start/Restart" to generate t-SNE data.</p>;
        }

    }
});

var ModelTabs = React.createClass({
    selectTab: function(name) {
        this.props.handleSelectTab(name);
    },

    getMainTab: function() {
        return <ModelMainTab
                modelName={this.props.model.get('model_name')}
                stats={this.props.model.stats}
                modelState={this.props.model.get('state')}
                model={this.props.model}
                trainingTime={this.props.model.get('training_time')}
                showSmallConfusionMatrix={this.props.model.hasConfusionMatrix()}
                humanModelNames={this.props.ensemble.modelNames}
                humanStateNames={this.props.model.stateNames} />;
    },

    render: function() {
        var tab = null, selectedTab = this.props.selectedTab, props = this.props;

        switch (selectedTab) {
            case 'charts':
                tab = <ModelChartsTab modelName={this.props.model.get('model_name')} stats={this.props.model.stats} />;
                break;
            case 'confusion':
                tab = <ModelConfusionMatrixTab modelName={this.props.model.get('model_name')} stats={this.props.model.stats} />;
                break;
            case 'accuracy_matrix':
                tab = <ModelAccuracyMatrixTab stats={this.props.model.stats} />;
                break;
            case 'tsne_visualization':
                tab = <ModelVisualizationTab model={this.props.model} />;
                break;
            case 'hyperparams':
                if (this.props.model.paramModel) {
                    tab = <ModelHyperparamsTab params={this.props.model.paramModel} model={this.props.model}/>;
                } else {
                    tab = this.getMainTab();
                }
                break;
            default:
                tab = this.getMainTab();
        }
        return (
            <div>
                <ul className="tabs">
                    <li className={(selectedTab === 'main') ? "active" : ""} onClick={this.selectTab.bind(this, 'main')}>Status</li>
                    <li className={(selectedTab === 'hyperparams') ? "active" : ""} onClick={this.selectTab.bind(this, 'hyperparams')}>Hyperparams</li>
                    <li className={(selectedTab === 'charts') ? "active" : ""} onClick={this.selectTab.bind(this, 'charts')}>Charts</li>
                    {(this.props.model.hasConfusionMatrix()) ? <li className={(selectedTab === 'confusion') ? "active" : ""} onClick={this.selectTab.bind(this, 'confusion')}>Confusion matrix</li> : ""}
                    {(this.props.model.get('model_name') === 'MRNN') ? <li className={(selectedTab === 'accuracy_matrix') ? "active" : ""} onClick={this.selectTab.bind(this, 'accuracy_matrix')}>Accuracy Matrix</li> : ""}
                    {(this.props.model.get('model_name') === 'TSNE') ? <li className={(selectedTab === 'tsne_visualization') ? "active" : ""} onClick={this.selectTab.bind(this, 'tsne_visualization')}>Visualization</li> : ""}
                </ul>

                <div className="tabs-pane">
                    {tab}
                </div>
            </div>
        );
    }
});

var ModelBody = React.createClass({
    mixins: [Utils.BackboneEventMixin],
    getBackboneEvents: function() {
        var props = this.props;
        return {
            "change": props.model,
        };
    },

    render: function() {
        var progress = null,
            model = this.props.model;
        if (model.isProgressBarVisible()) {
            progress = <ModelProgress stats={model.stats} params={model.paramModel} isActive={this.props.model.get('state') === 'TRAIN'}/>;
        }
        return (
            <div className="span9">
                <ModelTitle id={this.props.model.id} model={this.props.model} ensemble={this.props.ensemble} nextModel={this.props.nextModel} previousModel={this.props.previousModel} handleSelectModel={this.props.handleSelectModel}/>
                <ModelActions model={this.props.model} ensemble={this.props.ensemble} />
                {progress}
                <ModelTabs
                    model={this.props.model}
                    ensemble={this.props.ensemble}
                    selectedTab={this.props.selectedTab}
                    handleSelectTab={this.props.handleSelectTab} />
            </div>
        );
    }
});

module.exports = {
    Head: ModelHead,
    Body: ModelBody
};
