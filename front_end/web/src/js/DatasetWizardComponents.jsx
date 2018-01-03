/** @jsx React.DOM */
/* global React */
/* global Humanize */
/* global initTour */
/* global flexboxHack */
/* global getCookie */
/* global launchTour */
/* global _ */


"use strict";
var Utils = require('./Utils');
var Alerts = require('./alerts');
var Bootstrap = require('./bootstrap.jsx');
var BootstrapModal = Bootstrap.Modal;
var columnSelect = require('./filters/columnSelectComponent.jsx');
var outputColumns = columnSelect.outputColumns;

var TimeseriesMetaReact = React.createClass({
    render: function() {
        var meta = this.props.meta,
            df = this.props.df;
        return (
            <ul className="dm-file-meta">
                <li><strong>Available models:</strong> MRNN</li>
                <li><strong>Min Timesteps:</strong> {meta.min_timesteps}</li>
                <li><strong>Max Timesteps:</strong> {meta.max_timesteps}</li>
                <li><strong>Features:</strong> {meta.input_size}</li>
                <li><strong>Outputs:</strong> {meta.output_size}</li>
                <li><strong>Samples:</strong> {Humanize.intComma(meta.data_rows)}</li>
            </ul>
        );
    }
});

var GeneralMetaReact = React.createClass({
    render: function() {
        var meta = this.props.meta, archivePath = null, lastCol, df = this.props.df;
        if (meta.hasOwnProperty('archive_path')) {
            archivePath = <li><strong>File in archive:</strong> {meta.archive_path}</li>;
        }
        if (meta.last_column_info.classes) {
            lastCol = "Last column contains " + Object.keys(meta.last_column_info.classes).length + " classes";
        } else {
            lastCol = "Last column contains more than 200 classes or non-integer values";
        }
        return (
            <ul className="dm-file-meta">
                <li><strong>Available models:</strong> Autoencoder, T-SNE, Deepnets</li>
                <li><strong>Samples:</strong> {Humanize.intComma(meta.data_rows)}</li>
                <li><strong>Columns:</strong> {meta.num_columns}</li>
                <li><strong>Classes:</strong> {lastCol}</li>
                {archivePath}
                <li><strong>Header:</strong> {(meta.with_header) ? "Yes" : "No"}</li>
            </ul>
        );
    }
});

var ImagesMetaReact = React.createClass({
    render: function() {
        var meta = this.props.meta,
            df = this.props.df;
        return (
            <ul className="dm-file-meta">
                <li><strong>Available models:</strong> ConvNet</li>
                <li><strong>Samples:</strong> {Utils.sum(_.values(meta.classes))}</li>
                <li><strong>Classes:</strong> {Object.keys(meta.classes).length}</li>
            </ul>
        );
    }
});

var MetaData = React.createClass({
    render: function() {
        var df = this.props.df, metaData = null, file_format = df.get('file_format');
        if (file_format === 'TIMESERIES') {
            return <TimeseriesMetaReact meta={df.get('meta')} df={df} />;
        } else if (file_format === 'GENERAL') {
            return <GeneralMetaReact meta={df.get('meta')}  df={df} />;
        } else if (file_format === 'IMAGES') {
            return <ImagesMetaReact meta={df.get('meta')} df={df} />;
        } else {
            return <div className="span3"></div>;
        }
    }
});

var FileInfoItem = React.createClass({
    render: function() {
        return (
            <div>
                <i className={"icon icon-white " + this.props.iconClasses}></i>
                <strong>{this.props.label}:</strong><span>{this.props.value}</span>
            </div>
        );
    }
});

var FileInfo = React.createClass({
    render: function() {
        var df = this.props.df;
        var date = Utils.isoDateToHumanize(df.get('created'));
        var fileID = null, fileDate = null, fileSize = null, fileType = null;

        if (this.props.status === 'Ready') {
            fileSize = <li>
                           <FileInfoItem iconClasses="icon-resize-full"
                                         label="File size"
                                         value={Humanize.fileSize(df.get('meta').size ? df.get('meta').size : 0)} />
                       </li>;

            fileType = <li>
                           <FileInfoItem iconClasses="icon-star"
                                         label="Data type"
                                         value={Humanize.capitalize(df.get('file_format').toLowerCase())} />
                       </li>;
        }

        fileID = <li>
                    <FileInfoItem iconClasses="icon-file"
                                     label="ID" value={df.id} />
                </li>;

        fileDate = <li>
                       <FileInfoItem iconClasses="icon-calendar"
                                     label="Date upload"
                                     value={date} />
                   </li>;

        return (
            <ul className="dm-file-meta">
                {fileID}{fileDate}{fileSize}{fileType}
            </ul>
        );
    }
});

var StatusPanel = React.createClass({

    displayOutput: function(){

        },

    drop: function(e){
        var filter = this.props.wizard.getCurrentFilter();
        if(filter && filter.name == "column select")
            this.refs.outputColumns.drop(e);
    },

    render: function() {
        var df = this.props.df;

        var filter = this.props.wizard.getCurrentFilter();

        if(filter && filter.name == "column select")
            return (
                <div className="panel panel-secondary" onDrop={this.drop}>

                    <div className="panel-heading">
                        <h2>Output Columns</h2>
                    </div>
                    <div className="panel-body">
                        <outputColumns ref='outputColumns' filter={filter} wizard={this.props.wizard}/>
                    </div>
                </div>
            );
        else
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

var SelectFilter = React.createClass({
    handleFinish: function(e) {
        e.preventDefault();
        this.refs.modal.open();
    },

    openModal: function(e) {
        e.preventDefault();
        this.refs.modal.open();
    },

    closeModal: function() {
        this.refs.modal.close();
    },

    getInitialState: function() {
        return { text: this.props.wizard.get('dataFile').get('name').split('.')[0] };
    },

    onChange: function(e) {
        this.setState({text: e.target.value});
    },

    handleLastColumnChange: function(e) {
        this.props.wizard.set('lastColumnIsOutput', e.target.checked);
    },

    setDataFileName: function() {
        this.props.wizard.set('firstDatasetName', this.state.text);
        this.props.wizard.finish();
        this.refs.modal.close();
    },

    toOutput: function(){
        this.closeModal();
        this.props.wizard.showOutputFilter();
    },

    render: function() {
        var loader = null, message = null, setNameInput = null, setNameHeader = null, lastColumnComponent = null;
        if (this.props.wizard.get('finish-request') === 'before') {
            loader = (
                <div className="overlay">
                    <div className="ajax-loader"></div>
                </div>
            );
        } else if (this.props.wizard.get('finish-request') === 'fail') {
            loader = null;
            message = <div className="alert alert-danger">{Alerts.msg.simpleError}</div>;
        } else {
            loader = null; message = null;
        }
        if (this.props.df.get('file_format') === 'GENERAL') {
            if (this.props.wizard.outputs != true ) {
                lastColumnComponent = (<div className='no-output alert'>
                <p className='main-message'>You haven't selected any output</p>
                <p>Datasets without output can only be used for Autoencoder and prediction.</p>
                <a className="btn btn-warning" href="#" onClick={this.toOutput}>Return to output selection</a>
                </div>);
            } else {
                lastColumnComponent = (
                    <div>
                    </div>);
            }
        }
        if ($.inArray('split', this.props.wizard.filtersApplied) !== -1) {
            var splitFilter = this.props.wizard.filterRegister.split;
            setNameHeader = "Datasets names";
            setNameInput = (
                <div>
                    <h5>Datasets will be created with following names:</h5>
                    <p><strong>Dataset 1:</strong> {splitFilter.get('filenameFirst')}</p>
                    <p><strong>Dataset 2:</strong> {splitFilter.get('filenameSecond')}</p>
                </div>
            );
        } else {
            setNameHeader = "Set name for dataset";
            setNameInput = (
                <div>
                    <h5>Please provide a name:</h5>
                    <input type="text" onChange={this.onChange} value={this.state.text} className="rename-input" />
                </div>
            );
        }

        var filters = this.props.wizard.getNextFilters().map(function(filter) {
            return filter.getHeadComponent();
        });
        return (
            <div>
                {loader} {message}
                <div className="panel-body-step clearfix">
                    <div className="filters">
                        {filters.length ? filters : <p>All filters already applied</p>}
                    </div>
                    <div className={filters.length ? 'filters-apply' : 'filters-apply filters-apply-simple'}>
                        <span className="choose">Choose filter</span>
                        <span className="or">- or -</span>
                        <a href="#" className="filter-finish" onClick={this.handleFinish}>
                            <i className="icon icon-white icon-flag"></i>
                            Create Dataset
                        </a>
                    </div>
                </div>

                <BootstrapModal
                  ref="modal"
                  classes="modal-mini"
                  confirm="OK"
                  cancel="Cancel"
                  confirmButtonClass="btn-success"
                  onCancel={this.closeModal}
                  onConfirm={this.setDataFileName}
                  title={setNameHeader} >
                      {setNameInput}
                      {lastColumnComponent}
                </BootstrapModal>
            </div>
        );

    }
});

var SetupFilter = React.createClass({
    render: function() {

        var component = this.props.wizard.getCurrentFilter().getBodyComponent(this.props.status),
            filterInvalid = this.props.wizard.get('filterInvalid'),
            currentFilterName = this.props.wizard.get('currentFilter').name,
            mainBtn = null, classes = 'filters-apply ',
            cancelBtn = (
                <a href="#" className="filter-finish" onClick={this.props.handleCancelClick}>
                    <i className="icon icon-white icon-remove"></i>
                    Cancel
                </a>
            );
        if (this.props.wizard.get('state') === 'update-filter') {
            mainBtn = (
                <a href="#" className={filterInvalid ? "filter-finish disabled" : "filter-finish"} onClick={this.props.handleNextClick}>
                    Update
                    <i className="icon icon-white icon-chevron-right"></i>
                </a>
            );
        } else {
            mainBtn = (
                <a href="#" className={filterInvalid ? "filter-finish disabled" : "filter-finish"} onClick={this.props.handleNextClick}>
                    Next step
                    <i className="icon icon-white icon-chevron-right"></i>
                </a>
            );
        }

        if (currentFilterName === 'shuffle' || currentFilterName === 'normalize') {
            classes += 'filters-apply-simple';
        }

        return (
            <div className="panel-body-step panel-body-step2 clearfix">
                {component}
                <div className={classes}>
                    <div className="choose">Choose parameters</div>
                    {cancelBtn}{mainBtn}
                </div>
            </div>
        );
    }
});

var ActionPanel = React.createClass({
    nextClick: function(e) {
        e.preventDefault();
        if (this.props.wizard.get('filterInvalid')) {
            return false;
        } else {
            this.props.wizard.applyFilter(this.props.wizard.getCurrentFilter());
        }
        flexboxHack();
    },

    cancelUpdateClick: function(e) {
        e.preventDefault();
        this.props.wizard.cancelUpdate(this.props.wizard.getCurrentFilter());
    },

    cancelSelectClick: function(e) {
        e.preventDefault();
        this.props.wizard.cancelSelect();
    },


    render: function() {
        var state = this.props.wizard.get('state'),
            component = null;
        if (state === 'select-filter') {
            component = <SelectFilter wizard={this.props.wizard} df={this.props.df}/>;
        } else if (state === 'setup-filter') {
            component = <SetupFilter wizard={this.props.wizard} handleNextClick={this.nextClick} handleCancelClick={this.cancelSelectClick} dfs={this.props.dfs} status={this.props.status.refs.status}/>;
        } else { // update
            component = <SetupFilter wizard={this.props.wizard} handleNextClick={this.nextClick} handleCancelClick={this.cancelUpdateClick} dfs={this.props.dfs} status={this.props.status.refs.status}/>;
        }
        return (
            <div className="panel panel-primary panel-blue">
                <div className="panel-heading">
                    <h2>Data transformation</h2>
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
        var component = null, self = this, filters, visibilityClass = '';
        if (this.props.wizard.filtersApplied.length === 0 && this.props.wizard.filtersForDismiss.length === 0) {
            component = (
                <div className="panel-body">
                    <div className="panel-note panel-note-offset">
                        <p>No filters applied yet.</p>
                        <p>A list of filters which have already been applied to your data will be shown. You can always modify them.</p>
                    </div>
                </div>
            );
        } else {
            if (this.props.wizard.get('state') === 'update-filter') {
                filters = this.props.wizard.filtersApplied.map(function(name) {
                    return self.props.wizard.filterRegister[name].getAppliedComponent('applied');
                });
                filters.push(self.props.wizard.get('currentFilter').getAppliedComponent('update'));
                for (var i=0; i<this.props.wizard.filtersForDismiss.length; i++) {
                    filters.push(self.props.wizard.filterRegister[self.props.wizard.filtersForDismiss[i]].getAppliedComponent('dismiss'));
                }
            } else {
                filters = this.props.wizard.filtersApplied.map(function(name) {
                    return self.props.wizard.filterRegister[name].getAppliedComponent();
                });
            }

            if(this.props.wizard.get('state') === 'update-filter'){
                var last_pos = self.props.wizard.get('currentFilterPos');

                if(last_pos > -1){
                    filters.move(filters.length-1, last_pos);
                }
            }

            filters.reverse();

            var resetBtn = (
                <button className="filter-finish" onClick={this.resetClick}>
                    <i className="icon icon-white icon-remove"></i>
                    Reset all filters
                </button>
            );
            component = (
                <div className="panel-body">
                    <p className="panel-note">Click on filter to update:</p>
                    <div className="filters">
                        {filters}
                        {resetBtn}
                    </div>
                </div>
            );
        }

        if (this.props.wizard.get('currentFilter') !== undefined &&
            this.props.wizard.get('currentFilter').name === 'column select') {
            visibilityClass = 'hide';
        }

        return (
            <div className={"panel panel-secondary panel-blue " + visibilityClass}>
                <div className="panel-heading">
                    <h2>Filters Applied</h2>
                </div>
                {component}
            </div>
        );
    }
});

var WizardRoot = React.createClass({
    showTour: function() {
        var dfs = this.props.dfs;
        if (!getCookie('tourwasplayed-dataset-created')) {
            if (dfs.findWhere({isNewDatasetCreated: true})) {
                launchTour("Congrats, now you can train a model by clicking on the Create Ensemble button", 'dataset-created');
            }
        }
    },

    componentDidMount: function() {
        initTour();
        this.showTour();
    },

    componentDidUpdate: function() {
        this.showTour();
    },

    render: function() {
        var df = this.props.wizard.get('dataFile');
        return (
            <div>
                <a href="/dashboard/" className="btn btn-mini btn-info btn-wizard-back">
                    <i className="icon icon-white icon-chevron-left"></i>
                    Back to Dashboard
                </a>
                <div className="wizard clearfix">
                    <StatusPanel df={df} wizard={this.props.wizard} ref='status'/>
                    <ActionPanel df={df} wizard={this.props.wizard} dfs={this.props.dfs} status={this}/>
                    <ResultPanel df={df} wizard={this.props.wizard} />
                </div>
            </div>
        );
    }
});

module.exports = {
    WizardRoot: WizardRoot,
    FileInfo: FileInfo,
    MetaData: MetaData
};
