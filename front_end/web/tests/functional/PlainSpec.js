var Base = require('./node_modules/mocha/lib/reporters/base'),
  ms = require('./node_modules/mocha/lib/ms'),
  cursor = Base.cursor,
  color = Base.color;

exports = module.exports = PlainSpec;

function PlainSpec(runner) {
  Base.call(this, runner);

  var self = this,
      stats = this.stats,
      indents = 0,
      n = 0;

  function indent() {
    return Array(indents).join('  ');
  }

  runner.on('start', function(){
    console.log();
  });

  runner.on('suite', function(suite){
    ++indents;
    console.log('%s%s', indent(), suite.title);
  });

  runner.on('suite end', function(suite){
    --indents;
    if (1 == indents) console.log();
  });

  runner.on('pass', function(test){
    var fmt = indent() + '  pass - %s (%dms)';
    console.log(fmt, test.title, test.duration);
  });

  runner.on('fail', function(test, err){
    console.log(indent() + '  fail - %d) %s', ++n, test.title);
  });

  runner.on('end', this.epilogue.bind(self));
}

Base.prototype.epilogue = function() {
  var stats = this.stats;
  var tests;
  var fmt;

  console.log();

  // passes
  fmt = '  %d passing (%s)';

  console.log(fmt, stats.passes || 0, ms(stats.duration));

  // pending
  if (stats.pending) {
    fmt = '  %d pending';
    console.log(fmt, stats.pending);
  }

  // failures
  if (stats.failures) {
    fmt = '  %d failing';
    console.error(fmt, stats.failures);
    Base.list(this.failures);
    console.error();
  }

  console.log();
};

PlainSpec.prototype.__proto__ = Base.prototype;
