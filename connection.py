# -*- coding: utf-8 -*-
import psycopg2
import psycopg2.extensions

from local_settings import PG_PARAMS

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)


class Connection(object):

    __connection = psycopg2.connect(PG_PARAMS)
    __connection.autocommit = True

    @staticmethod
    def query(query, qargs=None):
        cursor = Connection.__connection.cursor()
        cursor.execute(query, qargs)
        data = cursor.fetchall()
        cursor.close()

        return data

    @staticmethod
    def execute(statement, qargs=None):
        cursor = Connection.__connection.cursor()
        cursor.execute(statement, qargs)
        cursor.close()
        Connection.__connection.commit()
