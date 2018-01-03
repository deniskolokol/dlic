var path = require("path"),
    mime = require("mime"),
    fs = require("fs"),
    client = require("./client").client,
    chai = require("chai"),
    assert = chai.assert,
    expect = chai.expect;

// test credentials
var TEST_SERVER_URL = process.env.TEST_SERVER_URL,
    TEST_SERVER_EMAIL = process.env.TEST_SERVER_EMAIL,
    TEST_SERVER_PASSWORD = process.env.TEST_SERVER_PASSWORD,
    IRIS_ACADEMIC_FILENAME = "iris_academic.zip",
    IRIS_ACADEMIC_FILE = path.resolve(__dirname, "datasets", IRIS_ACADEMIC_FILENAME);

describe("test uploading dataset, training and predicting", function() {
  this.timeout(99999999);

  var dashboardUrl = TEST_SERVER_URL + "/dashboard/?test=true";

  before(function(done) {
    client
      .init()
      .windowHandleSize({width: 1024, height: 768})
      .url(dashboardUrl)

      // set the following cookie so the tour won't fire
      .setCookie({name: "tourwasplayed-dataset-created", value: "1"})
      .setCookie({name: "tourwasplayed-datafile-upload", value: "1"})
      .setCookie({name: "tourwasplayed-dashboard-train", value: "1"})
      .setCookie({name: "tourwasplayed-predict-images", value: "1"})

      .call(done);
  });

  describe("logging-in to dashboard", function() {
    it("should be able to login", function(done) {
      client
        .element("#loginForm", function(err, result) {
          // make sure there was no error locating login form
          assert.notOk(err, "Unable to locate login form");

          // fill-up login form and submit
          client
            .setValue("#login_username", TEST_SERVER_EMAIL)
            .setValue("#login_password", TEST_SERVER_PASSWORD)
            .submitForm("#loginForm", function() {
              client.url(function(err, res) {
                assert.equal(res.value, dashboardUrl, "URL after login doesn't match " + dashboardUrl);
              });
            });
        })
        .call(done);
    });

    it("should have upload button", function(done) {
      client
        .element("#dataUpload form", function(err, result) {
          assert.notOk(err, "Unable to locate upload dataset form");
        })
        .call(done);
    });
  });

  describe("upload iris-academic dataset", function() {
    it("should be able to upload dataset", function(done) {
      client
        .chooseFile("#dataUpload form #file", IRIS_ACADEMIC_FILE, function(err, res) {
          // wait for the listed filename and make sure its present
          setTimeout(function() {
            client.getText("//*[@id='dm-list']/div[1]/div/a/div/div/div[1]/div/strong", function(err, text) {
              assert.equal(text, IRIS_ACADEMIC_FILENAME, "Unable to find listed uploaded dataset");
              done();
            });
          }, 5000);
        });
    });

    it("should have ready status", function(done) {
      enableTestUtils(client, function() {
        var attempts = 0;
        var timer = setInterval(function() {
          client.getText("//*[@id='dm-list']/div[1]/div/a/div/div/div[2]/span[1]", function(err, text) {
            attempts += 1;
            if (text === "ready") {
              clearInterval(timer);
              done();
            } else if (attempts === 5) {
              assert.notOk(false, "Parsing dataset took longer than 10 seconds");
            }
          });
        }, 2000);
      });
    });
  });

  describe("create dataset with all available filters", function() {
    it("should be able to expand dataset", function(done) {
      // get first dataset since new uploads always stays on top first
      client
        .click("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//div[@class='dm-item']", function(err) {
          assert.notOk(err, "Unable to expand dataset");

          client.waitFor("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//div[@class='accordion-body']", 500, function(err) {
            assert.notOk(err, "Unable to find body of expanded dataset");

            client.element("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//span[contains(text(), 'Create Dataset')]", function(err, res) {
              assert.notOk(err, "Unable to find 'Create Dataset' button");
            });
          });
        })
        .call(done);
    });

    // columns filter
    it("should be able to select columns", function(done) {
      client
        .click("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//span[contains(text(), 'Create Dataset')]", function(err) {
          assert.notOk(err, "Error while clicking 'Create Dataset' button");

          client
            .getText("//div[@class='panel-body']//h3", function(err, text) {
              assert.notOk(err, "Unable to get title of wizard panel");
              assert.equal(text, "SELECT COLUMNS", "First panel doesn't match 'SELECT COLUMNS'");

              // drag column#5 to output columns
              client.execute(function() {
                var fakeEvent = {
                  dataTransfer: {
                    getData: function() {
                      return '{"name":"5","type":"S","index":4}';
                    }
                  },
                  preventDefault: function() {}
                };
                React.addons.TestUtils.Simulate.drop($("#df-list > div > div > div:nth-child(1)")[0], fakeEvent);
              }, [], function(err, res) {
                // click NEXT STEP button
                client.click("//div[@class='panel-body']//span[contains(text(), 'Next step')]", function(err) {
                  assert.notOk(err, "Error clicking 'Next step' button");

                  // verify that its added on the right panel
                  client.element("(//div[@class='filters'])[2]//span[contains(text(), 'Select Columns')]", function(err) {
                    assert.notOk(err, "Unable to find applied 'Select Columns' filter");
                  });
                });
              });
            });
        })
        .call(done);
    });

    // normalize filter
    it("should be able to apply normalize filter", function(done) {
      client
        .click("(//div[@class='filters'])[1]//span[contains(text(), 'Normalize')]", function(err) {
          assert.notOk(err, "Error clicking 'Normalize' filter");

          // click NEXT STEP button
          client.click("//div[@class='panel-body']//span[contains(text(), 'Next step')]", function(err) {
            assert.notOk(err, "Error clicking 'Next step' button");

            // verify that its added on the right panel
            client.element("(//div[@class='filters'])[2]//span[contains(text(), 'Normalize')]", function(err) {
              assert.notOk(err, "Unable to find applied 'Normalize' filter");
            });
          });
        })
        .call(done);
    });

    // shuffle filter
    it("should be able to apply shuffle filter", function(done) {
      client
        .click("(//div[@class='filters'])[1]//span[contains(text(), 'Shuffle')]", function(err) {
          assert.notOk(err, "Error clicking 'Shuffle' filter");

          // click NEXT STEP button
          client.click("//div[@class='panel-body']//span[contains(text(), 'Next step')]", function(err) {
            assert.notOk(err, "Error clicking 'Next step' button");

            // verify that its added on the right panel
            client.element("(//div[@class='filters'])[2]//span[contains(text(), 'Shuffle')]", function(err) {
              assert.notOk(err, "Unable to find applied 'Shuffle' filter");
            });
          });
        })
        .call(done);
    });

    // balance filter, default: uniform
    it("should be able to apply balance filter", function(done) {
      client
        .click("(//div[@class='filters'])[1]//span[contains(text(), 'Balance')]", function(err) {
          assert.notOk(err, "Error clicking 'Balance' filter");

          // click NEXT STEP button
          client.click("//div[@class='panel-body']//span[contains(text(), 'Next step')]", function(err) {
            assert.notOk(err, "Error clicking 'Next step' button");

            // verify that its added on the right panel
            client.element("(//div[@class='filters'])[2]//span[contains(text(), 'Balance')]", function(err) {
              assert.notOk(err, "Unable to find applied 'Balance' filter");
            });
          });
        })
        .call(done);
    });

    // split filter, default: 70%/30%
    it("should be able to apply split filter", function(done) {
      client
        .click("(//div[@class='filters'])[1]//span[contains(text(), 'Split')]", function(err) {
          assert.notOk(err, "Error clicking 'Balance' filter");

          // click NEXT STEP button
          client.click("//div[@class='panel-body']//span[contains(text(), 'Next step')]", function(err) {
            assert.notOk(err, "Error clicking 'Next step' button");

            // verify that its added on the right panel
            client.element("(//div[@class='filters'])[2]//span[contains(text(), 'Split')]", function(err) {
              assert.notOk(err, "Unable to find applied 'Split' filter");
            });
          });
        })
        .call(done);
    });

    it("create dataset", function(done) {
      client
        .click("//div[@class='panel-body']//span[contains(text(), 'Create Dataset')]", function(err) {
          assert.notOk(err, "Error clicking 'Create Dataset' button");

          // wait for modal to slide-in
          setTimeout(function() {
            client
              .click("(//div[@class='panel-body']/div/div)[2]//a[contains(text(), 'OK')]", function(err) {
                assert.notOk(err, "Error clicking 'OK' button on modal");

                client
                  .waitFor("(//div[@id='dm-list']/div[@class='accordion-group'])[1]", 500, function(err) {
                    assert.notOk(err, "Error while waiting for added dataset");

                    // make sure the dataset train and test are listed
                    client
                      .element("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//ul[@class='datasets-list']/li//span[contains(text(), 'iris_academic_test')]", function(err, res) {
                        assert.notOk(err, "Unable to find test dataset");
                      })
                      .element("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//ul[@class='datasets-list']/li//span[contains(text(), 'iris_academic_train')]", function(err, res) {
                        assert.notOk(err, "Unable to find train dataset");
                      });
                  });
              })
              .call(done);
          }, 500);

        });
    });
  });

  // DeepNet: Rectified Linear
  describe("create ensemble with 'DeepNet' model and 'Rectified Linear'", function() {
    it("should have 'Create Ensemble' button", function(done) {
      client
        .element("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//span[contains(text(), 'Create Ensemble')]", function(err, res) {
          assert.notOk(err, "Unable to find 'Create Ensemble' button");

          client
            .click("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//span[contains(text(), 'Create Ensemble')]", function(err) {
              assert.notOk(err, "Error while clicking 'Create Ensemble' button");
            });
        })
        .call(done);
    });

    it("should be able to select model", function(done) {
      client
        .click("(//div[@class='filters'])[1]//a[contains(text(), 'DeepNet')]", function(err) {
          assert.notOk(err, "Error clicking 'DeepNet' model");

          client.execute(function() {
            var $select = $(".panel-body-step1 > div > div > div:nth-child(3) > div:nth-child(1) > select");
            $select.val("MLP_RECTIFIED");
            React.addons.TestUtils.Simulate.change($select[0]);
          }, [], function() {
            client.click("//div[@class='panel-body']//span[contains(text(), 'Next step')]", function(err) {
              assert.notOk(err, "Error clicking 'Next step' button");

              // pick LET ME DO IT so we can set iteration to 10,
              // this makes tests run faster since we're interested
              // in the actual training result anyway.
              client.click("//*[@id='df-list']/div/div[2]/div[2]/div[2]/div/div/a[2]", function(err) {
                assert.notOk(err, "Error clicking 'LET ME DO IT' button");

                client
                  .setValue("//*[@id='df-list']/div/div[2]/div[2]/div[2]/div/div[1]/div[1]/table/tbody/tr[1]/td[2]/input", "10")
                  .click("//*[@id='df-list']/div/div[2]/div[2]/div[2]/div/div[2]/a[2]", function(err) {
                    assert.notOk(err, "Error clicking 'FINISH' button");

                    // wait till page is fully loaded then click start
                    setTimeout(function() {
                      client.click("//*[@id='ensemble-view']/div/div[3]/div[2]/div[2]/div/button", function(err) {
                        assert.notOk(err, "Error clicking 'START' button");
                        done();
                      });
                    }, 5000);
                  });
              });

            });
          });
        });
    });

    it("should be able to train initial model", function(done) {
      var attempts = 0;
      var timer = setInterval(function() {
        attempts += 1;
        getEnsembleModelStatus(client, function(status) {
          if (status === "Finished") {
            clearInterval(timer);
            done();
          } else if (attempts === 10) {
            assert.notOk(false, "Training model took longer than 5 minutes");
          }
        });
      }, 1000 * 30);  // every 30 seconds for the next 5 minutes
    });
  });

  // Predict with DeepNet: Rectified Linear
  describe("prediction with 'DeepNet' model and 'Rectified Linear'", function() {
    predictWithCSV(client, 2000 * 60);
  });

  // DeepNet: Sigmoid
  describe("create ensemble with 'DeepNet' model and 'Sigmoid'", function() {
    // first go back to dashboard
    it("should be able to go back and expand uploaded data", function(done) {
      client
        .click("//a[@class='brand']", function(err) {
          assert.notOk(err, "Error clicking 'Data' navigation menu");

          // expand the uploaded file
          client
            .click("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//div[@class='dm-item']", function(err) {
              assert.notOk(err, "Unable to expand dataset");

              client.waitFor("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//div[@class='accordion-body']", 500, function(err) {
                assert.notOk(err, "Unable to find body of expanded dataset");
              });
            });
        })
        .call(done);
    });

    it("should have 'Create Ensemble' button", function(done) {
      client
        .element("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//span[contains(text(), 'Create Ensemble')]", function(err, res) {
          assert.notOk(err, "Unable to find 'Create Ensemble' button");

          client
            .click("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//span[contains(text(), 'Create Ensemble')]", function(err) {
              assert.notOk(err, "Error while clicking 'Create Ensemble' button");
            });
        })
        .call(done);
    });

    it("should be able to select model", function(done) {
      client
        .click("(//div[@class='filters'])[1]//a[contains(text(), 'DeepNet')]", function(err) {
          assert.notOk(err, "Error clicking 'DeepNet' model");

          client.execute(function() {
            var $select = $(".panel-body-step1 > div > div > div:nth-child(3) > div:nth-child(1) > select");
            $select.val("MLP_SIGMOID");
            React.addons.TestUtils.Simulate.change($select[0]);
          }, [], function() {
            client.click("//div[@class='panel-body']//span[contains(text(), 'Next step')]", function(err) {
              assert.notOk(err, "Error clicking 'Next step' button");

              client.click("//*[@id='df-list']/div/div[2]/div[2]/div[2]/div/div/a[2]", function(err) {
                assert.notOk(err, "Error clicking 'LET ME DO IT' button");

                client
                  .setValue("//*[@id='df-list']/div/div[2]/div[2]/div[2]/div/div[1]/div[1]/table/tbody/tr[1]/td[2]/input", "10")
                  .click("//*[@id='df-list']/div/div[2]/div[2]/div[2]/div/div[2]/a[2]", function(err) {
                    assert.notOk(err, "Error clicking 'FINISH' button");

                    // wait till page is fully loaded then click start
                    setTimeout(function() {
                      client.click("//*[@id='ensemble-view']/div/div[3]/div[2]/div[2]/div/button", function(err) {
                        assert.notOk(err, "Error clicking 'START' button");
                        done();
                      });
                    }, 5000);
                  });
              });

            });
          });
        });
    });

    it("should be able to train initial model", function(done) {
      var attempts = 0;
      var timer = setInterval(function() {
        attempts += 1;
        getEnsembleModelStatus(client, function(status) {
          if (status === "Finished") {
            clearInterval(timer);
            done();
          } else if (attempts === 10) {
            assert.notOk(false, "Training model took longer than 5 minutes");
          }
        });
      }, 1000 * 30);  // every 30 seconds for the next 5 minutes
    });
  });

  // Predict with DeepNet: Sigmoid
  describe("prediction with 'DeepNet' model and 'Sigmoid'", function() {
    predictWithCSV(client, 2000 * 60);
  });

  // DeepNet: Maxout
  describe("create ensemble with 'DeepNet' model and 'Maxout'", function() {
    // first go back to dashboard
    it("should be able to go back and expand uploaded data", function(done) {
      client
        .click("//a[@class='brand']", function(err) {
          assert.notOk(err, "Error clicking 'Data' navigation menu");

          // expand the uploaded file
          client
            .click("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//div[@class='dm-item']", function(err) {
              assert.notOk(err, "Unable to expand dataset");

              client.waitFor("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//div[@class='accordion-body']", 500, function(err) {
                assert.notOk(err, "Unable to find body of expanded dataset");
              });
            });
        })
        .call(done);
    });

    it("should have 'Create Ensemble' button", function(done) {
      client
        .element("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//span[contains(text(), 'Create Ensemble')]", function(err, res) {
          assert.notOk(err, "Unable to find 'Create Ensemble' button");

          client
            .click("(//div[@id='dm-list']/div[@class='accordion-group'])[1]//span[contains(text(), 'Create Ensemble')]", function(err) {
              assert.notOk(err, "Error while clicking 'Create Ensemble' button");
            });
        })
        .call(done);
    });

    it("should be able to select model", function(done) {
      client
        .click("(//div[@class='filters'])[1]//a[contains(text(), 'DeepNet')]", function(err) {
          assert.notOk(err, "Error clicking 'DeepNet' model");

          client.execute(function() {
            var $select = $(".panel-body-step1 > div > div > div:nth-child(3) > div:nth-child(1) > select");
            $select.val("MLP_MAXOUT");
            React.addons.TestUtils.Simulate.change($select[0]);
          }, [], function() {
            client.click("//div[@class='panel-body']//span[contains(text(), 'Next step')]", function(err) {
              assert.notOk(err, "Error clicking 'Next step' button");

              client.click("//*[@id='df-list']/div/div[2]/div[2]/div[2]/div/div/a[2]", function(err) {
                assert.notOk(err, "Error clicking 'LET ME DO IT' button");

                client
                  .setValue("//*[@id='df-list']/div/div[2]/div[2]/div[2]/div/div[1]/div[1]/table/tbody/tr[1]/td[2]/input", "10")
                  .click("//*[@id='df-list']/div/div[2]/div[2]/div[2]/div/div[2]/a[2]", function(err) {
                    assert.notOk(err, "Error clicking 'FINISH' button");

                    // wait till page is fully loaded then click start
                    setTimeout(function() {
                      client.click("//*[@id='ensemble-view']/div/div[3]/div[2]/div[2]/div/button", function(err) {
                        assert.notOk(err, "Error clicking 'START' button");
                        done();
                      });
                    }, 5000);
                  });
              });

            });
          });
        });
    });

    it("should be able to train initial model", function(done) {
      var attempts = 0;
      var timer = setInterval(function() {
        attempts += 1;
        getEnsembleModelStatus(client, function(status) {
          if (status === "Finished") {
            clearInterval(timer);
            done();
          } else if (attempts === 10) {
            assert.notOk(false, "Training model took longer than 5 minutes");
          }
        });
      }, 1000 * 30);  // every 30 seconds for the next 5 minutes
    });
  });

  // Predict with DeepNet: Maxout
  describe("prediction with 'DeepNet' model and 'Maxout'", function() {
    predictWithCSV(client, 2000 * 60);
  });

  after(function(done) {
    client.end(done);
  });
});

function getEnsembleModelStatus(client, callback) {
  client
    .getText("//*[@id='ensemble-view']/div/div[3]/div[2]/div[4]/div/div/div[1]/span[6]/span[2]", function(err, inQueue) {

      // finished
      client.getText("//*[@id='ensemble-view']/div/div[3]/div[2]/div[3]/div/div/div[1]/span[6]/span[2]", function(err, finished) {
        callback(inQueue || finished);
      });
    });
}

function predictWithCSV(client, timeToWait) {
  it("should be able to visit 'Predictions Dashboard'", function(done) {
    client
      .getText("//*[@id='ensemble-view']/div/div[1]/div/div/div/div[1]/button[1]/span[2]", function(err, text) {
        assert.equal(text, "Predict", "Unable to find 'Predict' button");

        client.click("//*[@id='ensemble-view']/div/div[1]/div/div/div/div[1]/button[1]", function(err) {
          assert.notOk(err, "Error while clicking 'Predict' button");

          enableTestUtils(client, function() {
            client.waitFor("//*[@id='predict']", 1000, function(err) {
              assert.notOk(err, "Unable to find 'Predictions Dashboard'");
              done();
            });
          });
        });
      });
  });

  it("should be able to predict from browser", function(done) {
    client
      .click("//*[@id='predict']/div/div[1]/div[1]/div[2]/ul/li[1]/label", function(err) {
        assert.notOk(err, "Error while clicking 'Enter data directly into my browser' option");

        client.getAttribute("//*[@id='predict']/div/div[1]/div[2]/div[2]/ul/li[1]/label/span[1]/input", "checked", function(err, value) {
          assert.notStrictEqual(value, true, "option 'Output values' on step-2 not selected");

          var input = "5.1,3.5,1.4,0.2\n" +  // Iris-setosa
                      "7.0,3.2,4.7,1.4\n" +  // Iris-versicolor
                      "6.3,3.3,6.0,2.5";     // Iris-virginica
          client.setValue("//*[@id='predict']/div/div[2]/div[2]/div/div/div/div[2]/div/textarea", input, function(err) {
            assert.notOk(err, "Error while entering prediction input data");

            client
              .click("//*[@id='predict']/div/div[2]/div[2]/div/div/div/div[2]/button", function(err) {
                assert.notOk(err, "Error while clicking 'Go Predict' button");

                // wait for tab switch and listing of prediction item
                setTimeout(function() {
                  client.getAttribute("//*[@id='predict']/div/div[2]/div[2]/div/ul/li[2]", "class", function(err, value) {
                    assert.equal(value, "active", "'Download Results' tab is not active");

                    client.element("//*[@id='predict-list']/div[1]", function(err, res) {
                      assert.notOk(err, "Prediction item not listed");

                      client.getText("//*[@id='predict-list']/div[1]/div[1]/a/div/div/div[2]/span", function(err, text) {
                        assert.equal(text, "in queue", "Prediction's initial status is not 'In queue'");

                        // wait till prediction is finished
                        setTimeout(function() {
                          client.getText("//*[@id='predict-list']/div[1]/div[1]/a/div/div/div[2]/span", function(err, text) {
                            assert.equal(text, "finished", "Prediction's status is not 'Finished'");

                            // switch back to 'General' tab
                            client.click("//*[@id='predict']/div/div[2]/div[2]/div/ul/li[1]", function() {
                              done();
                            });
                          });
                        }, 30000);  // 20 seconds to predict

                      });
                    });
                  });
                }, 1000);

              });
          });
        });
      });
  });

  it("should be able to predict from uploaded dataset", function(done) {
    client
      .click("//*[@id='predict']/div/div[1]/div[1]/div[2]/ul/li[2]/label", function(err) {
        assert.notOk(err, "Error while clicking 'Use dataset I've already uploaded' option");

        client.getAttribute("//*[@id='predict']/div/div[1]/div[2]/div[2]/ul/li[1]/label/span[1]/input", "checked", function(err, value) {
          assert.notStrictEqual(value, true, "option 'Output values' on step-2 not selected");

          // make sure that selected dataset is test (ie. iris_academic_test)
          client.execute(function() {
            var $select = $(".tabs-pane select");
            $select.val($(".tabs-pane select option:contains('iris_academic_test')").first().val());
            React.addons.TestUtils.Simulate.change($select[0]);
          }, [], function(err, res) {
            assert.notOk(err, "Unable to find dataset for prediction");

            client
              .click("//*[@id='predict']/div/div[2]/div[2]/div/div/div/div[2]/button", function(err) {
                assert.notOk(err, "Error while clicking 'Go Predict' button");

                // wait for tab switch and listing of prediction item
                setTimeout(function() {
                  client.getAttribute("//*[@id='predict']/div/div[2]/div[2]/div/ul/li[2]", "class", function(err, value) {
                    assert.equal(value, "active", "'Download Results' tab is not active");

                    client.element("//*[@id='predict-list']/div[1]", function(err, res) {
                      assert.notOk(err, "Prediction item not listed");

                      client.getText("//*[@id='predict-list']/div[1]/div[1]/a/div/div/div[2]/span", function(err, text) {
                        assert.equal(text, "in queue", "Prediction's initial status is not 'In queue'");

                        // wait till prediction is finished
                        var attempts = 0;
                        var maxAttempts = (timeToWait / 30) / 1000;
                        var timer = setInterval(function() {
                          attempts += 1;
                          client.getText("//*[@id='predict-list']/div[1]/div[1]/a/div/div/div[2]/span", function(err, text) {
                            if (text === "finished") {
                              clearInterval(timer);
                              done();
                            } else if (attempts === maxAttempts) {
                              assert.notOk(false, "Prediction took longer than " + ((timeToWait / 1000) / 60) + " minutes");
                            }
                          });
                        }, 1000 * 30);  // every 30 seconds for the next timeToWait

                      });
                    });
                  });
                }, 1000);

              });
          });
        });
      });
  });
}

function enableTestUtils(client, callback) {
  client.execute(function() {
    if (window.location.search.indexOf("test") === -1) {
      window.location = window.location.href + '?test=true';
    }
  }, [], function() {
    setTimeout(callback, 2000);
  });
}
