<h2 id="conv-tut">Convolutional Neural Networks Tutorial</h2>
-------------------------------------------------------------

Look in [data managment](/help/data/) for data format.
After uploading file, select *Images* tab on [create new ensemble page](/train-ensemble/new/).

![convolution new](/static/img/help/conv_new.png)

Select File for training and how to split batches between train and test datasets.
Add model (CONV) and create ensemble.

![convolution params](/static/img/help/conv_params.png)

**Test frequency** - every this many iterations compute test error.  
**Saving frequency** - every this many iteration save model data to server.
So, with default values: 10, 30; after 50 iters you will see stats for this 50 iters
but if you stop and resume model it will not resume from iteration 50, it will 
resume from iteration 30.


<h3 id="predict">Predict</h3>

You can predict on finished ensemble (Run ensemble link near ensemble status or 
from dashboard 'Make prediction' button). Just drop images and press classify button.

![convolution predict](/static/img/help/conv_predict.png)
