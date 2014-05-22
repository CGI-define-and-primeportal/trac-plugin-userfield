#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2013 CGI IT UK Ltd

from setuptools import setup

setup(
    name='UserFieldPlugin',
    version=0.1,
    description='Adds a user custom field automatically populated by groups',
    author="Ian Clark",
    author_email="ian.clark@cgi.com",
    license='BSD',
    url='http://define.primeportal.com/',
    packages=['userfield'],
    package_data={
        'userfield': [
            'htdocs/css/*.css',
            'htdocs/js/*.js',
            'templates/*',
        ]
    },
    install_requires = ['LogicaOrderTracker',],
    entry_points={
        'trac.plugins': [
            'userfield.filter = userfield.filter',
            'userfield.api = userfield.api',
        ]
    },
)
