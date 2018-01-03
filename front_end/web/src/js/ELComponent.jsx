/** @jsx React.DOM */
/* global React */

"use strict";
var Utils = require('./Utils');
var Alerts = require('./alerts');
var Bootstrap = require('./bootstrap.jsx');
var BootstrapModal = Bootstrap.Modal,
    BootstrapAlert = Bootstrap.Alert;

var MetaDataItemReact = React.createClass({
    render: function() {
        return (
            <div>
                <i className={"icon icon-white " + this.props.iconClasses}></i>
                <strong>{this.props.label}:</strong><span>{this.props.value}</span>
            </div>
        );
    }
});

var RemoveEnsembleReact = React.createClass({
    openModal: function(e) {
        e.preventDefault();
        this.refs.modal.open();
    },

    closeModal: function() {
        this.refs.modal.close();
    },

    deleteEnsemble: function() {
        var en = this.props.en;
        this.closeModal();
        en.beforeDeleteRequest();
        $.ajax({
            url: '/api/ensemble/' + en.id + '/',
            type: 'DELETE',
            dataType: 'json'
        }).done(function (data) {
            en.deleteRequestDone(data);
        }).fail(function (xhr) {
            en.deleteRequestFail(xhr);
        });
    },

    render: function() {
        return (
            <div>
                <ul className="dm-file-meta">
                    <li className="clearfix">
                        <a href="#" className="btn btn-flat pull-right" title="Remove Ensemble" onClick={this.openModal}>
                            <i className="icon icon-trash"></i>
                        </a>
                    </li>
                </ul>
                <BootstrapModal
                    ref="modal"
                    confirm="Delete"
                    cancel="Cancel"
                    confirmButtonClass="btn-danger"
                    onCancel={this.closeModal}
                    onConfirm={this.deleteEnsemble}
                    title={"Delete ensemble #" + this.props.en.get('id')} >
                      <p>If you delete this ensemble, you will no longer have access to it and it will be removed permanently.</p>
                </BootstrapModal>
            </div>
        );
    }
});

var EnsembleStateReact = React.createClass({
    render: function() {
        var classes = "label no-float ",
            state = this.props.state;

        if (state === 'new' || state === 'in queue') {
            classes += "label-info";
        } else if (state === 'stopped' || state === 'empty') {
            classes += "label-warning";
        } else if (state === 'error') {
            classes += "label-important";
        } else if (state === 'training' || state === 'finished') {
            classes += "label-success";
        }

        return (
            <div className="span2 ensemble-state">
                <span className={classes}>{state}</span>
            </div>
        );
    }
});

var AccordionHeadReact = React.createClass({
    clearAlert: function() {
        this.props.en.unset('delete-request');
    },

    handleEnsembleDelete: function() {
        this.props.handleEnsembleDelete(this.props.en);
    },

    render: function() {
        var en = this.props.en;
        var date = Utils.isoDateToHumanize(en.get('created')),
            time = Utils.secondsToStr(en.get('total_time'));

        var head = null, headBody = null, alert = null, makePredictions = null;

        if (en.get('state') === 'finished' && en.get('net_type') != 'AUTOENCODER') {
            makePredictions = (
                <a href={"/predict/train-ensemble/" + en.id} className="btn btn-mini btn-gray pull-left">
                    <i className="icon icon-white icon-screenshot"></i> Make Predictions
                </a>
            );
        }

        if (en.get('delete-request') === 'done') {
            alert = <BootstrapAlert
                     type="success"
                     message={"Ensemble <strong>#" + en.get('id') + "</strong> has been successfully deleted."}
                     handleClose={this.handleEnsembleDelete}
                    />;
        } else {
            if (en.get('delete-request') === 'fail') {
                alert = <BootstrapAlert
                         type="error"
                         message={Alerts.msg.simpleError}
                         handleClose={this.clearAlert}
                        />;
            }
            if (en.get('delete-request') === 'before') {
                headBody = <div className="ajax-loader"></div>;
            } else {
                headBody = (
                    <div className="row-fluid">
                        <a className="ensemble-row-link" href={"/train-ensemble/" + en.id}>
                            <div className="span1 text-center">
                                <strong className="ensemble-id dm-col-offset">{en.get('id')}</strong>
                            </div>
                            <div className="span2">
                                <strong>{(en.get('train_dataset_name')) ? en.get('train_dataset_name') : 'Not selected'}</strong>
                            </div>
                            <EnsembleStateReact state={en.get('state')} />
                            <div className="span2">{date}</div>
                            <div className="span3">
                                <ul className="dm-file-meta">
                                    <li>
                                        <MetaDataItemReact iconClasses="icon-flag"
                                                           label="Number of models"
                                                           value={en.get('models_count')} />
                                    </li>
                                    <li>
                                        {en.get('total_time') ?
                                            <MetaDataItemReact iconClasses="icon-time"
                                                               label="Training time"
                                                               value={time} />
                                            : ''}
                                    </li>
                                </ul>
                            </div>
                        </a>
                        <div className="span2 text-center ensemble-row-actions">
                            <div className="dm-col-offset-r">
                                {makePredictions}
                                <RemoveEnsembleReact en={en} />
                            </div>
                        </div>
                    </div>
                );
            }
            head = (
                <div className={"accordion-toggle collapsed"}>
                    <div className="dm-item">
                        {headBody}
                    </div>
                </div>
            );
        }

        return (
            <div className="accordion-heading">
                {alert}
                {head}
            </div>
        );
    }
});

var AccordionGroupReact = React.createClass({
    render: function() {
        return (
            <div className="accordion-group">
                <AccordionHeadReact
                 en={this.props.en}
                 handleEnsembleDelete={this.props.handleEnsembleDelete}
                />
            </div>
        );
    }
});

var EnsemblesListReact = React.createClass({
    mixins: [Utils.BackboneMixin],


    getInitialState: function() {
        return {filterString: ''};
    },

    getBackboneModels: function() {
        var collections = [];
        this.props.ens.forEach(function(en) {
            collections.push(en);
        });
        collections.push(this.props.ens);
        return collections;
    },

    deleteEnsemble: function(ensemble) {
        this.props.ens.remove(ensemble);
    },

    filterChange: function(event) {
        this.setState({filterString: event.target.value});
    },

    filterName: function(name) {
        if(!name)
            return(0);
        name = name.toLowerCase();
        var filterString = this.state.filterString.toLowerCase();
        return (name.indexOf(filterString) != -1);
    },


    render: function() {
        var self = this;
        var accordion = this.props.ens.map(function(en) {
            if (self.filterName(en.attributes.train_dataset_name || en.attributes.test_dataset_name)) {
            return (
                <AccordionGroupReact en={en} key={en.id}
                 handleEnsembleDelete={self.deleteEnsemble}
                />
            );
            }
        });

        return (
            <div className="row-fluid">
                <div className="span12">
                    <FindFileReact  handleChange={this.filterChange} />
                    <div className="dm-header">
                        <div className="row-fluid">
                            <div className="span1 text-center"><span className="dm-col-offset">ID</span></div>
                            <div className="span2">Training data</div>
                            <div className="span2 text-center">Status</div>
                            <div className="span2">Date created</div>
                            <div className="span3">Training Details</div>
                            <div className="span2 text-center"></div>
                        </div>
                    </div>

                    <div className="accordion">
                        {accordion}
                    </div>
                </div>
            </div>
        );
    }
});


var FindFileReact = React.createClass({
    render: function() {
        return (
            <div className="search-panel ensemble-search">
                <span className="icon icon-white icon-search"></span>
                <input type="text" placeholder="Search by dataset name" className="search-box" onChange={this.props.handleChange} />
            </div>
        );
    }
});



module.exports = EnsemblesListReact;
