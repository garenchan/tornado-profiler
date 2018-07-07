#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tornado_profiler.backend import Backend


class Sqlalchemy(Backend):

    def __init__(self, db_url="sqlite:///tornado_profiler.db", **kwargs):
        super(Sqlalchemy, self).__init__()
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import scoped_session, sessionmaker
        except ImportError:
            raise Exception("To use this backend, you should install "
                            "'sqlalchemy' manually. Use command:\n"
                            "'pip install sqlalchemy'.")

        self.db_engine = create_engine(db_url, **kwargs)
        self.db_pool = sessionmaker(bind=self.db_engine, autocommit=False)
        # NOTE: sqlite connection can't share across threads
        if self.db_engine.name == "sqlite":
            self.db_pool = scoped_session(self.db_pool)

    def initialize(self):
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy import Column, Text, Numeric, Integer, String

        base = declarative_base()

        class Measurement(base):
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
                return "<Measurement {id}, {name}, {method}>".format(
                    id=self.id, name=self.name, method=self.method
                )

        base.metadata.create_all(self.db_engine)
        globals()["Base"] = base
        globals()["Measurement"] = Measurement

    def insert(self, **kwargs):
        # Prevent IDE from error reporting
        Measurement = globals()["Measurement"]
        measurement = Measurement(**kwargs)

        session = self.db_pool()
        session.add(measurement)
        session.commit()

        return measurement

    @classmethod
    def get_name(cls):
        return "sqlalchemy"

    def get_all(self):
        # Prevent IDE from error reporting
        Measurement = globals()["Measurement"]

        session = self.db_pool()
        return session.query(Measurement).all()


if __name__ == '__main__':
    db = Sqlalchemy()
    db.initialize()
    print(db.get_all())
