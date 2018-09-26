# demo.py
import time
import http.client

import tornado.ioloop
import tornado.web
import io

from tornado_profiler import Profiler


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        conn = http.client.HTTPConnection("www.baidu.com")
        conn.request("GET", "/")
        self.write("main")


class HelloHandler(tornado.web.RequestHandler):
    def get(self):
        time.sleep(1)
        self.write("Hello, world")


def make_app():
    app = tornado.web.Application([
        (r"/", MainHandler),
    ])

    # use to store measurement datas
    backend = {
        "engine": "sqlalchemy",
    }
    # instantiate profiler
    profiler = Profiler(backend)
    # do something to your app
    profiler.init_app(app)

    # you can add some rules that won't be profiled here
    app.add_handlers(r".*", [
        (r"/hello", HelloHandler),
    ])

    return app


if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()