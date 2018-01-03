# Functional Tests

## Install dependencies

1. Install selenium
2. Install node dependencies

```bash
$ cd Ersatz-API/tests
$ npm install
```

## Setup

1. Make sure selenium is running
2. Make sure the following environment variables are present, its used to authenticate against the target test server:

    - `TEST_SERVER_URL`
    - `TEST_SERVER_EMAIL`
    - `TEST_SERVER_PASSWORD`

## Running

```bash
$ mocha run.js
```
