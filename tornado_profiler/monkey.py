#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import socket
import traceback
import functools
import threading


class Receiver(object):
    """a abstract class for receive monkey message"""

    def notify_blocking_point(self, message):
        raise NotImplementedError()


class Monkey(object):
    """Some monkey patches of built-in or standard library
    """

    def __init__(self, receiver):
        assert isinstance(receiver, Receiver)
        self.receiver = receiver

    def patch_time_sleep(self):
        """Patch built-in module time's `sleep` function.

        Its call will cause thread to be blocked.
        """
        _sleep = time.sleep

        @functools.wraps(_sleep)
        def sleep(secs):
            # TODO: ioloop may be not running in main thread.
            if threading.current_thread() is threading.main_thread():
                self.receiver.notify_blocking_point(
                    traceback.format_stack()[:-1])
            _sleep(secs)

        time.sleep = sleep

    def _patch_socket_func(self, func_name):
        """Patch specified `socket.socket`'s function.

        :param func_name: `socket.socket`'s function name
        """
        func = getattr(socket.socket, func_name, None)
        if not func:
            return

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if threading.current_thread() is threading.main_thread():
                # judge whether this socket is in blocking mode.
                get_blocking = getattr(args[0], "getblocking", None)
                if get_blocking:
                    blocking = get_blocking()
                else:
                    blocking = (args[0].gettimeout() == None)
                if blocking:
                    self.receiver.notify_blocking_point(
                        traceback.format_stack()[:-1])

            return func(*args, **kwargs)

        setattr(socket.socket, func_name, wrapper)

    def patch_socket_funcs(self):
        func_names = {
            "accept", "close", "connect", "connect_ex",
            "recv", "recv_into", "recvfrom", "recvfrom_into",
            "send", "sendall", "sendto", "shutdown",
        }

        for func_name in func_names:
            self._patch_socket_func(func_name)

    def patch_all(self):
        for attr in dir(self):
            if not (attr.startswith("patch") and attr != "patch_all"):
                continue

            patch_func = getattr(self, attr)
            if callable(patch_func):
                patch_func()
