(function(io) {
  "use strict";

  var client = null;

  /**
   * Constructor
   * @param {string} url
   * @param {object} options
   */
  function Socket() {
    var url = window.SOCKET_URL || null;
    var options = window.SOCKET_OPTIONS || {};
    client = io(url, options);
  }

  /**
   * bind single-shot event
   * @param {string} name
   * @param {function} callback
   */
  Socket.prototype.once = function(name, callback) {
    client.once(name, callback);
  };

  /**
   * bind custom events
   * @param {string} name
   * @param {function} callback
   */
  Socket.prototype.bind = function(name, callback) {
    client.on(name, callback);
  };

  /**
   * unbind custom events
   * @param {string} name
   * @param {function} callback
   */
  Socket.prototype.unbind = function(name, callback) {
    client.removeListener(name, callback);
  };

  /**
   * connect event
   * @param {function} callback
   */
  Socket.prototype.onConnect = function(callback) {
    this.bind("connect", callback);
  };

  /**
   * error event
   * @param {function} callback
   */
  Socket.prototype.onError = function(callback) {
    this.bind("error", callback);
  };

  /**
   * disconnect event
   * @param {function} callback
   */
  Socket.prototype.onDisconnect = function(callback) {
    this.bind("disconnect", callback);
  };

  /**
   * send event
   * @param {function} callback
   */
  Socket.prototype.send = function(name, data, callback) {
    data = data || null;
    client.emit(name, data, callback);
  };

  $(function() {
    // initialize socket
    window.socket = window.socket || new Socket();
  });

})(io);
