<h2 id="api-mrnn-example">API workflow example for MRNN</h2>
-------------------------------------

<h3 id="file-upload">Uploading data</h3>

Uploading file:

    curl http://api.ersatz1.com/api/upload/file/ -F key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4 -F file=@/tmp/aaa.zip

    {"status": "success", "file_id": 53}

Checking file state:

    # curl "http://api.ersatz1.com/api/file/state/?key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4&files%5B%5D=53"               

    {"files": [{"state": "Parsing", "id": 53}], "state": "success"}

    # curl "http://api.ersatz1.com/api/file/state/?key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4&files%5B%5D=53"

    {"files": [{"state": "Ready", "id": 53}], "state": "success"}

File ready, now we can create ensemble with it.

<h3 id="create-ensemle">Creating ensemble</h3>

Creating ensemble with uploaded file, split this file on 3 sets: train, test, valid with percents 70%, 20%, 10%

    # curl http://api.ersatz1.com/api/train/ -X POST -d \
        '{"models": [{"model_name": "MRNN", "num_models": 1}],
          "file_id": 53,
          "data_type": "TIMESERIES",
          "data_split": [70, 20, 10],
          "out_nonlin": "SOFTMAX",
          "start": false,
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'
    {"status": "success", "ensemble_id": 151, "ensemble_url": "/train-ensemble/151/"}

Ensemble created, now we should set params for models.
Checking current params

    # curl "http://api.ersatz1.com/api/train/state/?ensemble=151&key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"

    {"models": [{"model_params": "{}", "model_name": "MRNN", "state": "NEW", "training_time": 0.0, "error": null, "id": 179}], "ensemble": {"data_type": "TIMESERIES", "deleted_models_time": 0.0, "send_email_on_change": false, "file_name": "uploads/1/1384345267200/aaa.zip", "deleted_predicts_time": 0, "state": "new", "error": null, "shared": false, "id": 151}}

Setting new params:

    # curl "http://api.ersatz1.com/api/model/settings/" -X POST -d \
        '{"model": 179,
          "model_params": {"maxnum_iter": "10",
                           "h": "76",
                           "f": "26",
                           "cg_max_cg": "160",
                           "cg_min_cg": "8",
                           "lambda": "0.7525",
                           "mu": "0.00325"
                          },
         "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

    {"status": "success", "model_params": {"maxnum_iter": 10, "f": 26, "h": 76, "mu": 0.00325, "lambda": 0.7525, "cg_min_cg": 8, "cg_max_cg": 160}}

<h3 id="training">Training</h3>

Start training:

    # curl "http://api.ersatz1.com/api/ensemble/resume/" -X POST -d \
        '{"ensemble": 561,
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'
    {"status": "success", "state": "in queue"}

Checking state:

    curl "http://api.ersatz1.com/api/train/state/?ensemble=151&key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"

    {"models": [{"model_params": "{\"maxnum_iter\":10,\"f\":26,\"h\":76,\"mu\":0.00325,\"cg_max_cg\":160,\"cg_min_cg\":8,\"lambda\":0.7525}", "model_name": "MRNN", "state": "QUEUE", "training_time": 0.0, "error": null, "id": 179}], "ensemble": {"data_type": "TIMESERIES", "deleted_models_time": 0.0, "send_email_on_change": false, "file_name": "uploads/1/1384345267200/aaa.zip", "deleted_predicts_time": 0, "state": "in queue", "error": null, "shared": false, "id": 151, "queue_position": 1}}

In state queue, checking again:

    # curl "http://api.ersatz1.com/api/train/state/?ensemble=151&key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"

    {"models": [{"model_params": "{\"maxnum_iter\":10,\"f\":26,\"h\":76,\"mu\":0.00325,\"T\":97,\"lambda\":0.7525,\"cg_min_cg\":8,\"cg_max_cg\":160}", "traceback": null, "model_name": "MRNN", "state": "TRAIN", "training_time": 0.0, "error": null, "id": 179}], "ensemble": {"data_type": "TIMESERIES", "deleted_models_time": 0.0, "send_email_on_change": false, "file_name": "uploads/1/1384345267200/aaa.zip", "traceback": null, "deleted_predicts_time": 0, "state": "training", "error": null, "shared": false, "id": 151}}

Training started, checking stats of model:

    curl "http://api.ersatz1.com/api/model/stats/?model=179&key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"

     [...] returns list of stats.

Waiting for finishing (or we can stop training and finalize model, see api doc)

    curl "http://api.ersatz1.com/api/train/state/?ensemble=151&key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"

    {"models": [{"model_params": "{\"maxnum_iter\":10,\"f\":26,\"h\":76,\"mu\":0.00325,\"T\":97,\"cg_max_cg\":160,\"cg_min_cg\":8,\"lambda\":0.7525}", "model_name": "MRNN", "state": "FINISHED", "training_time": 137.289654970169, "error": null, "id": 179}], "ensemble": {"data_type": "TIMESERIES", "deleted_models_time": 0.0, "send_email_on_change": false, "file_name": "uploads/1/1384345267200/aaa.zip", "deleted_predicts_time": 0, "state": "finished", "error": null, "shared": false, "id": 151}}

State = 'finished', we can predict on this ensemble.

<h3 id="predicting">Predicting</h3>
 We should select best iteration. Selecting from list of stats iteration with better test_accuracy (see previous step how we got stats of model.).
Example with python:

    In [28]: max((x['test_accuracy'], x['iteration']) for x in stats)
    Out[28]: (0.9398625429553261, 9)

Iteration 9 has best test accuracy.
Now we will try to predict with this model.

    curl http://api.ersatz1.com/api/predict/ -X POST -d \
        '{"input_data": "1,2;3,4;5,6;",
          "ensemble": 151,
          "models": [{"id": 179, "iteration": 9}],
          "key": "d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"}'

    {"status": "success", "ensemble_id": 498, "iterations": [[179, 9]]}

Predict ensemble created, now we should wait for results.

Checking predict result:

    curl "http://api.ersatz1.com/api/predict/?ensemble=498&key=d3ece19addabd7b9c6a7d8d8b89e31ae41eda8e4"

    {'id': 498,
        'input_data': '1,2;3,4;5,6;',
        'predicting_time': 108.456316947937,
        'results': {'avg': [[0, 0, 0]],
            'avg_pre_activation': [[[0.9154919385910034, 0.08450805395841599],
            [0.9921425580978394, 0.007857434451580048],
            [0.9959755539894104, 0.004024415742605925]]],
            'avg_pre_activation_results': [[0, 0, 0]],
            'predicts': [{'model': 179, 'results': [[0, 0, 0]]}]},
        'state': 'FINISHED',
        'status': 'success',
        'type': 'input'}
