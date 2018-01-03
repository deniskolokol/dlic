<h2 id="auto-tut">Autoencoder Tutorial</h2>
-------------------------------------------

See [data managment](/help/data/) for more information on data formatting.
After uploading a file, select the *General* tab on [create new ensemble page](/train-ensemble/new/).

![autoencoder new](/static/img/help/autoencoder_new.png)

Select a file and add an autoencoder model. After selecting an autoencoder, you can create an
ensemble.  Start the ensemble using the *Create and start training* button.  You can also create and
tune the autoencoder params with the *Create* button.

If you have not started training, you can change the autoencoder params on the *Model
params* tab.  If you have started the training and want to change the params, you can stop the training, 
change the params and resume or restart the training.

![autoencoder params](/static/img/help/autoencoder_params.png)

**IMPORTANT:** The iterations count begins with zero (not 1).  If you train a model with 100 iterations, 
the last iteration will be 99, for example (0-99).
