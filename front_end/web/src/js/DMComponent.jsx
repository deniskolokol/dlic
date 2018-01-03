/** @jsx React.DOM */
/* global React */
/* global initTour */
/* global getCookie */
/* global launchTour */
/* global scrollToDataset */
/* global userAdmin */


"use strict";
var Utils = require('./Utils'),
    Alerts = require('./alerts'),
    Bootstrap = require('./bootstrap.jsx'),
    DatasetWizard = require('./DatasetWizardComponents.jsx'),
    EnsembleWizard = require('./EnsembleWizardComponents.jsx'),
    EnsembleWizardRoot = EnsembleWizard.WizardRoot,
    BootstrapModal = Bootstrap.Modal,
    BootstrapButton = Bootstrap.Button,
    BootstrapAlert = Bootstrap.Alert,
    FileInfo = DatasetWizard.FileInfo,
    DatasetWizardRoot = DatasetWizard.WizardRoot,
    MetaData = DatasetWizard.MetaData,
    Router;

var CurrentStatusReact = React.createClass({
    render: function() {
        var classes = "label ",
            message = null,
            status = this.props.status;
        if (this.props.parseLog && this.props.status !== 'Ready') {
            message = this.props.parseLog.get('message');
        }
        if (this.props.status === 'Parsing') {
            classes += "label-info";
        } else if (this.props.status === 'Ready') {
            if (this.props.file_format === 'UNSUPPORTED') {
                status = 'Unsupported';
                classes += "label-important";
            } else {
                classes += "label-success";
            }
        } else if (this.props.status === 'Parse Failed') {
                classes += "label-important";
        }
        return (
            <div className="span5">
                <span className={classes}>{status}</span>
                <span className="dm-current-state">{message}</span>
            </div>
        );
    }
});

var AccordionHeadReact = React.createClass({
    clearAlert: function() {
        this.props.df.unset('rename-request');
        this.props.df.unset('delete-request');
    },

    handleDataFileDelete: function() {
        this.props.handleDataFileDelete(this.props.df);
    },

    render: function() {
        var df = this.props.df;
        var headBody = null, alert = null;
        var head = null;

        if (df.get('delete-request') === 'done') {
            alert = <BootstrapAlert
                     type="success"
                     message={"File <strong>" + df.get('name') + "</strong> has been successfully deleted."}
                     handleClose={this.handleDataFileDelete} />;
        } else {
            if (df.get('delete-request') === 'fail') {
                alert = <BootstrapAlert
                         type="error"
                         message={Alerts.msg.simpleError}
                         handleClose={this.clearAlert}/>;
            }
            if (df.get('delete-request') === 'before') {
                headBody = <div className="ajax-loader"></div>;
            } else {
                headBody = (
                    <div className={"row-fluid"}>
                        <div className="span3">
                            <div className="dm-filename dm-col-offset">
                                <strong>{df.get('name')}</strong>
                                {this.props.df.get('shared') ? <label className="label label-warning no-float">Shared</label> : ''}
                            </div>
                        </div>
                        <CurrentStatusReact status={df.get('state')}
                                            file_format={df.get('file_format')}
                                            parseLog={df.parseLogs.last()}/>
                        <div className="span2 text-center">
                            {df.get('datasets').length}
                        </div>
                        <div className="span2 text-center">
                            <span className="btn btn-mini btn-dark">
                                <i className="icon icon-white icon-info-sign"></i> Details
                            </span>
                        </div>
                    </div>
                );
            }
            head = (
                <a className={"accordion-toggle " + this.props.classes}
                   onClick={this.props.handleHeadClick}>
                    <div className="dm-item">
                        {headBody}
                    </div>
                </a>
            );
        }

        if (df.get('rename-request') === 'done') {
            alert = <BootstrapAlert
                     type="success"
                     message="File has been successfully renamed."
                     handleClose={this.clearAlert} />;
        } else if (df.get('rename-request') === 'fail') {
            alert = <BootstrapAlert
                     type="error"
                     message={Alerts.msg.simpleError}
                     handleClose={this.clearAlert} />;
        }

        return (
            <div className="accordion-heading">
                {alert}
                {head}
            </div>
        );
    }
});

var ShowLogsReact = React.createClass({
    render: function() {
        var df = this.props.df,
            logs = null,
            messages = null;
        if (df.get('state') === 'Ready') {
            messages = df.parseLogs.pluck('message');
        }
        return (
            <div>
                <div className="collapse" id={"logs-" + df.id}>
                    <div className="dm-logs">
                        <h4>Log</h4>
                        <div className="dm-logs-list custom-scroll">
                            {messages}
                        </div>
                    </div>
                </div>
                <span className="show-logs collapsed" data-toggle="collapse" data-target={"#logs-" + df.id}>
                    <i className="icon icon-white icon-list-alt"></i>
                </span>
            </div>
        );
    }
});

var MetaDataColumn = React.createClass({
    render: function() {
        var df = this.props.df, metaData = null, file_format = df.get('file_format'),
            messages = null;
        if (df.get('state') === 'Parsing' || file_format === 'UNSUPPORTED') {
            messages = df.parseLogs.pluck('message');
            metaData = <div className="span3 dm-logs-full">
                           <h4>Log</h4>
                           {messages}
                       </div>;
        } else if (df.needReparse()) {
            metaData = <div className="span3">{Alerts.msg.datafileNeedReparse}</div>;
        } else {
            metaData = (
                <div className="span3">
                    <h4>Meta data</h4>
                    <MetaData df={df} />
                    <ShowLogsReact df={df} />
                </div>
            );
        }
        return metaData;
    }
});

var DatasetEnsemblesLiReact = React.createClass({
    render: function() {
        return (
            <li className="clearfix">
                <span className="pull-right">
                    <strong>Models:</strong> {this.props.ensemble.models_count}
                </span>
                <strong>
                    <i className="icon icon-white icon-chevron-right"></i>
                    <a href={"/train-ensemble/" + this.props.ensemble.id}>
                        Ensemble #{this.props.ensemble.id}
                    </a>
                </strong>
            </li>
        );
    }
});


var LiPopOver = React.createClass({

  componentDidMount: function() {
    // When the component is added, turn on popover
        var props = this.props;
        var filters = JSON.parse(props.filters);
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
                var name;
                $(props.dfs.models).each(function(i, mo){
                    if(mo.id == id)
                        name = mo.attributes.name;
                });
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
            placement: 'left',
            content: html_content,
            container: 'body', //to body otherwise the div will hide it
            html: true,
        }
        $(this.getDOMNode()).popover(options);
  },

    render: function(){
        return(
            <li>
                {this.props.children}
            </li>
        )

    },

});

var DatasetLiReact = React.createClass({
    getInitialState: function() {
        return {ensembles: null};
    },
    getEnsemblesList: function(e) {
        e.preventDefault();
        var id = this.props.key, self = this;
        $.ajax({
            url: '/api/ensemble/?dataset=' + id,
            type: 'GET',
            dataType: 'json'
        }).done(function (data) {
            self.setState({ensembles: data});
            self.props.loadEnsembles(data, id);
            self.props.handleChange();
        }).fail(function (xhr) {
            console.log('fail');
        });
    },

    openConfirmModal: function(e) {
        e.preventDefault();
        this.refs.confirmModal.open();
    },

    closeConfirmModal: function() {
        this.refs.confirmModal.close();
    },

    openWarningModal: function() {
        this.refs.warningModal.open();
    },

    closeWarningModal: function() {
        this.refs.warningModal.close();
    },

    deleteDataset: function() {
        this.closeConfirmModal();
        var self = this;
        $.ajax({
            url: '/api/dataset/' + this.props.key + '/',
            type: 'DELETE',
            dataType: 'json'
        }).done(function (data) {
            self.props.handleDelete(self);
        }).fail(function (request, status, error) {
            if (error === 'BAD REQUEST') {
                self.openWarningModal();
            }
        });
    },

    render: function() {
        var modalDelete = null;
        return (
            <LiPopOver filters={this.props.filters} dfs={this.props.dfs}>
                <div>
                    <span className="dataset-remove pull-right" onClick={this.openConfirmModal} title="Delete this dataset">
                        <i className="icon icon-white icon-remove"></i>
                    </span>
                    <span className="datasets-list-action" onClick={this.getEnsemblesList} >
                        <i className="icon icon-white icon-chevron-right"></i>
                        <strong>{this.props.name} </strong>
                    </span>
                </div>
                <BootstrapModal
                  ref="confirmModal"
                  confirm="Delete"
                  cancel="Cancel"
                  confirmButtonClass="btn-danger"
                  onCancel={this.closeConfirmModal}
                  onConfirm={this.deleteDataset}
                  title={"Delete dataset " + this.props.name}>
                      <p>If you delete Dataset #{this.props.key}, you will no longer have access to it and it will be removed permanently from your Datasets list.</p>
                </BootstrapModal>

                <BootstrapModal
                  ref="warningModal"
                  cancel="Close"
                  onCancel={this.closeWarningModal}
                  title="Error">
                      <p>This dataset has ensembles, delete not allowed.</p>
                </BootstrapModal>

                <BootstrapModal
                  ref="try"
                  cancel="Close"
                  title="Error">
                      <p>Check this out.</p>
                </BootstrapModal>
            </LiPopOver>
        );
    }
});

var DataFileEnsemblesReact = React.createClass({
    getInitialState: function() {
        return {ensembles: [], loader: false};
    },

    componentDidMount: function() {
        var df = this.props.df;
        var self = this;
        $.ajax({
            url: '/api/ensemble/?data=' + df.id,
            type: 'GET',
            dataType: 'json'
        }).done(function (data) {
            self.setState({ensembles: data});
        }).fail(function (xhr) {
            console.log('fail');
        });
    },

    openConfirmModal: function(id) {
        this.refs['confirmModal' + id].open();
        return false;
    },

    closeConfirmModal: function(id) {
        this.refs['confirmModal' + id].close();
    },

    deleteEnsemble: function(en) {
        this.closeConfirmModal(en.id);
        var self = this;
        this.setState({loader: true});
        $.ajax({
           url: '/api/ensemble/' + en.id + '/',
            type: 'DELETE',
            dataType: 'json'
        }).done(function (data) {
            $('.ensemble-list-item[id="ens' + en.id + '"]').hide();
            self.setState({loader: false});
            // TODO: update array
        }).fail(function (xhr) {
            self.setState({loader: false});
            // TODO: alert on fail
        });
    },

    render: function() {
        var self = this;
        var loader = this.state.loader ? <div className="ajax-loader"></div> : null;
        var ensemblesList = this.state.ensembles.map(function(ensemble) {
            return (
                    <li key={ensemble.id}>
                        <div className="ensemble-list-item" id={"ens" + ensemble.id}>
                            <span className="dataset-remove pull-right" onClick={self.openConfirmModal.bind(self, ensemble.id)} title="Delete this ensemble">
                                <i className="icon icon-white icon-remove"></i>
                            </span>
                            <a href={"/train-ensemble/" + ensemble.id}>
                                <i className="icon icon-white icon-chevron-right"></i>
                                Ensemble #{ensemble.id}
                            </a>
                        </div>

                        <BootstrapModal
                            ref={"confirmModal" + ensemble.id}
                            confirm="Delete"
                            cancel="Cancel"
                            confirmButtonClass="btn-danger"
                            onCancel={self.closeConfirmModal.bind(self, ensemble.id)}
                            onConfirm={self.deleteEnsemble.bind(self, ensemble)}
                            title={"Delete ensemble #" + ensemble.id} >
                              <p>If you delete this ensemble, you will no longer have access to it and it will be removed permanently.</p>
                        </BootstrapModal>
                    </li>
                );
        });

        return (
            <div className="ensembles-list-wrap">
                {ensemblesList.length ? <h4>Ensembles created from this data</h4> : ''}
                <ul className="ensembles-list">
                    {ensemblesList}
                </ul>
                {loader}
            </div>
        );
    }
});

var EnsembleUlReact = React.createClass({
    getInitialState: function() {
        return {classes: '', ensemblesList: [], currentDatasetId: null};
    },
    handleChange: function() {
        this.setState({classes: 'active'});
    },
    deleteDataset: function(dataset) {
        var df = this.props.df;
        var datasets = this.props.datasets.filter(function(d) {
            return d.id !== dataset.props.key;
        });
        df.set('datasets', datasets);
    },
    handleBack: function(e) {
        e.preventDefault();
        this.setState({classes: ''});
    },
    loadEnsembles: function(ensembles, id) {
        var ens = ensembles.map(function(ensemble) {
            return <DatasetEnsemblesLiReact ensemble={ensemble} key={ensemble.id}/>;
        });
        this.setState({ensemblesList: ens, currentDatasetId: id});
    },
    render: function() {
        var df = this.props.df, self = this;
        var datasets = this.props.datasets.map(function(dataset) {
            return <DatasetLiReact df={df} key={dataset.id} name={dataset.name}
                                           handleChange={self.handleChange}
                                           handleDelete={self.deleteDataset}
                                           loadEnsembles={self.loadEnsembles}
                                           filters={dataset.filters}
                                            dfs={self.props.dfs} />;
        });
        var ensembles = this.state.ensemblesList;
        return (
            <div className="span4">
                <div className="row datasets-and-ensembles">
                    <div className="span6">
                        <div className="slide-container">
                            <div className={"slide " + this.state.classes}>
                                {datasets.length ? <h4>Datasets created from this data</h4> : ''}
                                <ul className="datasets-list">
                                    {datasets}
                                </ul>
                            </div>

                            <div className={"slide " + this.state.classes}>
                                <h4>Ensembles trained on Dataset #{this.state.currentDatasetId}</h4>
                                <ul className="dm-file-meta datasets-ensembles">
                                    {ensembles.length ? ensembles : <p>No ensembles created yet.</p>}
                                </ul>
                                <div className="controls">
                                    <a href="#" onClick={this.handleBack} className="btn btn-mini btn-back pull-left">
                                        <i className="icon icon-white icon-chevron-left"></i>
                                        Back to Datasets
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="span6">
                        <DataFileEnsemblesReact df={df} key={df.id} />
                    </div>
                </div>
            </div>
        );
    }
});

var FileActionsReact = React.createClass({
    openModal: function(e) {
        e.preventDefault();
        this.refs.modal.open();
    },

    closeModal: function() {
        this.refs.modal.close();
    },

    deleteDataFile: function() {
        var df = this.props.df;
        this.closeModal();
        df.beforeDeleteRequest();
        $.ajax({
            url: '/api/data/' + df.id + '/',
            type: 'DELETE',
            dataType: 'json'
        }).done(function (data) {
            df.deleteRequestDone(data);
        }).fail(function (xhr) {
            df.deleteRequestFail(xhr);
        });
    },

    reparse: function(e) {
        e.preventDefault();
        var df = this.props.df, oldState = df.get('state');
        $.ajax({
            url: '/api/data/' + df.id + '/parse/',
            type: 'POST',
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            df.set(data);
        }).fail(function (xhr) {
            df.set('state', oldState);
        });
    },

    runWizard: function(e) {
        e.preventDefault();
        Router.navigate("data-wizard/" + this.props.df.id + '/', {trigger: true});
    },

    handleCreateEnsemble: function(e) {
        e.preventDefault();
        var url = "ensemble-wizard/" + this.props.df.id + '/step/model-select/';
        Router.navigate(url, {trigger: true});
    },

    render: function() {
        var btnStart = null, btnRemove = null, btnReparse = null,
            df = this.props.df, btnNewDataset = null, btnShare = null;

        if (df.get('state') === 'Ready' &&
            this.props.file_format !== 'UNSUPPORTED' && !df.needReparse()) {
            if (df.get('datasets') && df.get('datasets').length > 0 && !df.isTimeseriesWithoutOutput()) {
                btnNewDataset = <li>
                                    <a hrefa="#"
                                       onClick={this.handleCreateEnsemble} className="btn btn-mini btn-info">
                                        <i className="icon icon-white icon-th"></i>
                                        Create Ensemble
                                    </a>
                                </li>;
            }
            btnStart = <li>
                           <BootstrapButton className="btn btn-mini btn-success"
                                            href="#" onClick={this.runWizard}>
                               <i className={"icon icon-white icon-ok"} />
                               Create Dataset
                           </BootstrapButton>
                       </li>;
        }

        if (this.props.df.needReparse() && this.props.df.get('state') !== 'Parsing') {
            btnReparse = <li>
                             <BootstrapButton className="btn btn-mini btn-info"
                                              href="#"
                                              onClick={this.reparse}>
                                 <i className="icon icon-white icon-repeat" />
                                 Reparse
                             </BootstrapButton>
                         </li>;
        }

        if (!this.props.df.get('shared')) {
            btnRemove = <li>
                            <BootstrapButton className="btn btn-mini btn-danger"
                                             href="#"
                                             onClick={this.openModal}>
                                <i className="icon icon-white icon-trash" />
                                Remove
                            </BootstrapButton>
                        </li>;
        }

        if (userAdmin && !this.props.df.get('shared')) {
            btnShare = <li>
                            <BootstrapButton className="btn btn-mini btn-warning"
                                             href="#"
                                             onClick={df.share.bind(df)}>
                                <i className="icon icon-white icon-share-alt" />
                                Share
                            </BootstrapButton>
                        </li>;
        }

        return (
            <div>
                <ul className="dm-file-meta">
                    {btnStart}{btnNewDataset}{btnReparse}{btnRemove}{btnShare}
                </ul>
                <BootstrapModal
                  ref="modal"
                  confirm="Delete"
                  cancel="Cancel"
                  confirmButtonClass="btn-danger"
                  onCancel={this.closeModal}
                  onConfirm={this.deleteDataFile}
                  title={"Delete file " + this.props.df.get('name')} >
                      <p>If you delete this file, you will no longer have access to it and it will be removed permanently from your Data list.</p>
                </BootstrapModal>
            </div>
        );
    }
});

var FileRenameReact = React.createClass({
    openModal: function(e) {
        e.preventDefault();
        this.refs.modal.open();
    },

    closeModal: function() {
        this.refs.modal.close();
    },

    getInitialState: function() {
        return { text: this.props.df.get('name') };
    },

    onChange: function(e) {
        this.setState({text: e.target.value});
    },

    renameDataFile: function() {
        var df = this.props.df;
        var filename = this.state.text;
        this.closeModal();
        $.ajax({
            url: '/api/data/' + df.id + '/',
            type: 'PATCH',
            data: JSON.stringify({name: filename}, null, 2),
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            df.set('name', data.name);
            df.renameRequestDone(data);
        }).fail(function (xhr) {
            df.renameRequestFail(xhr);
        });
    },

    render: function() {
        return (
            <div>
                <div className="meta-string">
                    <i className="icon icon-white icon-edit"></i>
                    <a href="#" onClick={this.openModal}>Rename</a>
                </div>
                <BootstrapModal
                  ref="modal"
                  classes="modal-mini"
                  confirm="Rename"
                  cancel="Cancel"
                  confirmButtonClass="btn-success"
                  onCancel={this.closeModal}
                  onConfirm={this.renameDataFile}
                  title={"Rename data file"} >
                      <p>Please provide new filename:</p>
                      <input type="text" onChange={this.onChange} value={this.state.text} className="rename-input" />
                </BootstrapModal>
            </div>
        );
    }
});


var AccordionBodyReact = React.createClass({
    render: function() {
        var df = this.props.df, visibilityClass = "", renameComponent = null;

        if (df.get('delete-request') === 'before' || df.get('delete-request') === 'done') {
            visibilityClass += "hide";
        }
        if (!this.props.df.get('shared')) {
            renameComponent = <FileRenameReact df={df} />;
        }
        return (
            <div className="accordion-body">
                <div className="accordion-inner">
                    <div className={"dm-details " + visibilityClass}>
                        <div className="row-fluid">
                            <div className="span3 dm-col-offset">
                                <h4>File info</h4>
                                {renameComponent}
                                <FileInfo df={df} status={df.get('state')} />
                            </div>
                            <MetaDataColumn df={df} />
                            <EnsembleUlReact datasets={df.get('datasets')} df={df} dfs={this.props.dfs}/>
                            <div className="span2 text-center">
                                <h4>Actions</h4>
                                <FileActionsReact file_format={df.get('file_format')} df={df} />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
});
var ReactCSSTransitionGroup = React.addons.CSSTransitionGroup;


var AccordionGroupReact = React.createClass({
    getInitialState: function() {
        return { classes: 'collapsed', body: [] };
    },

    handleHeadClick: function() {
        this.props.handleClick(this.props.df);
    },

    render: function() {
        var df = this.props.df, body = [], classes = '';
        if (this.props.showBody) {
            body = [<AccordionBodyReact key={this.props.df.id} df={this.props.df} dfs={this.props.dfs} />];
        } else {
            classes = 'collapsed';
        }
        return (
            <div className="accordion-group">
                <AccordionHeadReact
                 df={this.props.df}
                 handleDataFileDelete={this.props.handleDataFileDelete}
                 handleHeadClick={this.handleHeadClick}
                 classes={classes} />
                 <ReactCSSTransitionGroup transitionName="expand">
                     {body}
                 </ReactCSSTransitionGroup>
            </div>
        );
    }
});

var DataFileListReact = React.createClass({
    showTour: function() {
        var dfs = this.props.dfs;
        if (!getCookie('tourwasplayed-datafile-upload')) {
            if ((dfs.where({state: "Ready"}).length - dfs.where({state: "Ready", shared: true}).length) === 1) {
                launchTour("<h1>Congratulations! You've uploaded your first dataset to Ersatz</h1><hr>Now that you have a dataset, you should split it into training and testing sets by clicking on the \"Create dataset\" button", 'datafile-upload');
            }
        }
    },

    componentDidMount: function() {
        initTour();
        scrollToDataset();
        this.showTour();
    },

    componentDidUpdate: function() {
        this.showTour();
    },

    getInitialState: function() {
        return {filterString: ''};
    },

    filterName: function(name) {
        name = name.toLowerCase();
        var filterString = this.state.filterString.toLowerCase();
        return (name.indexOf(filterString) != -1);
    },

    filterChange: function(event) {
        this.setState({filterString: event.target.value});
    },

    filterNotEmpty: function(element) {
        return typeof element != "undefined";
    },

    handleDataFileDelete: function(df) {
        this.props.dfs.remove(df);
    },

    render: function() {
        var self = this, showBody;
        var accordion = this.props.dfs.map(function(df) {
            showBody = (df.id === self.props.showBodyDataFile);
            if (self.filterName(df.get('name'))) {
                return (
                    <AccordionGroupReact df={df} key={df.id} dfs={self.props.dfs}
                     handleDataFileDelete={self.handleDataFileDelete}
                     handleClick={self.props.handleDataFileSelect}
                     showBody={showBody}
                    />
                );
            }
        }).filter(this.filterNotEmpty);

        return (
            <div className="row-fluid">
                <div className="span12">
                    <FindFileReact handleChange={this.filterChange} />
                    <div className="dm-header">
                        <div className="row-fluid">
                            <div className="span3"><span className="dm-col-offset">Filename </span></div>
                            <div className="span5">Current status &amp; Latest log info</div>
                            <div className="span2 text-center">Number of datasets</div>
                            <div className="span2 text-center">Actions</div>
                        </div>
                    </div>

                    <div className="accordion" id="dm-list">
                        {accordion.length ? accordion : <h4>No matches found</h4>}
                    </div>
                </div>
            </div>
        );
    }
});

var FindFileReact = React.createClass({
    render: function() {
        return (
            <div className="search-panel">
                <span className="icon icon-white icon-search"></span>
                <input type="text" placeholder="Search by filename" className="search-box" onChange={this.props.handleChange} />
            </div>
        );
    }
});

var RootComponent = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        var collections = [this.props.dfs, this.props.datasetWizard, this.props.ensembleWizard];
        this.props.dfs.forEach(function(df) {
            collections.push(df.parseLogs);
        });
        return collections;
    },

    getInitialState: function() {
        return {filterString: '', showBodyDataFile: undefined};
    },

    handleDataFileSelect: function(df) {
        if (df.id === this.state.showBodyDataFile) {
            this.setState({showBodyDataFile: false});  // hide this body
        } else {
            this.setState({showBodyDataFile: df.id});  // show this body
        }
    },

    render: function() {
        Router = this.props.router;
        switch (this.props.router.currentRoute) {
            case "dataWizard":
                return <DatasetWizardRoot wizard={this.props.datasetWizard} dfs={this.props.dfs} handleDataFileSelect={this.handleDataFileSelect} />;
            case "ensWizard":
                return <EnsembleWizardRoot wizard={this.props.ensembleWizard} dfs={this.props.dfs} />;
            default:
                return <DataFileListReact showBodyDataFile={this.state.showBodyDataFile} dfs={this.props.dfs} handleDataFileSelect={this.handleDataFileSelect} />;
        }
    }
});

module.exports = RootComponent;
