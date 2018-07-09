#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json

import tornado.gen
import tornado.web

from tornado_profiler.utils import str2bool


class BaseHandler(tornado.web.RequestHandler):

    def initialize(self, template_path=None, static_path=None,
                   static_url_prefix=None):
        self._executor = getattr(self.application,
                                    "profiler_executor_", None)  # noqa
        self._backend = getattr(self.application,
                                        "profiler_backend_")  # noqa
        self._template_path = template_path
        self._static_path = static_path
        self._static_url_prefix = static_url_prefix

    def get_json_argument(self, name, *args):
        """Get json argument"""
        # TODO: We need to check whether the request's content-type is
        # application/json and get the charset.
        _json = getattr(self, "_json", None)
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

    def get_template_path(self):
        """Override to customize template path for our handlers"""
        return self._template_path

    def static_url(self, path, include_host=None, **kwargs):
        """Override to use static_url in template"""
        get_url = tornado.web.StaticFileHandler.make_static_url

        if include_host is None:
            include_host = getattr(self, "include_host", False)

        if include_host:
            base = self.request.protocol + "://" + self.request.host
        else:
            base = ""

        return base + get_url({
            "static_url_prefix": self._static_url_prefix,
            "static_path": self._static_path,
        }, path, **kwargs)

    def write_error(self, status_code, **kwargs):
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


##############################
#       API Handlers
##############################
class MeasurementHandler(APIHandler):

    @tornado.gen.coroutine
    def get_measurement_by_id(self, _id):
        """ Get a measurement by id
        """
        if self._backend.is_nonblock():
            measurement = self._backend.filter(id=_id)
        else:
            measurement = yield \
                self._executor.submit(self._backend.filter, id=_id)

        response = dict(measurement=measurement)
        return response

    @tornado.gen.coroutine
    def get_measurements(self):
        """ Get measurement list
        """
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
            response = self.make_error_response(400, "Param %r error" % arg_name)
            self.set_status(400)
            return self.write(response)

        if self._backend.is_nonblock():
            measurements = self._backend.filter(**kwargs)
        else:
            measurements = yield \
                self._executor.submit(self._backend.filter, **kwargs)

        response = dict(measurements=measurements)
        return response

    @tornado.gen.coroutine
    def get(self, *args):
        if args:
            _id = args[0]
            response = yield self.get_measurement_by_id(_id)
        else:
            response = yield self.get_measurements()

        self.write(response)


class MeasGroupHandler(APIHandler):
    """ Measurements can be grouped by their names.
    """

    @tornado.gen.coroutine
    def get_datatable(self):
        """Datatable ajax source"""
        COL_MAP = {
            2: "count",
            3: "avg",
            4: "max",
            5: "min",
        }
        try:
            echo = self.get_argument("sEcho", "1")
            start = int(self.get_argument("iDisplayStart", 0))
            length = int(self.get_argument("iDisplayLength", 10))
            search = self.get_argument("sSearch", None)
            sortcol = int(self.get_argument("iSortCol_0", 2))
            sortcol = COL_MAP[sortcol]
            sortdir = self.get_argument("sSortDir_0", "asc").strip()
        except (tornado.web.MissingArgumentError, ValueError) as ex:
            self.set_status(400)
            return self.make_error_response(400, "Param error")

        kwargs = dict(
            search=search,
            sort=','.join([sortcol, sortdir]),
            offset=start,
            limit=length,
            return_total=True,
        )
        try:
            if self._backend.is_nonblock():
                total, measgroups = self._backend.group(**kwargs)
            else:
                total, measgroups = yield \
                    self._executor.submit(self._backend.group, **kwargs)
        except Exception as ex:
            self.set_status(500)
            return self.make_error_response(500, "Profiler internal error", 1)
        else:
            return dict(
                sEcho=echo,
                iTotalRecords=total,
                iTotalDisplayRecords=total,
                data=measgroups,
            )

    @tornado.gen.coroutine
    def get_measgroups(self):
        query_args = [
            ("begin_time", float),
            ("finish_time", float),
            ("method", str),
            ("name", str),
            ("sort", str),
            ("offset", int),
            ("limit", int),
        ]
        try:
            kwargs = dict()
            for arg_name, arg_type in query_args:
                value = self.get_argument(arg_name, None)
                if value is not None:
                    value = arg_type(value)
                    kwargs[arg_name] = value
        except ValueError:
            self.set_status(400)
            return self.make_error_response(400, "Param %r error" % arg_name)

        try:
            if self._backend.is_nonblock():
                measgroups = self._backend.group(**kwargs)
            else:
                measgroups = yield \
                    self._executor.submit(self._backend.group, **kwargs)
        except Exception:
            self.set_status(500)
            return self.make_error_response(500, "Profiler internal error", 1)
        else:
            return dict(measgroups=measgroups)

    @tornado.gen.coroutine
    def get(self):
        echo = self.get_argument("sEcho", None)
        if echo is not None:
            response = yield self.get_datatable()
        else:
            response = yield self.get_measgroups()

        self.write(response)


##############################
#      Page Handlers
##############################
class DashboardHandler(BaseHandler):

    def get(self):
        """Dashboard/Index page"""
        self.render("index.html")
