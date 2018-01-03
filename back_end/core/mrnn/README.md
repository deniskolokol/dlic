![MRNN](http://upload.wikimedia.org/wikipedia/commons/d/dd/RecurrentLayerNeuralNetwork.png)




This is an implementation of the multiplicative RNN as applied to character level 
language modelling with a multiGPU implementation. 


How to run it:

 cd to the mrnns directory
open python

>>> import opt.r.rnn.full_rnn_run as r;   r.t.optimize()
For the huge 8-GPU run with a 1500-unit MRNN on wikipedia.
(the log is in runs/opt/r/rnn/full_rnn_run/results
and  runs/opt/r/rnn/full_rnn_run/detailed_results)
Note: the log doesn't exist. You need to run an experiment, and then
the log will be formed. 

>>> import opt.r.rnn.full_rnn_run_test as r;   r.t.optimize()
For a tiny 2-GPU diagnostic run that's much faster. 
You should star with the full_rnn_run_test first, and make sure that
it works and that it prints things to the log. 
(the log is in runs/opt/r/rnn/full_rnn_run_test/results
and  runs/opt/r/rnn/full_rnn_run_test/detailed_results)
A sample log is provided with the code, and if you run an experiment
once more, the next experiment will print thing to the end of the log
file. Hence, it's a good practice to create a new run file for each
experiment by saving a copy of the run file, and making the desired 
modifications. This way, we will also have a degree of
reproducibility, since we'll store all the parameters of every
experiment we've ever made. 

The modules opt.r.rnn.full_rnn_run_test
and opt.r.rnn.full_rnn_run are the main file
which defines the run. 

Each of these files (which we call a run file) determines the size of
the MRNN, the size of the minibatch, the length of the text sequences
we're doing our training on, the weight decay, and quite a few other
things.

In more detail, the run file
 - creates a data object, whose parameters determine the batch size
   and the sequence length

 - creates an MRNN object of a certain size
   - it also initializes the MRNN object

 - it also chooses things like weight decay and the initial damping

 - creates an HF optimizer object. The HF object needs the data object,
   functions for computing gradients and curvature, the initial parameters,
   parameters that specify the number of CG steps,
   the number of minibatches for computing the gradient, and the number
   of minibatches for computing the curvature, as well as the backtracking.
   And many other things. 


The MRNN object is defined in 

opt.m.rnn.mrnn

The MRNN needs to be able to compute the loss, the gradinet, and the
gauss-newton matrix vector products. See the source of this module for
a detailed explanation of the things it does.


In all likelihood, you'll want to run things on different datasets. 
The data object is created by the function
wik in the module  opt.d.lang.wik.b 

Please have a look at how it works. You will see that this module
loads a text file and give it to the "ContiguousText" object. 
The ContiguousText is a pretty capable class. I recommend reading its source. 


The most interesting class is HF from opt.hfs.c3_par_c. It implements
the multi-GPU HF optimizer. While it sounds complicated, in reality
it's pretty easy.  HF creates multiple instances of the current
process, with a manager process and a few worker processes. The
manager process runs CG and does all the bookkeeping; it tells the
worker processes the minibatches on which it wants the gradient /
curvature. 

opt.hfs.c3_par_c is fairly well documented, and each of its parameters
are moderately well-explained.


Finally, you'll want to sample from the MRNN after
training it for a while. Or you'll want to use it as a part of another
system (though be warned: big 1500-unit MRNNs can be quite slow, so
you should either use a GPU or use smaller MRNNs). 

So, to sample from the MRNN, please see the demo.mrnn file. 

We finish with a GPU note. If your computer has many GPUs, and the
cuda paths are all set up correctly, then this code should work just
fine with no problems. To be sure that the GPUs work, you need to
ascertain that cudamat is functional. 

To check that the GPU works, cd to mrnns, run python,
and type
>>> import gnumpy as g
>>> g.rand(10)

If there is a problem with the gpu, gnumpy will print a message saying
that it cannot import a GPU, so it must rely on emulation mode. 
