var webdriverio = require("webdriverio");

exports.client = webdriverio
  .remote({
    desiredCapabilities: {
      browserName: "phantomjs"
    }
  });
