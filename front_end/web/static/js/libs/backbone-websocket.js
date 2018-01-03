(function(Backbone, $, _, io) {

  var urlError = function(){ throw new Error('A "url" property or function must be specified.'); };
  var socketError = function() { throw new Error("Missing socket on options, model or window."); };
  var eventEmit = io.Socket.prototype.emit;

  /**
   * Mimic Backbone.sync over websocket
   * Usage:
   * var Collection = Backbone.Collection.extend({
   *   url: '/api/foo',
   *   model: Backbone.Model,
   *   sync: Backbone.socketSync
   * });
   *
   * var Model = Backbone.Model.extend({
   *   url: '/api/foo/bar',
   *   sync: Backbone.socketSync
   * }))();
   */
  Backbone.socketSync = function(method, model, options) {
    var opts = _.extend({}, options);
    var defer = $.Deferred();
    var promise = defer.promise();
    var namespace;
    var params;
    var socket;

    opts.url = (opts.url) ? _.result(opts, "url") : (model.url) ? _.result(model, "url") : void 0;

    // throw error if there's no URL
    if (!opts.url) urlError();

    // transform URL into namespace
    var parsedUrl = Backbone.Model.prototype.namespace.call(this, opts.url);
    namespace = parsedUrl[0];
    params = parsedUrl[1];

    // determine what data we're sending, and ensure
    // id is present if we're performing a PATCH call
    if (!opts.data && model) opts.data = opts.attrs || model.toJSON(options) || {};
    if (!opts.data.id && opts.patch === true && model) opts.data.id = model.id;

    // determine which websocket to use - set in options or on model
    socket = opts.socket || model.socket || window.socket;
    if (!socket) socketError();

    // rethrow socketio thrown errors
    socket.onError(function(error) {
      throw error.description;
    });

    var eventName = namespace + params + method;
    console.log("Backbone.Socket: listening to " + eventName);
    socket.bind(eventName, function(response) {
      if (_.isFunction(options.success)) options.success(response);
      defer.resolve(response);
    });

    // send our namespaced method and the model+opts data
    socket.send(eventName, opts.data);

    // trigger the request event on the model, as per backbone spec
    model.trigger("request", model, promise, opts);

    // return the promise for any chaining
    return promise;
  };

  /**
   * Convert URL into namespace
   * ie. /api/ensemble/12 => api:ensemble:12:
   * @param {string} url
   */
  Backbone.Model.prototype.namespace = function(url) {
    url = url || this.url();

    // preserve GET params
    var tmp = url.split("?");
    var segment = tmp[0].replace(/^\/+|\/+$/g, "").replace(/\//g, ":") + ":";
    var params = "";
    if (tmp.length > 1) {
      params = tmp[1].split("&").join(":") + ":";
    }
    return [segment, params];
  };

})(Backbone, jQuery, _, io);
