#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import time
import json
import base64
import inspect
import functools
from concurrent.futures import ThreadPoolExecutor

import tornado.web
import tornado.routing


class Profiler(object):

    def __init__(self, backend, max_workers=5):
        """
        :param backend: a tornado web application instance
        :param max_workers: use thread pool to store measurements
        """
        self.backend = backend
        self._max_workers = max_workers

    def init_app(self, app):
        # self.app = app
        app.profiler_executor = ThreadPoolExecutor(self._max_workers)
        app.profiler_backend = self.backend

        self.patch_matcher_match()
        for handler_class in self.get_app_handlers(app):
            self.patch_handler_class(handler_class)

    @staticmethod
    def _get_app_router_handlers(app_router):
        handlers = set()

        for rule in app_router.rules:
            if isinstance(rule.target, tornado.web._ApplicationRouter):
                nested_handlers = Profiler._get_app_router_handlers(rule.target)
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
        # static handler
        static_handler_class = app.settings.get("static_handler_class",
                                                tornado.web.StaticFileHandler)
        handlers.add(static_handler_class)
        # fallback error handler
        handlers.add(tornado.web.ErrorHandler)
        # default router handlers
        default_router_handlers = \
            Profiler._get_app_router_handlers(app.default_router)
        handlers.update(default_router_handlers)

        return handlers

    def patch_matcher_match(self):
        """Patch tornado.routing's HostMatches and PathMatches class.
           FIXME: tornado use regex in `Rule` to match url path or host, we
                  can't know a request is correspond to which Rule's regex
                  unless we iterate all Rules in an application
        """
        # patch HostMatches
        old_host_match = tornado.routing.HostMatches.match
        def host_match(self, request):
            ret = old_host_match(self, request)
            if ret is not None:
                # remove final $ or not?
                request.profiler_name = pattern = self.regex.pattern
                request.profiler_type = "host_match"
            return ret
        tornado.routing.HostMatches.match = functools.partialmethod(host_match)

        # patch PathMatches
        old_path_match = tornado.routing.PathMatches.match
        def path_match(self, request):
            ret = old_path_match(self, request)
            if ret is not None:
                # remove final $ or not?
                request.profiler_name = pattern = self.regex.pattern
                request.profiler_type = "path_match"
                if ret:
                    request.profiler_path_args = ret
            return ret
        tornado.routing.PathMatches.match = functools.partialmethod(path_match)

    def patch_handler_class(self, handler_class):
        """Patch all handler classes registered in application.
           Record profile datas at key points.
        :param handler_class: subclass of tornado.web.RequestHandler
        """
        # patch __init__ method
        # old_init = handler_class.__init__
        # def __init__(self, *args, **kwargs):
        #     old_init(self, *args, **kwargs)
        #     #self.__profiler_handler_init_at = time.time()
        # handler_class.__init__ = functools.partialmethod(__init__)

        # patch on_finish method
        old_on_finish = handler_class.on_finish
        def on_finish(self):
            old_on_finish(self)

            kwargs = {}
            # get the corresponding rule(name) for the current request
            kwargs["name"] = getattr(self.request, "profiler_name", None)
            if kwargs["name"] is None:
                return

            kwargs["method"] = self.request.method
            kwargs["type"] = getattr(self.request, "profiler_type", None)
            path_args = getattr(self.request, "profiler_path_args", None)

            # http request instantiated when headers received
            kwargs["begin_time"] = int(self.request._start_time)
            kwargs["finish_time"] = int(time.time())
            kwargs["elapse_time"] = round(
                kwargs["finish_time"] - kwargs["begin_time"], 6)

            context = {
                # "method": self.request.method,
                "uri": self.request.uri,
                "version": self.request.version,
                "headers": str(self.request.headers),
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
            kwargs["context"] = json.dumps(context)
            # Store measurement into backend
            future = self.application.profiler_executor.submit(
                self.application.profiler_backend.insert, **kwargs)
            future.result()
        handler_class.on_finish = functools.partialmethod(on_finish)
