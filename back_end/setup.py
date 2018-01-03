from setuptools import setup, find_packages

setup(
    name='ErsatzDeepnet',
    version='0.1-dev',
    scripts=['bin/errun', 'bin/ertrain', 'bin/erpredict'],
    packages=find_packages(),
)
