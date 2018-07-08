#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import sys
import inspect
import traceback


class BaseLoader(object):
    """ Use to implement plug-in mode
    """

    def __init__(self, loadable_cls_type):
        mod = sys.modules[self.__class__.__module__]
        self.path = os.path.abspath(mod.__path__[0])
        self.package = mod.__package__
        self.loadable_cls_type = loadable_cls_type

    def _is_correct_class(self, obj):
        return (inspect.isclass(obj) and
                not inspect.isabstract(obj)
                and (not obj.__name__.startswith('_')) and
                issubclass(obj, self.loadable_cls_type))

    def _get_class_from_module(self, module_name):
        classes = []
        module = self.import_module(module_name)
        for obj_name in dir(module):
            if obj_name.startswith('_'):
                continue
            obj = getattr(module, obj_name)
            if self._is_correct_class(obj):
                classes.append(obj)
        return classes

    @classmethod
    def import_class(cls, import_str):
        mod_str, _sep, class_str = import_str.rpartition('.')
        __import__(mod_str)
        try:
            return getattr(sys.modules[mod_str], class_str)
        except AttributeError:
            raise ImportError("Class %s cannot be found (%s)" %
                              (class_str,
                               traceback.format_exception(*sys.exc_info())))

    @classmethod
    def import_module(cls, import_str):
        __import__(import_str)
        return sys.modules[import_str]

    def get_all_classes(self):
        classes = []
        for dirpath, dirnames, filenames in os.walk(self.path):
            relpath = os.path.relpath(dirpath, self.path)
            if relpath == '.':
                relpkg = ''
            else:
                relpkg = "%s" % '.'.join(relpath.split(os.sep))
            for fname in filenames:
                root, ext = os.path.splitext(fname)
                if ext != ".py" or root == "__init__":
                    continue
                module_name = "%s%s.%s" % (self.package, relpkg, root)
                mod_classes = self._get_class_from_module(module_name)
                classes.extend(mod_classes)
        return classes

    def get_matching_classes(self, loadable_class_names):
        classes = []
        for cls_name in loadable_class_names:
            obj = self.import_class(cls_name)
            if self._is_correct_class(obj):
                classes.append(obj)
            elif inspect.isfunction(obj):
                    classes.extend(obj())
        return classes


def str2bool(str_val):
    """ Convert a boolean-like string into bool

    :param str_val: a boolean-like string
    :return: bool
    """
    assert isinstance(str_val, str)

    str_val = str_val.lower()
    if str_val in ["true", "yes", "1"]:
        return True
    elif str_val in ["false", "no", "0"]:
        return False
    else:
        raise ValueError("Unknown boolean-like string %r" % str_val)
