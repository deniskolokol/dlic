<h2 id="apiv1">APIv1</h2>

<h3 id="general-info">General info</h3>

Currently, only files lower than 10Mb can be uploaded via api directly.  You can upload files with bigger size from the web interface.   
After uploading a file with web interface, you can find the file id in Data Management section on the dashboard.

<h3 id="data-management">Data management</h3>

<h4 id="upload-file">Upload file</h4>
**url: /api/upload/file/**  

  - key: api key
  - file: zip file with dataset

Example with curl:

    curl http://api.ersatz1.com/api/upload/ \
    -F key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4 \
    -F file=@/tmp/my_dataset.zip

<h4 id="upload-string">Upload string</h4>
**url: /api/upload/string/**  

  - key: api key
  - data: string with data
  - filename: name of this data file

Example with curl:

    curl http://api.ersatz1.com/api/upload/string/ \
    -F key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4 \
    -F filename='fake.ts' \
    -F data='18.08,336|1,0;18.57,308|1,0;\n19.06,213|1,0;19.06,154|1,0;'
    {"status": "success", "file_id": 67}

<h4 id="file-state">File state</h4>
**url: /api/file/state/**  

  - key: api key
  - files[]: list of file ids

Example with curl:

    curl "http://api.ersatz1.com/api/file/state/?key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4&files%5B%5D=51&files%5B%5D=52" 

Success response:

    {"files": [{"state": "Ready", "id": 52}, {"state": "Ready", "id": 51}], "state": "success"}

When file will in state "Ready" you can create an ensemble.

<h3 id="train-model">Train model</h3>
**url: /api/train/**  

<h4 id="train-model-general-keys">General keys</h4>

  - key: api key
  - models: list of the models to train
    - model_name: name of a model (MRNN, CONV, AUTOENCODER)
    - num_models: number of a model to train in the ensemble
  - file_id: id of an uploaded file that contains the training data
  - start: start training (default: false)

<h4 id="train-model-mrnn">MRNN specific</h4>

  - test_dataset: id of an uploaded file that contains the test data
  - valid_dataset: id of an uploaded file that contains the validation data
  - data_split: percentages used to divide the uploaded file (by file_id) into train, test, and valid datasets
  - out_nonlin: output nonliniarity SOFTMAX, SIGMOID, SQ_SIGMOID
    (squared), LINEAR

MRNN example:

    curl http://api.ersatz1.com/api/train/ -X POST -d \
        '{"models": [{"model_name": "MRNN", "num_models": 1}],
          "file_id": 75,
          "test_dataset": 79,
          "data_split": [70, 20, 10],
          "out_nonlin": "SOFTMAX",
          "start": true,
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

Success response:

        {"status": "success", "ensemble_id": 45, "ensemble_url": "/train-ensemble/45/"}

<h4 id="train-model-cnn">CNN specific</h4>

  - data_split: the batches from cifar that are used for training and testing

Example CNN:

    curl http://api.ersatz1.com/api/train/ -X POST -d \
        '{"models": [{"model_name": "CONV", "num_models": 1}],
          "file_id": 77,
          "data_split": ["1-5", 6],
          "start": true,
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

<h4 id="train-model-autoencoder">Autoencoder</h4>

Autoencoder Example:

    curl http://api.ersatz1.com/api/train/ -X POST -d \
        '{"models": [{"model_name": "AUTOENCODER", "num_models": 1}],
          "file_id": 75,
          "start": true,
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

<h3 id="predict">Predict</h3>

<h4 id="predict-MRNN">MRNN</h4>


  - key
  - ensemble: ensemble id
  - models: list of models
    - id: model id
    - iteration: iteration model used for prediction

*If you want to run ensemble on file*

**url: /api/ensemble/run/**

  - file_id: a file with data to be classified

If you do not specify a file_id, then the test set will be used as file_id.

    curl http://api.ersatz1.com/api/ensemble/run/ -X POST -d \
        '{"file_id": "75",
          "ensemble": 561,
          "models": [{"id": 929, "iteration": 8}, {"id": 930, "iteration": 19}],
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

Response:

    {"status": "success", "ensemble_id": 888, "iterations": [[930, 19], [929, 8]]}


*If you want to predict using raw data*

**url: /api/predict/**

  - input_data: csv like string with data to classify

Example POST:

    curl http://api.ersatz1.com/api/predict/ -X POST -d \
        '{"input_data": "1,2;3,4;5,6;",
          "ensemble": 561,
          "models": [{"id": 929, "iteration": 8}, {"id": 930, "iteration": 19}],
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

GET results example:

    curl "http://api.ersatz1.com/api/predict/?ensemble=889&key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"

Response:

    {'id': 629,
     'status': 'success',
     'state': 'FINISHED',
     'seconds_to_run': 3.61784100532532,
     'type': 'input',
     'input_data': '0.1,0.1,0.1,0.1,0.2,0.2,0.2,0.2;',
     'results': {
        'ensemble_prediction': [[[9.494099608464701e-05,
                                  3.240551753602716e-07,
                                  3.248054009663548e-05,
                                  4.789478255773361e-06,
                                  7.535973374217519e-07,
                                  0.9987983405590057,
                                  0.0003376320091774687,
                                  2.2962919754565547e-07,
                                  5.426259277866753e-06,
                                  2.1217933416110488e-13,
                                  2.233954746284355e-08,
                                  5.4999646687592385e-05,
                                  2.9031101655419e-06,
                                  0.0006671955891463521]]],
      'predictions': [
            {
                'model': 289,
                'hidden_activations': [[[0.9999975562095642,
                                         -0.9999921321868896,
                                         0.999930739402771,
                                         -0.9999890327453613,
                                         0.9643383026123047,
                                         -0.9752657413482666]]],
                'results': [[[2.184874947630533e-09,
                              4.1179002430169476e-09,
                              1.10505915529302e-09,
                              1.189897957942776e-08,
                              3.1994389360079367e-09,
                              0.9995519518852234,
                              0.00044808423263020813,
                              2.033362367370728e-10,
                              2.759651014649922e-11,
                              1.4950458134942862e-13,
                              8.95413910660843e-14,
                              5.64915891843043e-11,
                              3.8450476136375755e-10,
                              1.5066093927984525e-09]]]}
           {
                'model': 288,
                'hidden_activations': [[[0.95543372631073,
                                         -0.4228708744049072,
                                         0.41271185874938965,
                                         0.9300063848495483,
                                         0.8173874616622925,
                                         -0.4386230707168579]]],
                'results': [[[0.0001898798072943464,
                              6.439924504775263e-07,
                              6.495997513411567e-05,
                              9.567057531967293e-06,
                              1.503995235907496e-06,
                              0.9980447292327881,
                              0.0002271797857247293,
                              4.5905505885457387e-07,
                              1.085249095922336e-05,
                              2.7485408697278113e-13,
                              4.467900538429603e-08,
                              0.00010999923688359559,
                              5.805835826322436e-06,
                              0.0013343896716833115]]]
                }
            ]
        }
    }


<h4 id="predict-CNN">CNN</h4>

**url: /api/predict/image**

CNN prediction differs from other api calls because of the uploaded files.  
You should use Content-Type multipart/form-data.

  - key
  - model: id of the finished CNN model
  - file-[0..n]: binary image file

POST example:

    curl http://api.ersatz1.com/api/predict/image/ \
        -F model=933 \
        -F key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4 \
        -F file-0=@~/Desktop/bird.jpg \
        -F file-1=@~/Desktop/truck.jpg

Response:

    {"status": "success", "ensemble_id": 886, "iterations": [[933, 99]]}

Example GET:


    curl "http://api.ersatz1.com/api/predict/?ensemble=886&key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"

Response with state "NEW" (no results yet):

    {"status": "success", "state": "NEW"}

Response after retry:

    {"id": 886,
     "predicting_time": 0.295861959457397,
     "results": {"img_labels": [{"filename": "file-1--truck.jpg",
                                 "labels": [[0.9984059929847717, "truck"],
                                            [0.001057328307069838, "airplane"],
                                            [0.00015536535647697747, "ship"],
                                            [0.00013383087934926152, "cat"]]},
                                {"filename": "file-0--bird.jpg",
                                 "labels": [[0.881917417049408, "bird"],
                                            [0.08114659041166306, "airplane"],
                                            [0.018458310514688492, "frog"],
                                            [0.005006253719329834, "automobile"]]}]},
     "state": "FINISHED",
     "status": "success"}


<h3 id="ensemble">Ensemble</h3>

<h4 id="ensemble-state">State</h4>

Request

    curl "http://api.ersatz1.com/api/train/state/?ensemble=561&key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"
    
Response

    {"ensemble": {"data_type": "TIMESERIES",
                  "deleted_models_time": 0.0,
                  "deleted_predicts_time": 0,
                  "error": null,
                  "file_name": "uploads/Dp4AaD94_manualx.zip",
                  "id": 561,
                  "state": "finished"},
     "models": [{"error": null,
                 "id": 929,
                 "model_name": "MRNN",
                 "model_params": "{"maxnum_iter":20,"f":2,"h":2,"mu":0.001,"T":20,"cg_max_cg":40,"cg_min_cg":1,"lambda":0.01}",
                 "state": "FINISHED",
                 "training_time": 537.661821365356},
                {"error": null,
                 "id": 930,
                 "model_name": "MRNN",
                 "model_params": "{"maxnum_iter":20,"f":26,"h":76,"mu":0.00325,"T":36,"cg_max_cg":160,"cg_min_cg":8,"lambda":0.7525}",
                 "state": "FINISHED",
                 "training_time": 590.50421833992}]}

<h4 id="add-model">Add model</h4>

Request

    curl http://api.ersatz1.com/api/ensemble/add/  -X POST -d \
        '{"ensemble": 561,
          "model_name": "MRNN",
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

Response contains id of the newly created model

    {"status": "success", "id": 953}


<h4 id="ensemble-start">Start, resume</h4>

If you want to start or resume an ensemble from the last available state, use the resume call function:

    curl "http://api.ersatz1.com/api/ensemble/resume/" -X POST -d \
        '{"ensemble": 561,
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

Response:

    {"status": "success", "state": "in queue"}

<h4 id="ensemble-stop">Stop</h4>

    curl "http://api.ersatz1.com/api/ensemble/cancel/" -X POST -d \
        '{"ensemble": 561,
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

Response:

    {"status": "success", "state": "canceled"}

<h4 id="ensemble-params">Params</h4>
    curl "http://api.ersatz1.com/api/ensemble/settings/" -X POST -d \
        '{"ensemble": 561,
          "config": {"maxnum_iter": {"min": "20", "max": "22"},
                     "h": {"min": "2", "max": "100"},
                     "f": {"min": "2", "max": "100"},
                     "cg_max_cg": {"min": "40", "max": "200"},
                     "cg_min_cg": {"min": "1", "max": "30"},
                     "lambda": {"min": "0.010000", "max": "1.0"},
                     "mu": {"min": "0.001000", "max": "0.01"}
                    },
          "file_id": "21",
          "auto_next_model": true }'


<h3 id="model">Model</h3>

<h4 id="model-stats">Model Stats</h4>

Request

    curl "http://api.ersatz1.com/api/model/stats/?model=929&key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"

Response

    [{"id": 6393, iteration: 0, ...}, ...] # list of stats.

After training the model, you can add `last` key to request id of the last iteration. This will 
return the iteration with the highest id.

    curl "http://api.ersatz1.com/api/model/stats/?model=929&key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4&last=6393"

<h4 id="s-r-r-f-model">Resume</h4>

To resume training for a model from concrete iteration, use the resume call function.  If  you
do not specify the iteration number, the model will resume from the most recent iteration:

    curl "http://api.ersatz1.com/api/model/resume/" -X POST -d \
        '{"model": 955,
          "iteration": 4,
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

Response:

    {"status": "success"}

<h4 id="model-restart">Restart</h4>

    curl "http://api.ersatz1.com/api/model/restart/" -X POST -d \
        '{"model": 955,
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

<h4 id="model-finalize">Finalize</h4>

    curl "http://api.ersatz1.com/api/model/finalize/" -X POST -d \
        '{"model": 955,
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

<h4 id="model-delete">Delete</h4>

    curl "http://api.ersatz1.com/api/model/delete/" -X POST -d \
        '{"model": 955,
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

<h4 id="model-params">Params</h4>
    curl "http://api.ersatz1.com/api/model/settings/" -X POST -d \
        '{"model": 930,
          "model_params": {"maxnum_iter": "22",
                           "h": "76",
                           "f": "26",
                           "cg_max_cg": "160",
                           "cg_min_cg": "8",
                           "lambda": "0.7525",
                           "mu": "0.00325"
                          }
         }'

Response:

       {"status": "success",
         "model_params": {"maxnum_iter": 22,
                          "mu": 0.00325,
                          "lambda": 0.7525,
                          "cg_min_cg": 8,
                          "cg_max_cg": 160
                         }
        }


<h4 id="lrnn-neural-map">MRNN Neural map</h4>
    curl "http://api.ersatz1.com/api/plot/model/?model=929&key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"

Response is list of layers

    [{"value": [[-0.06986033171415329, 0.3851667642593384]], "key": "1_h"}, ...]
