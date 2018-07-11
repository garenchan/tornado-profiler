#!/usr/bin/env python
# -*- coding: utf-8 -*-
import abc

from tornado_profiler.utils import BaseLoader


class Backend(metaclass=abc.ABCMeta):
    """ Tornado Profiler's Base Backend Class
        : backend uses to store datas
    """

    def __init__(self, **kwargs):
        """ backend's constructor

        :param kwargs: backend related arguments
        """

    def initialize(self):
        """ Use for lazy initialization
            :subclass need to override this method
        """

    @classmethod
    @abc.abstractmethod
    def get_name(cls):
        """Returns backend specific name"""
        return cls.__name__

    @abc.abstractmethod
    def insert(self, **kwargs):
        """This method used to insert new data"""

    @abc.abstractmethod
    def filter(self, **kwargs):
        """This method used to filter datas"""

    @abc.abstractmethod
    def group(self, **kwargs):
        """This method used to group datas"""

    def is_nonblock(self):
        """Used to indicate whether the backend's CRUD will be blocked!"""
        return False


class BackendFinder(BaseLoader):
    """ Backend Finder class
        : use to find all backend classes
    """

    def __init__(self):
        super(BackendFinder, self).__init__(Backend)


def get_all_backends():
    """ Get all backends
    :return: a dict mapping backend name to backend class
    """
    backends = {}
    for backend_class in BackendFinder().get_all_classes():
        backend_name = backend_class.get_name()
        assert backend_name not in backends, "duplicated backend names"
        backends[backend_name] = backend_class

    return backends


def get_backend(backend_name, **kwargs):
    """ Get a instantiated backend object.

    :param backend_name:
    :param kwargs:
    :return: a backend object
    """
    all_backends = get_all_backends()
    try:
        backend_class = all_backends[backend_name]
    except KeyError:
        raise Exception("Backend not found for: %s, available backends are %s"
                        % (backend_name, list(all_backends.keys())))
    else:
        return backend_class(**kwargs)
