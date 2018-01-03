DEVELOPMENT
===========


Git
---

Basic workflow: http://blogs.atlassian.com/2014/01/simple-git-workflow-simple/

branches:
  - master (where we developing new version)
  - production (code for production server)
  - staging (code for staging server)

For mrnn and dmworker repo we use same branching,
so in production branch we have code which works with production
branch in another repo, and so on

After feature complited in a separated branch you should do pull request
to the master branch


Python
------

Use PEP8 for all new code.
Use pylint::
    make pylint

Test::
    make test  # will run all project's tests

Look into Makefile for ideas about how to run more specific commands by hands


JavaScript
----------

1) Install node packages with ``npm install``.

2) Run ``./manage runserver --settings=ersatz.settings.local``,
it will start grunt-watch, so when you edit .jsx files
it compile it to js files and build automatically.

**DO NOT EDIT BY HAND FILES IN web/static/build**

3) Checking for errors in js files::

    make jslint

4) If you've changed any file in ``web/src/`` then you must build js,
for this you can start runserver or run::

    make jsbuild
