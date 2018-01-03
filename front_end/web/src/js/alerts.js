/* global module */
/* global _ */

/* format of alert: message, color, timeout.
 *  color: success = green, error = red, info = blue, warning = yellow
 *  timeout: 1000 = 1 second, if not specified alert will be live until
 *  user close it */

var messages = {
    ensembleSettingsChanged: 'Settings have been changed, apply them to take effect.',
    ensembleSettingsChangedStop: 'Settings have been changed, stop training to apply them.',
    ensembleSettingsErrors: 'Settings have errors. Please fix them.',
    validateMaxGtMin: 'Maximum value should be greater than minimum.',
    valudateMinLtMax: 'Minimum value should be lower than maximum.',
    datafileNeedReparse: 'To use this datafile again, please reparse it.',
    simpleError: 'Error. Please refresh your browser and try again.'
};

var alerts = {
    ensembleSettingsSaved: ['Ensemble settings was saved.', 'success', 2000],
    ensembleResumed: ['Ensemble #<%= id %> started.', 'success', 10000],
    ensembleStopped: ['Ensemble #<%= id %> stopped.', 'warning', 10000],
    ensembleShared: ['Ensemble shared.', 'success'],
    oneMoreModelAdded: ['New model added to the ensemble.', 'success', 10000]
};

var trigger = function(model, vars) {
    "use strict";
    var values = _.clone(alerts[this]);
    values.unshift('alert');
    values[1] = _.template(values[1])(vars);
    model.trigger.apply(model, values);
};

var getXhrErrorParser = function(model){
    "use strict";
    return function(xhr) {
        var problem = JSON.parse(xhr.responseText).problem, message;
        if (typeof problem === 'string') {
            message = problem;
        } else if ('__all__' in problem) {
            message = problem.__all__[0];
        } else {
            message = JSON.stringify(problem);
        }
        model.trigger('alert', message, 'error');
    };
};

module.exports = {
    alerts: alerts,
    msg: messages,
    getXhrErrorParser: getXhrErrorParser
};

for (var key in alerts) {
    if (alerts.hasOwnProperty(key)) {
        if (module.exports.hasOwnProperty(key)) {
            throw "Alert redifinition";
        }
        module.exports[key] = trigger.bind(key);
    }
}
