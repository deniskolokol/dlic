RUN
---

For local run you need start two workers::

    python run_server.py

ADDITIONAL LIBRARIES
----
Install csvstat - see native/readme.txt


TEST
----

Unit tests::
    py.test tests

Functional tests::
    py.test functional_tests

All::
    py.test

Test for python bug (it downloads 18Mb from s3, so I moved it out of regular test)::
    py.test functional_tests/zip_unl_bug.py
