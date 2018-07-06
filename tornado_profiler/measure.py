#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time


class Measurement(object):
    """represents an endpoint measurement
    """

    PRECISION = 6

    def __init__(self, name, method, context=None):
        """

        :param name: endpoint name, usually is path
        :param method: http method
        :param context: http request context
        """
        self.name = name
        self.method = method
        self.context = context

        self.start_time = None
        self.end_time = None
        self.elapsed = None
