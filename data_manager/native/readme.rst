Building csvstat
================

1. Install packages

    sudo apt-get install g++ libboost-all-dev zlibc libhdf5-serial-dev h5utils

2. Build csvstat

    cd projects/csvstat
    make

3. Install csvstat

    sudo make install 


Using csvstat
=============

For parse:

    csvstat parse <input csv file>

Input can be plain text or gzip or bzip compressed binary. (tar.gz and zip is not supported yet!)
It analize the input and print the result in JSON format to stdout.
User messages (errors and progress info) goes to standard error.

Returns

 0  : success
 1  : user error
 2-3: internal logic error
 4  : fatal error

For load to hdf5 file:

    csvstat load <csv file> <hdf5 file> [load config file]

Transforms csv data to hdf5 format for training and prediction.

Load config file is optional. It describes what transformation should be applied
to the dataset such as changing columnt types, normalization, sampling, etc.

Syntax of the config file is JSON. For possible configuration options see the following example:

TODO!
