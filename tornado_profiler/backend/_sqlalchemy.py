#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Text, Numeric, Integer, String


BASE = declarative_base()


class Measurement(BASE):
    """Table used to store measurements"""
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(String(32), nullable=True)
    method = Column(String(32), nullable=True)
    context = Column(Text, nullable=True)

    begin_time = Column(Numeric, nullable=False)
    finish_time = Column(Numeric, nullable=False)
    elapse_time = Column(Numeric, nullable=False)

    def __repr__(self):
        return "<Measurement {id}, {name}, {type}, {method}, {context}, " \
               "{begin_time}, {finish_time}, {elapse_time}>".format(
            id=self.id,
            name=self.name,
            type=self.type,
            method=self.method,
            context=self.context,
            begin_time=self.begin_time,
            finish_time=self.finish_time,
            elapse_time=self.elapse_time,
        )


class Sqlalchemy(object):

    def __init__(self, engine_url="sqlite:///tornado_profiler.db", **kwargs):
        self.db_engine = create_engine(engine_url, **kwargs)
        self.db_pool = sessionmaker(bind=self.db_engine, autocommit=False)

    def init_database(self):
        BASE.metadata.create_all(self.db_engine)

    def insert(self, **kwargs):
        measurement = Measurement(**kwargs)

        session = self.db_pool()
        session.add(measurement)
        session.commit()
        print(measurement)
        return measurement

    def get_all(self):
        session = self.db_pool()

        print(session.query(Measurement).all())


if __name__ == '__main__':
    db = Sqlalchemy()
    db.init_database()
    #db.insert(name="123", type="111", method="22", begin_time=100, finish_time=100, elapse_time=1)
    db.get_all()
