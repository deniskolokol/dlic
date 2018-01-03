<h2 id="data-upload">Data Upload</h2>
-------------------------------------

After your initial login, you can upload data files for neural network
training on the [dashboard](http://api.ersatz1.com/dashboard/).  
Currently Ersatz supports [*timeseries*](#timeseries), [*images*](#images) and [*general csv*](#general-csv) data.


<h3 id="timeseries">Timeseries</h3>

A valid timeseries dataset is a zipped text file with **.ts** extension (not csv) and has the following format:

    1,2,3|0,1;4,5,6|1,0;
    1,3,2|1,0;1,2,4|0,1;1,2,5|1,0;
    1,3,4|0,1;1,4,5|1,0;
    
    More specifically:
    
    ( 1,2,3 ) <= that's a single timestep
    ( 1,2,3|0,1 ) <= that's a single timestep with an output target of [0,1] corresponding to class #2/2
    ( 1,2,3|0,1; 4,5,6|1,0; ) <= that's two timesteps with two target outputs representing a single timeseries sample
    * You can have as many timesteps as you want, but we recommend sticking to a range of 50-250 steps.  
    * Different samples can have a different number of timesteps (your windows do not need to be equal length)
    
    ** don't include a text header
    ** each individual timeseries gets its own line (one sample per line)
    
Every row represents a data sample. 
Each sample contains timesteps separated by a semicolon. 
Each timestep consists of two parts.  The first part is the input vector value; the second part is an output vector value. 
The values are separated by a pipe character '|'.
Input and output vectors contain values (input and output).  One row represents one sample.  
An archive can contain only one .ts file.

*** So in short: put your timeseries data into input/output pairs, add it to a .ts text file, zip it, and upload to Ersatz***

<h3 id="images">Images</h3>
Currently Ersatz supports the following format for image datasets: a zip with folders in the root and images inside.

The folders represent classes.  The images in the folders are used to train the cases of this class. Image dimensions do not matter (we rescale automatically)

The following image formats are supported: **.jpeg**, **.jpg**, **.png**, **.bmp**

Please use only alpha characters and numbers in folder and file names.

Please see an example of a file in an acceptable format for convnet:


    some_dataset.zip
    
    some_class/this_class_case.jpg
    some_class/this_another_case.jpg
    some_class/and_so_on.jpg
    another_class/1.jpg
    another_class/2.jpg
    another_class/3.jpg
    ...

<h3 id="general-csv">General CSV</h3>

Currently we support a *zipped CSV* format.  This format is an archive with a single text file with **.csv** extension. A
[CSV formatted](http://en.wikipedia.org/wiki/Comma-separated_values) dataset contains a single table with a fixed number of columns separated by a delimeter.  We currently support comma and space characters as delimeters.
Each row represents a record of this table.

An example of valid CSV text (do not include a header):
    
    0,0,0,1,0,0,0,0,1,10
    0,.6,0,1,0,0,0,0,.8,6
    0,0,0,0,0,1,0,0,0,4
    0,0,0,.5,0,.8,0,0,0,6
    
    * The final column determines the target output class. 
      It should be provided as a single integer 
      (in MNIST, with 10 classes, that would be 0-9)
      
    * Numbers may be binary or real valued


<h3 id="autoencoder">Autoencoder</h3>
Currently an autoencoder model supports *General CSV* format.
