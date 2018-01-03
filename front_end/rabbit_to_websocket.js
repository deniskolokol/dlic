var BROKER_PASSWORD = process.env.BROKER_PASSWORD,
    BROKER_VHOST = process.env.BROKER_VHOST,
    BROKER_HOST = process.env.BROKER_HOST,
    BROKER_PORT = process.env.BROKER_PORT,
    BROKER_USER = process.env.BROKER_USER;

var BROKER_PASSWORD = "ija9fj432ertuerthjfsa";
var BROKER_VHOST = "ersatz";
var BROKER_HOST = "localhost";
var BROKER_PORT = "5672"; 
var BROKER_USER = "ersatz";

var broker_url = "amqp://" + BROKER_USER + ":" + BROKER_PASSWORD + "@" + BROKER_HOST + ":" + BROKER_PORT + "/" + BROKER_VHOST;

var http = require('http');
var server = http.createServer().listen(4000);
var io = require('socket.io').listen(server);
var context = require('rabbit.js').createContext(broker_url);

io.on("connection", function(socket) {
  console.log("client connected!");
  console.log("BROKER_URL is " + broker_url);

  var statsSub = context.socket('SUBSCRIBE');
  var logsSub = context.socket('SUBSCRIBE', {routing: 'topic'});

  // user can only subscribe to a single ensemble's models training at a time,
  // this holds the key for that subscription.
  var ensembleTrainSubKey = null;

  statsSub.setEncoding('utf-8');
  logsSub.setEncoding('utf-8');

  // subscribe to model stats
  statsSub.connect('livestats', function() {
    console.log("subscribed => livestats");
  });

  // handle stats
  statsSub.on('data', function(data) {
    // node doesn't know about numpy so we adjust
    data = data.replace(': -Infinity', ': "-Infinity"');

    try {
      var payload = JSON.parse(data);
    } catch (e) {
      console.log('Error parsing stats: ' + e.toString());
      return;
    }
    var eventName = "api:model:" + payload.model + ":stats:read";
    console.log("Stats for " + eventName);
    socket.emit(eventName, [payload.data]);
  });

  socket.on("model:logs:subscribe", function(data, callback) {
    // make sure ensembleId and modelId are present
    if (!data.ensembleId || !data.modelId) {
      callback(false);
      return;
    }

    // IMPORTANT: we should check if the current user is really
    // the owner of ensemble where the model belongs

    // routing key for any incoming logs of any model under this ensemble
    var routingKey = 'ensemble.' + data.ensembleId + '.#';

    // if user is not yet subscribed to any ensemble's models training
    // we create one, or subscribed but to a different one, we
    // disconnect the old one and create new subscription
    if (!ensembleTrainSubKey || (ensembleTrainSubKey && ensembleTrainSubKey !== routingKey)) {
      if (ensembleTrainSubKey) logsSub.close();
      console.log('subscribing to logs of model:' + data.modelId);
      console.log('subscribing to ' + routingKey);
      logsSub.connect('training_logs', routingKey, function() {
        ensembleTrainSubKey = routingKey;
      });
    }

    callback(true);
  });

  logsSub.on('data', function(data) {
    try {
      var payload = JSON.parse(data);
    } catch (e) {
      console.log('Error parsing logs: ' + e.toString());
      return;
    }
    var key = 'model:' + payload.modelId + ':training:logs';
    console.log('Logs for ' + key);
    socket.emit(key, payload.data);
  });

  socket.on("disconnect", function() {
    statsSub.close();
    logsSub.close();
    console.log("disconnected!");
  });

  socket.on("error", function() {
    console.log(arguments);
  });
});
