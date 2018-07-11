#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import time
import itertools
import json
import base64
import inspect
import functools
from concurrent.futures import ThreadPoolExecutor

import tornado.web
import tornado.routing

from tornado_profiler import backend as _backend
from tornado_profiler.views import (MeasurementHandler, MeasGroupHandler,
                                    DashboardHandler)


class Profiler(object):

    def __init__(self, backend, max_workers=5, url_prefix="/tornado-profiler"):
        """
        :param backend: a tornado web application instance
        :param max_workers: use thread pool to store measurements
        :param url_prefix: profiler related handlers' url prefix, NO end slash.
        """
        if isinstance(backend, _backend.Backend):
            self.backend = backend
        elif isinstance(backend, dict):
            backend_name = backend.pop("engine")
            self.backend = _backend.get_backend(backend_name, **backend)
        else:
            raise ValueError("Unknown backend argument.")

        self._max_workers = max_workers
        self._url_prefix = url_prefix

    def init_app(self, app):
        self.backend.initialize()

        # Inject attributions into application
        # NOTE: Create thread pool to execute backend operations
        if not self.backend.is_nonblock():
            app.profiler_executor_ = ThreadPoolExecutor(self._max_workers)
        app.profiler_backend_ = self.backend

        # patch app
        self.patch_matcher_match()
        for handler_class in self.get_app_handlers(app):
            if issubclass(handler_class, tornado.web.StaticFileHandler):
                # no need to profile static file handlers
                continue
            self.patch_handler_class(handler_class)

        # register handlers
        self.register_handlers(app)

    @staticmethod
    def _get_router_handlers(router):
        handlers = set()

        for rule in router.rules:
            if isinstance(rule.target, tornado.routing.Router):
                nested_handlers = Profiler._get_router_handlers(rule.target)
                handlers.update(nested_handlers)
            elif inspect.isclass(rule.target) and \
                    issubclass(rule.target, tornado.web.RequestHandler):
                handlers.add(rule.target)
            else:
                raise Exception("Unknown rule target of type %r" % rule.target)
        return handlers

    @staticmethod
    def get_app_handlers(app):
        """Get all handler classes registered in application

        :param app: a instance of tornado.web.Application
        :return: a set of handler classes
        """
        assert isinstance(app, tornado.web.Application)
        handlers = set()

        # default handler
        default_handler_class = app.settings.get("default_handler_class")
        if default_handler_class:
            handlers.add(default_handler_class)

        # fallback error handler
        handlers.add(tornado.web.ErrorHandler)

        # default router handlers
        default_router_handlers = \
            Profiler._get_router_handlers(app.default_router)
        handlers.update(default_router_handlers)

        return handlers

    def patch_matcher_match(self):
        """Patch tornado.routing's HostMatches and PathMatches class.
           FIXME: tornado use regex in `Rule` to match url path or host, we
                  can't know a request is correspond to which Rule's regex
                  unless we iterate all Rules in an application
        """
        # patch PathMatches
        old_path_match = tornado.routing.PathMatches.match

        def path_match(self, request):
            ret = old_path_match(self, request)
            if ret is not None:
                # remove final $ or not?
                pattern = self.regex.pattern
                if pattern.endswith('$'):
                    pattern = pattern[:-1]
                request.profiler_name_ = pattern
                if ret:
                    request.profiler_path_args_ = ret
            return ret
        tornado.routing.PathMatches.match = functools.partialmethod(path_match)

    def patch_handler_class(self, handler_class):
        """Patch all handler classes registered in application.
           Record profile datas at key points.
        :param handler_class: subclass of tornado.web.RequestHandler
        """
        # patch on_finish method
        old_on_finish = handler_class.on_finish

        def on_finish(self):
            old_on_finish(self)

            kwargs = dict()
            # get the corresponding rule(name) for the current request
            kwargs["name"] = getattr(self.request, "profiler_name_", None)
            if kwargs["name"] is None:
                return

            kwargs["method"] = self.request.method
            path_args = getattr(self.request, "profiler_path_args_", None)

            # http request instantiated when headers received
            kwargs["begin_time"] = self.request._start_time
            kwargs["finish_time"] = time.time()
            kwargs["elapse_time"] = kwargs["finish_time"] - kwargs["begin_time"]

            context = {
                # "method": self.request.method,
                "uri": self.request.uri,
                "version": self.request.version,
                "headers": dict(self.request.headers),
                # TODO: maybe decode the body according to Content-Type
                "body": base64.b64encode(self.request.body).decode(),

                "remote_ip": self.request.remote_ip,
                "protocol": self.request.protocol,

                "host": self.request.host,
                "path": self.request.path,
                "arguments": self.request.arguments,
                "cookies": self.request.cookies,

                "full_url": self.request.full_url(),
            }
            if path_args is not None:
                context.update(path_args)

            def json_convert(obj):
                if isinstance(obj, bytes):
                    return obj.decode("utf-8")
            kwargs["context"] = json.dumps(context, default=json_convert)
            # Store measurement into backend
            profiler_executor = getattr(self.application,
                                        "profiler_executor_", None)
            profiler_backend = getattr(self.application, "profiler_backend_")
            if profiler_backend.is_nonblock():
                profiler_backend.insert(**kwargs)
            else:
                profiler_executor.submit(profiler_backend.insert, **kwargs)

        handler_class.on_finish = functools.partialmethod(on_finish)

    def register_handlers(self, app):
        """ Register profiler related handlers
        """
        dirname = os.path.abspath(os.path.dirname(__file__))
        template_path = os.path.join(dirname, "templates")
        static_path = os.path.join(dirname, "static")
        static_url_prefix = r"/static/"

        page_handlers = [
            # Pages
            (r"/?", DashboardHandler, {
                "template_path": template_path,
                "static_path": static_path,
                "static_url_prefix": self._url_prefix + static_url_prefix
            }),
        ]

        api_handlers = [
            # APIs
            (r"/api/measurements/?", MeasurementHandler),
            (r"/api/measurements/groups/?", MeasGroupHandler),
            (r"/api/measurements/([^/]*)", MeasurementHandler),
        ]

        static_handlers = [
            (static_url_prefix + r"(.*)", tornado.web.StaticFileHandler, {
                "path": static_path,
            }),
        ]

        handlers = list()
        for handler in itertools.chain(page_handlers,
                                       api_handlers,
                                       static_handlers):
            from tornado.web import url
            assert len(handler) in [2, 3, 4]

            handlers.append(url(
                self._url_prefix + handler[0],
                *handler[1:]
            ))

        app.add_handlers(r".*", handlers)
