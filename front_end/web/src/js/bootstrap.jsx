/** @jsx React.DOM */
/* global React */
/* global _ */

"use strict";

var Utils = require('./Utils');

var BootstrapAlert = React.createClass({
    render: function() {
        var type = this.props.type, classes;
        if (type) {
            classes = 'alert alert-' + type;
        } else {
            classes = 'alert';
        }
        return (<div className={classes}>
                     <button className="close"
                      onClick={this.props.handleClose} type="button">×</button>
                     <span dangerouslySetInnerHTML={{__html: this.props.message}} />
               </div>);
    }
});

var Switch = React.createClass({
    componentDidMount: function() {
        var value = this.props.value || false,
            handleChange = this.props.handleChange,
            rootNode = this.getDOMNode();
        $(rootNode).bootstrapSwitch();
        $(rootNode).bootstrapSwitch('setState', value, true);
        //TODO: use react event
        $(rootNode).on('switch-change', function(_, data) {
            handleChange(data.value);
        });
    },

    componentWillUnmount: function() {
        $(this.getDOMNode()).off('switch-change');
    },

    render: function() {
        return (
            <div id='emailSwitch' className="switch-mini" data-on="success" data-off="default">
                <input type="checkbox" />
            </div>
        );
    }
});

var BootstrapInListAlert = React.createClass({
    componentDidMount: function() {
        if (this.props.seconds !== undefined) {
            var timeoutId = setTimeout(this.handleHidden, this.props.seconds);
            this.setState({timeoutId: timeoutId});
        }
    },
    getInitialState: function() {
        return {};
    },
    handleHidden: function() {
        if (this.state.timeoutId !== undefined) {
            clearTimeout(this.state.timeoutId);
        }
        $(this.getDOMNode()).hide();
        this.props.handleHidden(this.props.key);
    },
    render: function() {
        var type = this.props.type, classes;
        if (type) {
            classes = 'alert alert-' + type;
        } else {
            classes = 'alert';
        }
        return (<div className={classes}>
                     <button className="close"
                      onClick={this.handleHidden} type="button">×</button>
                     <span dangerouslySetInnerHTML={{__html: this.props.message}} />
               </div>);
    }
});

var AlertList = React.createClass({
    componentDidMount: function() {
        this.props.models.forEach(function(model) {
            model.on('alert', this.addAlert, this);
        }, this);
    },

    componentWillUnmount: function() {
        this.props.models.forEach(function(model) {
            model.off(null, null, this);
        }, this);
    },

    getInitialState: function() {
        return {alerts: {}};
    },

    addAlert: function(message, type, seconds) {
        var alerts = _.clone(this.state.alerts);
        alerts[Utils.uuid()] = {message: message, type: type, seconds: seconds};
        this.setState({alerts: alerts});
    },

    removeAlert: function(key) {
        var alerts = _.clone(this.state.alerts);
        delete alerts[key];
        this.setState({alerts: alerts});
    },

    render: function(key) {
        var alertsComponent = null, _alert, alerts = this.state.alerts,
            handleHidden=this.removeAlert;
        alertsComponent = Object.keys(alerts).map(function(key) {
            _alert = alerts[key];
            return <BootstrapInListAlert
                       message={_alert.message}
                       seconds={_alert.seconds}
                       type={_alert.type}
                       key={key}
                       handleHidden={handleHidden} />;
        }).reverse();
        return <div>{alertsComponent}</div>;
    }
});

var BootstrapButton = React.createClass({
    render: function() {

        return this.transferPropsTo(
            <a role="button" className="btn">
                {this.props.children}
            </a>
        );
    }
});

var BootstrapSelect = React.createClass({

    handleChange: function(event) {
        this.setState({value: event.target.value});
    },

    getInitialState: function() {
        return {value: this.props.value};
    },

    render: function() {
        var options = this.props.values.map(function(val) {
                return (<option key={val[0]} value={val[0]}>
                            {val[1]}
                        </option>);
            });
        return <select defaultValue={this.state.value} onChange={this.handleChange}>{options}</select>;
    }
});

var BootstrapSimpleSelect = React.createClass({
    render: function() {
        var options = this.props.values.map(function(val) {
                return (<option key={val[0]} value={val[0]}>
                            {val[1]}
                        </option>);
            });
        return <select value={this.props.value} onChange={this.props.handleChange}>{options}</select>;
    }
});

var BootstrapModal = React.createClass({
    componentDidMount: function() {
        $(this.getDOMNode()).modal({backdrop: 'static', keyboard: false, show: false});
    },
    componentWillUnmount: function() {
        $(this.getDOMNode()).off('hidden', this.handleHidden);
    },
    close: function() {
        $(this.getDOMNode()).modal('hide');
    },
    open: function() {
        $(this.getDOMNode()).modal('show');
    },
    render: function() {
        var confirmButton = null;
        var cancelButton = null;

        if (this.props.confirm) {
            confirmButton = (
                <BootstrapButton
                    href="#"
                    onClick={this.handleConfirm}
                    className={this.props.confirmButtonClass}>
                    {this.props.confirm}
                </BootstrapButton>
            );
        }
        if (this.props.cancel) {
            cancelButton = (
                <BootstrapButton href="#" onClick={this.handleCancel}>
                    {this.props.cancel}
                </BootstrapButton>
            );
        }

        return (
            <div className={"modal hide fade " + this.props.classes}>
                <div className="modal-header">
                    <button
                        type="button"
                        className="close"
                        onClick={this.handleCancel}
                        dangerouslySetInnerHTML={{__html: '&times'}}
                    />
                    <h3>{this.props.title}</h3>
                </div>
                <div className="modal-body">
                    {this.props.children}
                </div>
                <div className="modal-footer">
                    {cancelButton}
                    {confirmButton}
                </div>
            </div>
       );
    },
    handleCancel: function(e) {
        e.preventDefault();
        if (this.props.onCancel) {
            this.props.onCancel();
        }
    },
    handleConfirm: function(e) {
        e.preventDefault();
        if (this.props.onConfirm) {
            this.props.onConfirm();
        }
    }
});

var BootstrapSlider = React.createClass({
    getInitialState: function() {
        return {sliderValue: 0};
    },
    componentDidMount: function() {
        var self = this;
        var slider = this.refs.slider.getDOMNode();
        $(slider).slider({
            range: 'min',
            min: this.props.min,
            max: this.props.max,
            step: this.props.step,
            value: this.props.value,
            create: function(event, ui) {
                if (self.props.handleSlide) {
                    self.props.handleSlide(self.props.value);
                }
                if (self.props.value === undefined) {
                    self.setState({sliderValue: 0});
                } else {
                    self.setState({sliderValue: self.props.value});
                }
            },
            slide: function(event, ui) {
                if (self.props.handleSlide) {
                    self.props.handleSlide(ui.value);
                }
                self.setState({sliderValue: ui.value});
            }
        });
    },
    render: function() {
        return (
            <div>
                {this.props.percentage ? <div className="slider-value">{this.state.sliderValue}{this.props.suffix}</div> : '' }
                <div className="slider" ref="slider"></div>
            </div>
        );
    }
});

module.exports = {
    Modal: BootstrapModal,
    Button: BootstrapButton,
    Select: BootstrapSelect,
    SimpleSelect: BootstrapSimpleSelect,
    Alert: BootstrapAlert,
    AlertList: AlertList,
    Slider: BootstrapSlider,
    Switch: Switch
};
