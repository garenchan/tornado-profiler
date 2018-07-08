#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Test(object):

    def __init__(self):
        class B:
            pass
        globals()['B'] = B

    def test(self):
        b = B()
        print(b)


if __name__ == '__main__':
    a = Test()
    print(a.test())
