<h2 id="mrnn-tutorial">MRNN Tutorial</h2>
-----------------------------------------

For more information on data format please see [data managment](/help/data/).
After uploading a file, select the *Timeseries* tab on the [create new ensemble page](/train-ensemble/new/).

![mrnn new](/static/img/help/mrnn_new.png)

If you do not have separate train/test/valid datasets, you can select the individual file types,
and the missing dataset will be created by dividing your input to create the missing file for training. 
To divide a training file you should specify percentages. On the screenshot, we have selected values 
for training and test datasets, but have not entered a validation dataset.  The training dataset will be split
based on the percentages entered (80%, 0%, 20%).  Therefore, 80% of the training file will be split for the
training dataset and 20% will be split to create a validation dataset.

The next step, you can change the output nonlinearity: SOFTMAX or SIGMOID.

Finally, you add the models.

After completing these steps you can immediately run training with "Create and start training".
You can only create an ensemble and adjust the ensemle/model params for your new ensemble.


<h3 id="mrnn-params">MRNN params</h3>

If you do not start training immediately, the ensemble and models are saved in a 'new' state.
In this state you can change many of the training params.  If you have already started training the model,
you can stop the model, change the params and resume training it.
 
One of advantage of Ersatz is the autotune mrnn params.  These params produce better results. As on this 
screenshot, you can see that the model has these settings:

  - **Start training next model automatically**
  - **Change file for training** `WARNING: All models in ensemble must be trained
with data which has equal number of inputs and outputs.`
  - **Limits for automatic optimization** - low and high limits for automatic
training

For each model on the 'Model params' tab you can set params manually.  Before you start training the model, the
params are empty.  After starting the training, you will see the params the autotuner has selected for
the model.
![mrnn params](/static/img/help/mrnn_created.png)


<h3 id="workflow">Simple training workflow</h3>

  - Create the ensemble (changing autotune params is an advanced option)
  - Start training
  - Look at stats: tabs 'All iteration accuracy', 'Other training stats', 'Output'
  - If you identify some issues with the model training
    - Stop it
    - Change params
    - Resume from any iteration with a new param or restart from the beginning
  - If the model has reached the maximum number of iterations, but you would like to perform additional training, then
    - Increase the # of training iterations and resume from the last iteration.
  - If the model has not reached the max iteration yet, and you do not want to conduct further training, then, stop it and finalize.


<h3 id="predicting">Predicting</h3>

When all models in the ensemble are in the 'finished' state, you can make predictions using this ensemble.  
Near the ensemble state, you will see *Run ensemble* link, or 'Make prediction' button on the 
dashboard in the model row.

![mrnn predict](/static/img/help/mrnn_predict.png)

The main part of predicting is on *Run ensemble on data*. You can select which models
and iteration should be used for prediction, place raw data and 'Run ensemble'. 
In 'Previous predictions' you will see a new predictions with 'Processing...' status. When the prediction is 
done you will see the button 'Results' that will show results of the prediction.

**Average result** is average of all selected models. And **Average pre-activation result**
is average of pre sigmoid or softmax results.
