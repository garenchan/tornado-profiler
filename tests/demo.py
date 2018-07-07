#!/usr/bin/env python
# -*- coding: utf-8 -*-
import inspect
import functools

import tornado.web
import tornado.routing
import tornado.ioloop

from tornado_profiler import profiler


class MyHandler(tornado.web.RequestHandler):

    def get(self):
        self.write("hello, world")


def main():
    app = tornado.web.Application(
        handlers=[
            (r"/", MyHandler)
        ],
        enable_profile=True,
    )

    p = profiler.Profiler({"engine": "sqlalchemy"})
    p.init_app(app)
    app.listen(8888, address="0.0.0.0")
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
