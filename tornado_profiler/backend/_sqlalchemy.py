#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json

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
        from sqlalchemy import Column, Text, Float, Integer, String
        from sqlalchemy.orm import deferred

        base = declarative_base()

        class Measurement(base):
            """Table used to store measurements"""
            __tablename__ = "measurements"

            id = Column(Integer, primary_key=True)
            name = Column(Text, nullable=False)
            method = Column(String(32), nullable=False)
            context = deferred(Column(Text, nullable=True))

            begin_time = Column(Float, nullable=True)
            finish_time = Column(Float, nullable=True)
            elapse_time = Column(Float, nullable=False)

            def __repr__(self):
                return "<Measurement {id}, {name}, {method}>".format(
                    id=self.id, name=self.name, method=self.method
                )

        base.metadata.create_all(self.db_engine)
        globals()["Base"] = base
        globals()["Measurement"] = Measurement

    @classmethod
    def get_name(cls):
        return "sqlalchemy"

    def is_nonblock(self):
        # TODO: is there a better way to know whether sqlite in memory?
        url = self.db_engine.url
        if str(url) == "sqlite://":
            return True

        return False

    def insert(self, **kwargs):
        # Prevent IDE from error reporting
        Measurement = globals()["Measurement"]
        measurement = Measurement(**kwargs)

        session = self.db_pool()
        session.add(measurement)
        session.commit()

        return measurement

    @staticmethod
    def jsonify(measurement, with_context=False):
        if not measurement:
            return measurement

        data = {
            "id": measurement.id,
            "name": measurement.name,
            "method": measurement.method,
            "begin_time": round(measurement.begin_time, 6),
            "finish_time": round(measurement.finish_time, 6),
            "elapse_time": round(measurement.elapse_time, 6),
        }
        if with_context:
            data["context"] = json.loads(measurement.context or "null")
        return data

    def filter(self, **kwargs):
        from sqlalchemy.orm.attributes import InstrumentedAttribute

        Measurement = globals()["Measurement"]
        session = self.db_pool()
        query = session.query(Measurement)

        _id = kwargs.get("id")
        if _id is not None:
            measurement = query.get(_id)
            with_context = kwargs.get("with_context", True)
            return self.jsonify(measurement, with_context=with_context)

        elapse_time = kwargs.get("elapse_time")
        if elapse_time is not None:
            query = query.filter(Measurement.elapse_time >= elapse_time)

        begin_time = kwargs.get("begin_time")
        if begin_time is not None:
            query = query.filter(Measurement.begin_time >= begin_time)

        finish_time = kwargs.get("finish_time")
        if finish_time is not None:
            query = query.filter(Measurement.finish_time <= finish_time)

        method = kwargs.get("method")
        if method is not None:
            query = query.filter_by(method=method)

        name = kwargs.get("name")
        name_regex = kwargs.get("name_regex")
        if name is not None:
            query = query.filter_by(name=name)
        elif name_regex is not None:
            name_regex = ''.join(['%', name_regex, '%'])
            query = query.filter(Measurement.name.ilike(name_regex))

        sort = kwargs.get("sort", "finish_time,desc").split(",")
        sort_attr = getattr(Measurement, sort[0], None)
        if sort_attr is None or not isinstance(sort_attr, InstrumentedAttribute):
            raise ValueError("Unknown sort attribute %r" % sort[0])
        if len(sort) >= 2:
            order = sort[1].lower()
            if order not in ["asc", "desc"]:
                raise ValueError("Unknown sort order %r" % sort[1])
            else:
                sort_attr = getattr(sort_attr, order)()
        query = query.order_by(sort_attr)

        return_total = kwargs.get("return_total", False)
        if return_total:
            total = query.count()

        offset = kwargs.get("offset")
        if offset is not None:
            query = query.offset(offset)

        limit = kwargs.get("limit")
        if limit is not None:
            query = query.limit(limit)

        with_context = kwargs.get("with_context", False)
        data = [self.jsonify(row, with_context=with_context)
                for row in query.all()]
        if return_total:
            return total, data
        else:
            return data

    def group(self, **kwargs):
        from sqlalchemy import func, or_

        Measurement = globals()["Measurement"]
        session = self.db_pool()
        query = session.query(
            Measurement.name,
            Measurement.method,
            func.count(Measurement.id).label("count"),
            func.min(Measurement.elapse_time).label("min"),
            func.max(Measurement.elapse_time).label("max"),
            func.avg(Measurement.elapse_time).label("avg"),
        ).group_by(
            Measurement.name,
            Measurement.method,
        )

        begin_time = kwargs.get("begin_time")
        if begin_time is not None:
            query = query.filter(Measurement.begin_time >= begin_time)

        finish_time = kwargs.get("finish_time")
        if finish_time is not None:
            query = query.filter(Measurement.finish_time <= finish_time)

        search = kwargs.get("search")
        if search is not None:
            search = ''.join(['%', search, '%'])
            query = query.filter(or_(
                Measurement.name.ilike(search),
                Measurement.method.ilike(search),
            ))
        else:
            method = kwargs.get("method")
            if method is not None:
                query = query.filter_by(method=method)

            name = kwargs.get("name")
            if name is not None:
                query = query.filter_by(name=name)

        sort = kwargs.get("sort", "count,desc").split(",")
        if sort[0] not in ["name", "method", "count", "min", "max", "avg"]:
            raise ValueError("Unknown sort attribute %r" % sort[0])
        if len(sort) >= 2:
            sort[1] = sort[1].lower()
            if sort[1] not in ["asc", "desc"]:
                raise ValueError("Unknown sort order %r" % sort[1])
        query = query.order_by(' '.join(sort))

        return_total = kwargs.get("return_total", False)
        if return_total:
            total = query.count()

        offset = kwargs.get("offset")
        if offset is not None:
            query = query.offset(offset)

        limit = kwargs.get("limit")
        if limit is not None:
            query = query.limit(limit)

        data = [
            dict(
                name=row[0],
                method=row[1],
                count=row[2],
                min=round(row[3], 6),
                max=round(row[4], 6),
                avg=round(row[5], 6),
            )
            for row in query.all()
        ]
        if return_total:
            return total, data
        else:
            return data


if __name__ == '__main__':
    db = Sqlalchemy(db_url="sqlite:///tornado_profiler.db")
    db.initialize()
    print(db.filter())
