from setuptools import setup, find_packages
import sys, os

setup(name='redflare',
    version='0.1',
    description='',
    classifiers=[], 
    keywords='',
    author='BJ Dierkes',
    author_email='wdierkes@rackspace.com',
    url='',
    license='GNU GPL v3',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "ConfigObj",
        "Cement >=0.4.3, <0.5",
        "CementPlugins >=0.4.3, <0.5",
        ],
    setup_requires=[
        "PasteScript >= 1.7"
        ],
    test_suite='nose.collector',
    entry_points="""
    [console_scripts]
    redflare = redflare.appmain:main
    """,
    namespace_packages=['redflare', 'redflare.plugins'],
    )
