var fs = require('fs');
var exec = require('child_process').exec;
var express = require('express');
var app = express();
var walk = require('walk');


function isRunning(callback) {
  var walker  = walk.walk('./', {
    followLinks: false,
    filters: ['results', 'node_modules', 'datasets']
  });

  walker.on('file', function(root, stat, next) {
    if (stat.name.substring(0, 7) === 'running') {
      callback(true, stat.name.split("_")[1]);
    } else {
      next();
    }
  });

  walker.on('end', function() {
    callback(false);
  });
}

app.use('/results', express.static(__dirname + '/results'));
app.get('/run', function(req, res) {
  var timestamp = new Date().toISOString()
    .replace(/\..+/, '')
    .replace(/:/g, '')
    .replace(/-/g, '')
    .replace(/T/, '--');
  isRunning(function(running, filename) {
    if (running) {
      res.send("There's already a running test, you can access its result <a href=\"/results/" + filename + "\">here</a> once ready.");
    } else {
      var source = "running_" + timestamp + ".txt";
      exec("mocha -b -R PlainSpec run.js | tee " + source, {env: process.env}, function(error, stdout, stderr) {
        console.log(stderr);
        fs.renameSync('./' + source, './results/' + source.split('_')[1]);
      });
      res.send('You access the result <a href="/tests/results/' + timestamp + '.txt">here</a> once ready.');
    }
  });
});

app.listen(3000, function() {
  console.log("Listening on port 3000");
});
