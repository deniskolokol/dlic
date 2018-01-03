/** @jsx React.DOM */
/* global React */
/* global userAdmin */
/* global _ */


"use strict";
var Utils = require('./Utils'),
    Bootstrap = require('./bootstrap.jsx'),
    ModelComponents = require('./ModelComponents.jsx'),
    cx = React.addons.classSet;

var ModelHead = ModelComponents.Head,
    ModelBody = ModelComponents.Body;

var BootstrapModal = Bootstrap.Modal,
    BootstrapSelect = Bootstrap.Select,
    AlertList = Bootstrap.AlertList,
    Switch = Bootstrap.Switch;


var StatusState = React.createClass({
    render: function() {
        var classes,
            state = this.props.state;
        if (this.props.shared) {
            state = 'shared';
        }
        classes = cx({
            'label': true,
            'label-warning': (state === 'shared' || state === 'stopped'),
            'label-info': state === 'training',
            'label-success': state === 'finished',
            'label-important': state === 'error'
        });
        if (state === 'error' && typeof this.props.error === 'string' && this.props.error) {
            state += ": " + this.props.error;
        }
        return (
            <div>
                <b>Status:{' '}</b>
                <span className={classes}>{state}</span>
            </div>
        );
    }
});

var SimpleStatusItem = React.createClass({
    render: function() {
        return (
            <div className={this.props.classes}>
                <b>{this.props.name}:{' '}</b><span>{this.props.value}</span>
            </div>
        );
    }
});

var EnsembleStatus = React.createClass({
    render: function() {
        var props = this.props, traceback = null, queuePosition = null;
        if (props.traceback && userAdmin) {
            traceback = <div className="offset-top-mini">
                            <pre>{props.traceback}</pre>
                        </div>;
        }
        if (props.ensembleState === 'in queue') {
            queuePosition = <SimpleStatusItem
                             name="Position in queue"
                             value={props.queuePosition || "unknown"} />;
        }
        return (
            <div className="train-info">
                <SimpleStatusItem name="Finished jobs" value={props.finishedJobs} />
                <SimpleStatusItem name="Training time" value={props.trainingTime} />
                <StatusState state={props.ensembleState} error={props.error} shared={props.isShared} />
                {traceback}
                {queuePosition}
            </div>
        );
    }
});

var ActionButton = React.createClass({
    render: function() {
        return <button className={this.props.classes} onClick={this.props.handleClick}>
                    <i className={"icon icon-white icon-" + this.props.icon}></i> {this.props.name}
               </button>;
    }
});

var Select = React.createClass({

    getInitialState: function() {
        return {value: this.props.value};
    },

    changeSelect: function(event){
        this.props.ensemble.set(this.props.type, event.target.value);
        this.setState({value:event.target.value})
    },

    render: function() {

        var value = this.state.value || 0, options = [];
        if (value === 0) {
            options = [<option key={0} value={0}>---</option>];
        }
        options = options.concat(
            this.props.values.map(function(val) {
                return (<option key={val.id} value={val.id}>
                    {val.id + ': ' + val.name}
                    </option>);
            })
        );

        var filter;
        $(this.props.values).each(function(i,val){

            if(val.id == value)
                filter = i;

        });

        return (
        <div>
            <select value={value} onChange={this.changeSelect}>{options}</select>
            <FilterDatasetPopOver filters={this.props.values[filter].filters} value={value} />
        </div>)
    },

});


var FilterDatasetPopOver = React.createClass({

    getInitialState: function() {
        return {value: this.props.value, merge_name: '', current_merge_id:''};
    },

    componentDidMount: function(){
        this.createPopOver();

    },

    getDataFileName: function(id) {

        var self = this;
        $.ajax({
            url: '/api/data/' + id+"/",
            type: 'GET',
            dataType: 'json'
        }).done(function (data) {
            self.setState({merge_name:data.name, current_merge_id:data.id});
        }).fail(function (xhr) {
            console.log('fail');
        });
    },


    createPopOver: function() {
    // When the component is added, turn on popover

        $(this.getDOMNode()).popover('destroy');

        var filters  = this.props.filters;
        var icons = {
            normalize: '<i class="icon icon-white icon-signal"></i> Normalize',
            shuffle: '<i class="icon icon-white icon-random"></i> Shuffle',
            split: '<i class="icon icon-white icon-resize-full"></i> Split',
            balance:'<i class="icon icon-white icon-tasks"></i> Balance',
            merge: '<i class="icon icon-white icon-resize-small"></i> Merge',
            binarize: '<i class="icon icon-white icon-random"></i> Binarize',
            };

        var html_content = "<ul class='ul-dataset'>";
        var column = false;
        var filter_display;

        var getData = this.getDataFileName;
        var self = this;

        $(filters).each(function(n, filter){

            if((filter.name == "permute" || filter.name == "ignore") && column == false ){
                filter_display = '<i class="icon icon-white icon-indent-right"></i> Column Select';
                column = true;
            }
            else if(filter.name == 'split'){
                filter_display = icons[filter.name] + " Start: " +filter.start + "%, End: "+ filter.end +"%";
            }
            else if(filter.name == "balance"){
                filter_display = icons[filter.name] + " (" + filter.sample +" "+filter.adjust[0] +"%)";
            }
            else if(filter.name == "merge"){
                var id = filter.datas[0];
                if(id != self.state.current_merge_id)
                    self.getDataFileName(id);
                var name = self.state.merge_name;
                filter_display = icons[filter.name] + " (#" +id+" "+ name +")";
            }
            else if(filter.name != "permute" && filter.name != "ignore" ){
                filter_display = icons[filter.name];
            }
            else
                return false;

            html_content += "<li>"+filter_display+"</li>";

        });


        html_content += "</ul>";
        var options = {
            title:'Filters Applied',
            trigger: 'hover',
            placement: 'right',
            content: html_content,
            container: 'body', //to body otherwise the div will hide it
            html: true,
        }
        $(this.getDOMNode()).popover(options);

  },
    render: function(){
        if(this.isMounted())
            this.createPopOver();
        return(
            <div className="dataset-popover-train">
            <i className="icon icon-white icon-info-sign"></i>
            </div>
        )

    },
});

var EnsembleSettings = React.createClass({
    handleFileChange: function(dataset, event) {
        this.props.ensemble.set(dataset, event.target.value);
        console.log(this.refs);
    },

    render: function() {
        var infoText = null, applyAction = null, switches = null,
            testDatasetSelect = null, datasetsAlert = null,
            props = this.props,
            ensemble = props.ensemble;

        if (props.possibleDatasets === undefined) {
            ensemble.loadPossibleDatasets();
            return <div className="ajax-loader"></div>;
        }
        if (props.possibleDatasetsLoaded === false) {
            datasetsAlert = <div className="alert alert-error">Error. Please refresh your browser and try again.</div>;
        }
        applyAction = (
            <div>
                <div>
                </div>
                <button className="btn btn-mini btn-success" onClick={ensemble.applySettings.bind(ensemble)}>
                    <i className="icon icon-white icon-ok"></i> Apply Settings
                </button>
            </div>
        );
        if (!props.isTestless) {
            testDatasetSelect = (
                <span>
                <b>Test dataset</b><br />
                <Select values={props.possibleDatasets}
                        value={props.testDataset}
                        ensemble={this.props.ensemble}
                        type="train_dataset"/><br />
                </span>
            );
        }

        if (!props.isDatasetsValid) {
            datasetsAlert = <div className="alert alert-important">In order to keep training this model, please select datasets for training</div>;
        }
        if (!props.isShared) {
            switches = (
                <ul>
                    <li>
                        <b>Send me email on status change:{' '}</b>
                        <Switch value={props.sendEmailOnChange}
                                handleChange={ensemble.toggleSendEmail.bind(ensemble)} />
                    </li>
                </ul>);
        }

        var train_select = <Select values={props.possibleDatasets}
                            value={props.trainDataset}
                            ensemble={this.props.ensemble}
                            type="train_dataset" />

        return (
            <div className="train-subheader">
                {datasetsAlert}
                <div className="train-dataset">
                    <strong>Train dataset</strong><br />
                    {train_select}<br />
                    {testDatasetSelect}
                </div>
                <div className="train-settings">
                    {switches}
                    {applyAction}
                </div>
                <EnsembleStatus
                    finishedJobs={props.finishedJobs}
                    queuePosition={props.queuePosition}
                    traceback={props.traceback}
                    trainingTime={Utils.secondsToStr(props.trainingTime)}
                    isShared={props.isShared}
                    error={props.error}
                    ensembleState={props.ensembleState} />
            </div>
        );
    }
});

var EnsembleActions = React.createClass({
    handleOneMoreModelClick: function(event) {
        var name = this.props.ensemble.getNewModelName();
        if (typeof name === 'object') {
            this.openModal();
        } else {
            this.props.ensemble.addOneMoreModel(name);
        }
    },

    openModal: function() {
        this.refs.modal.open();
    },

    closeModal: function() {
        this.refs.modal.close();
    },

    submitNewModal: function(event) {
        this.props.ensemble.addOneMoreModel(this.refs.modalSelect.state.value);
        this.refs.modal.close();
    },

    openDeleteModal: function(e) {
        e.preventDefault();
        this.refs.modalDelete.open();
    },

    closeDeleteModal: function() {
        this.refs.modalDelete.close();
    },

    deleteEnsemble: function() {
        var en = this.props.ensemble;
        this.closeDeleteModal();
        $.ajax({
            url: '/api/ensemble/' + en.id + '/',
            type: 'DELETE',
            dataType: 'json'
        }).done(function (data) {
            window.location.href = '/dashboard/ensembles/';
        }).fail(function (xhr) {
            // TODO: show alert on fail
        });
    },

    render: function() {
        var props = this.props,
            ensemble = props.ensemble,
            names = props.newModelNames,
            btnStart = null, btnStop = null, btnPredict = null, btnDelete = null,
            btnShare = null, btnAdd = null, btnSettings = null, modal = null,
            modalSelect = null, modalDelete = null;

        if (typeof names === 'object') {
            modalSelect = <BootstrapSelect ref="modalSelect" value={names[0][0]} values={names} />;
            modal = (
              <BootstrapModal
                ref="modal"
                confirm="OK"
                cancel="Cancel"
                onCancel={this.closeModal}
                onConfirm={this.submitNewModal}
                title="Select model type.">
                    {modalSelect}
              </BootstrapModal>
            );
        }

        modalDelete = (
            <BootstrapModal
                ref="modalDelete"
                confirm="Delete"
                cancel="Cancel"
                confirmButtonClass="btn-danger"
                onCancel={this.closeDeleteModal}
                onConfirm={this.deleteEnsemble}
                title={"Delete ensemble #" + this.props.ensemble.get('id')} >
                  <p>If you delete this ensemble, you will no longer have access to it and it will be removed permanently.</p>
            </BootstrapModal>
        );

        if (props.allowStartResume) {
            btnStart = <ActionButton classes="btn btn-success"
                        name={(props.ensembleState === 'new') ? "Start All" : "Resume All"} icon="play"
                        handleClick={ensemble.resume.bind(ensemble)} />;
        }
        if (props.allowStop) {
            btnStop = <ActionButton classes="btn btn-warning" name="Stop All"  icon="stop"
                       handleClick={ensemble.stop.bind(ensemble)} />;
        }
        if (props.allowAddNewModel) {
            btnAdd = <ActionButton classes="btn btn-info" name="Add Model" icon="plus"
                      handleClick={this.handleOneMoreModelClick} />;
        }
        if (props.allowShare) {
            btnShare = <ActionButton classes="btn btn-info" name="Share" icon="share-alt"
                        handleClick={ensemble.share.bind(ensemble)} />;
        }
        if (props.allowPredict) {
            btnPredict = <ActionButton classes="btn btn-success" name="Predict" icon="screenshot"
                          handleClick={ensemble.goToPredict.bind(ensemble)} />;
        }
        btnDelete = <ActionButton classes="btn btn-danger" name="Delete Ensemble" icon="remove"
                     handleClick={this.openDeleteModal} />;
        btnSettings = <ActionButton classes="btn btn-info"
                       name={(this.props.settingsVisible) ? "Hide Settings" : "Show Settings"}
                       icon="cog" handleClick={this.props.toggleSettings} />;
        return (
            <div>
                <div className="btn-group btn-group-right">
                    {btnStart}{btnStop}{btnPredict}{btnSettings}{btnAdd}{btnShare}
                </div>
                {btnDelete}
                {modal}
                {modalDelete}
            </div>
        );
    }
});

var EnsembleReact = React.createClass({
    mixins: [Utils.BackboneEventMixin],

    getBackboneEvents: function() {
        var props = this.props;
        return {
            "change": props.ensemble,
            "add remove": props.ensemble.models
        };
    },

    getInitialState: function() {
        return {
            settingsVisible: !this.props.ensemble.validateDatasets(),
            selectedTab: 'main'
        };
    },

    selectModel: function(model) {
        this.setState({selectedModel: model});
    },

    selectTab: function(name) {
        this.setState({selectedTab: name});
    },


    toggleSettings: function() {
        this.setState({settingsVisible: !this.state.settingsVisible});
    },

    render: function() {
        var ensemble = this.props.ensemble,
            models = ensemble.models,
            settings = null,
            modelsPanel = null,
            modelsHeads = null,
            modelBody = null,
            modelIndex,
            selectedModel = this.state.selectedModel;

        if (models.length > 0) {
            if (!selectedModel || !_.contains(models.pluck('id'), selectedModel.id)) {
                selectedModel = models.at(0);
            }
            modelsHeads = models.map(function(model, index) {
                if (model.id === selectedModel.id) {
                    modelIndex = index;
                }
                return <ModelHead
                        key={model.id}
                        model={model}
                        ensemble={ensemble}
                        isSelected={model.id === selectedModel.id}
                        handleClick={this.selectModel.bind(this, model)}/>;
            }, this);
            modelBody = <ModelBody
                         key={selectedModel.id}
                         model={selectedModel}
                         ensemble={ensemble}
                         selectedTab={this.state.selectedTab}
                         handleSelectTab={this.selectTab}
                         previousModel={models.at(modelIndex+1)}
                         nextModel={models.at(modelIndex-1)}
                         handleSelectModel={this.selectModel}
                         />;
            modelsPanel = (
                <div className="row">
                    <div className="span3">
                        <div className="models-list">
                            <h3>List of models</h3>
                            <ul className="models-list-ul">
                                {modelsHeads}
                            </ul>
                        </div>
                    </div>
                    {modelBody}
                </div>
            );
        }
        if (this.state.settingsVisible) {
            settings = <EnsembleSettings
                        dataType={ensemble.get('data_type')}
                        allowApply={ensemble.allowApplySettings()}
                        isEnsembleShared={ensemble.get('shared')}
                        isTestless={ensemble.isTestless()}
                        isDatasetsValid={ensemble.validateDatasets()}
                        possibleDatasets={ensemble.get('possibleDatasets')}
                        trainDataset={ensemble.get('train_dataset')}
                        testDataset={ensemble.get('test_dataset')}
                        sendEmailOnChange={ensemble.get('send_email_on_change')}
                        ensembleState={ensemble.get('state')}
                        traceback={ensemble.get('traceback')}
                        queuePosition={ensemble.get('queue_position')}
                        finishedJobs={ensemble.getFinishedJobs()}
                        trainingTime={ensemble.getTrainingTime()}
                        isShared={ensemble.get('share')}
                        error={ensemble.get('error')}
                        possibleDatasetsLoaded={ensemble.get('possibleDatasetsLoaded')}
                        ensemble={ensemble} />;
        }
        return (
            <div>
                <div className="train-header">
                    <h1>
                        Train Ensemble {this.props.ensemble.id}
                    </h1>
                    <div className="training-actions">
                        <div className="row-fluid">
                        <EnsembleActions
                            ensemble={ensemble}
                            ensembleState={ensemble.get('state')}
                            newModelNames={ensemble.getNewModelName()}
                            allowStartResume={ensemble.allowStartResume()}
                            allowStop={ensemble.allowStop()}
                            allowAddNewModel={ensemble.allowAddNewModel()}
                            allowShare={ensemble.allowShare()}
                            allowPredict={ensemble.allowPredict()}
                            settingsVisible={this.state.settingsVisible}
                            toggleSettings={this.toggleSettings} />
                        </div>
                    </div>
                </div>
                {settings}
                <AlertList models={[ensemble]} />

                {modelsPanel}
            </div>
        );
    }
});

module.exports = EnsembleReact;
