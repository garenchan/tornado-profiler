#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import inspect
import functools

import tornado.web
import tornado.routing
import tornado.ioloop

from tornado_profiler import profiler


class MyHandler(tornado.web.RequestHandler):

    def get(self):
        self.write("hello, world")


class MyHandler1(tornado.web.RequestHandler):
    def get(self):
        self.write("hello, world1")


def main():
    dirname = os.path.abspath(os.path.dirname(__file__))
    profiler_path = os.path.join(dirname, "..", "tornado_profiler", "static")
    app = tornado.web.Application(
        handlers=[
            (r"/1", MyHandler),
            (r"/2", MyHandler1),
            (r"/3", MyHandler1),
            (r"/4", MyHandler),
            (r"/5", MyHandler),
            (r"/6", MyHandler),
            (r"/7", MyHandler),
            (r"/8", MyHandler),
            (r"/9", MyHandler),
            (r"/10", MyHandler),
            (r"/11", MyHandler),
            (r"/12", MyHandler),
        ],
        enable_profile=True,
        static_path=profiler_path,
        debug=True,
    )

    p = profiler.Profiler({"engine": "sqlalchemy",
                           "db_url": "sqlite:///test.db",
                           "echo": True})
    p.init_app(app)
    app.listen(8888, address="0.0.0.0")
    tornado.ioloop.IOLoop.current().start()
    print(p.get_app_handlers(app))
    backend = p.backend
    print(type(backend.filter(id=1).begin_time))


if __name__ == '__main__':
    main()
