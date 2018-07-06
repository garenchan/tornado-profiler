#!/usr/bin/env python
# -*- coding: utf-8 -*-
import inspect
import functools

import tornado.web
import tornado.routing
import tornado.ioloop

from tornado_profiler import profiler
from tornado_profiler.backend import Sqlalchemy


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
    sqlalchemy = Sqlalchemy()
    sqlalchemy.init_database()
    p = profiler.Profiler(sqlalchemy)
    p.init_app(app)
    #app.listen(8888)
    #tornado.ioloop.IOLoop.current().start()
    #print(help(MyHandler.on_finish))
    print(sqlalchemy.get_all())


if __name__ == '__main__':
    main()

