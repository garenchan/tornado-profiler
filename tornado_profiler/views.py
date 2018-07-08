#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json

import tornado.gen
import tornado.web

from tornado_profiler.utils import str2bool


class BaseHandler(tornado.web.RequestHandler):

    def initialize(self):
        self._executor = getattr(self.application,
                                    "profiler_executor_", None) # noqa
        self._backend = getattr(self.application,
                                        "profiler_backend_") # noqa

    def get_json_argument(self, name, *args):
        """Get json argument"""
        # TODO: We need to check whether the request's content-type is
        # application/json and get the charset.
        _json = getattr(self, '_json', None)
        if _json is None:
            body = self.request.body
            if isinstance(body, bytes):
                body = body.decode()
            _json = self._json = json.loads(body)
        try:
            value = _json[name]
        except KeyError:
            if len(args) >= 1:
                value = args[0]
            else:
                raise
        return value

    def write_error( self, status_code, **kwargs ):
        if status_code == 404:
            self.render('errors/404.html')


class APIHandler(BaseHandler):
    """Base handler class of RESTful API"""

    @staticmethod
    def make_error_response(status, message, code=None):
        return dict(error=dict(
            status=status,
            message=message,
            code=code,
        ))


class MeasurementHandler(APIHandler):

    @tornado.gen.coroutine
    def get(self):
        query_args = [
            ("begin_time", float),
            ("finish_time", float),
            ("method", str),
            ("name", str),
            ("sort", str),
            ("offset", int),
            ("limit", int),
            ("with_context", str2bool),
        ]
        try:
            kwargs = dict()
            for arg_name, arg_type in query_args:
                value = self.get_argument(arg_name, None)
                if value is not None:
                    value = arg_type(value)
                    kwargs[arg_name] = value
        except ValueError:
            response = self.make_error_response(400, "Params error", None)
            self.set_status(400)
            return self.write(response)

        if self._backend.is_nonblock():
            measurements = self._backend.filter(**kwargs)
        elif self._executor:
            measurements = yield \
                self._executor.submit(self._backend.filter, **kwargs)
        else:
            response = self.make_error_response(500,
                                                "Internal server error", None)
            self.set_status(500)
            self.write(response)

        response = {
            "measurements": measurements,
        }
        self.write(response)
