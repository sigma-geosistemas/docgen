# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod
import warnings
from exceptions import RuntimeWarning

from connection import Connection


class Schema(object):

    """Representa um Schema no banco de dados"""

    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.__tables = None
        self.__views = None

    @classmethod
    def all(cls):

        """ Retorna uma lista com objetos do tipo Schema
            para todos os Schemas do banco de dados
        """

        data = Connection.query(
            "SELECT nspname as name, "
            "pg_catalog.obj_description(ns.oid,'pg_namespace') as description "
            "FROM pg_catalog.pg_namespace ns  "
            "WHERE nspname != 'information_schema' "
            "AND nspname not LIKE 'pg_%' ORDER BY nspname")
        return [Schema(name=reg[0], description=reg[1]) for reg in data]

    @classmethod
    def with_name(cls, name):

        """ Retorna um objeto Schema referente ao schema com nome indicado.
            None caso não haja nenhum.
        """

        data = Connection.query(
            "SELECT nspname as name, "
            "pg_catalog.obj_description(ns.oid,'pg_namespace') as description "
            " FROM pg_catalog.pg_namespace ns  WHERE nspname = %s", (name,))

        if data:
            return Schema(name=data[0][0], description=data[0][1])
        else:
            return None

    def tables(self):

        """ Retorna todas tabelas que fazem parte do schema """

        # Executa a query para buscar elas somente uma vez
        if self.__tables is None:
            self.__tables = Table.all(schema=self.name)

        return self.__tables

    def views(self):

        """ Retorna todas views que fazem parte do schema """

        # Executa a query para buscar elas somente uma vez
        if self.__views is None:
            self.__views = View.all(schema=self.name)

        return self.__views

    def to_dic(self):

        """ Transforma o objeto Schema em um dicionário """

        tables = []
        views = []

        for table in self.tables():
            tables.append(table.to_dic())

        for view in self.views():
            views.append(view.to_dic())

        return {
            "1. name": self.name,
            "2. description": self.description,
            "3. tables": tables,
            "4. views": views
        }

    @classmethod
    def from_dic(cls, dic):

        """ Cria um objeto Schema a partir de um dicionário """

        s = Schema(name=dic["1. name"], description=dic["2. description"])

        tables = []
        for t in dic["3. tables"]:
            tables.append(Table.from_dic(t, s.name))
        s.set_tables(tables)

        views = []
        for v in dic["4. views"]:
            views.append(View.from_dic(v, s.name))
        s.set_views(views)

        return s

    def set_tables(self, tables):
        self.__tables = tables

    def set_views(self, views):
        self.__views = views

    def sync_description(self):

        """ Salva a descrição do schema e de suas tabelas e views
            no banco de dados
        """

        try:
            if self.description is not None:
                Connection.execute(
                    u"""COMMENT ON SCHEMA {0} IS %s""".format(self.name,),
                    (self.description,))
            else:
                Connection.execute(
                    u"""COMMENT ON SCHEMA {0} IS NULL""".format(self.name,))

            for table in self.tables():
                table.sync_description()

            for view in self.views():
                view.sync_description()

        except Exception, e:
            warnings.warn(
                "Erro ao sincronizar o schema {0}: {1}"
                .format(self.name, e),
                RuntimeWarning)


class Relation(object):

    """ Representa uma tabela ou view no banco de dados """

    __metaclass__ = ABCMeta

    def __init__(self, schema, name, description):
        self.schema = schema
        self.name = name
        self.description = description
        self.__columns = None

    def columns(self):

        """ Retorna todas colunas que fazem parte da relação """

        # Executa a query para buscar elas somente uma vez
        if self.__columns is None:
            self.__columns = Column.all(self.schema, self.name)

        return self.__columns

    @classmethod
    @abstractmethod
    def all(cls, schema):
        """ Retorna uma lista com relações do schema conforme o tipo."""
        raise NotImplementedError("Método não implementado na classe base.")

    def to_dic(self):

        """ Transforma o objeto Relation em um dicionário """

        dic = {
            "1. name": self.name,
            "2. description": self.description,
        }

        columns = []
        for column in self.columns():
            columns.append(column.to_dic())
        dic["3. columns"] = columns

        return dic

    @abstractmethod
    def sync_description(self):
        """ Salva a descrição da relação e de suas colunas
            (caso seja uma tabela) no banco de dados
        """

        raise NotImplementedError("Método não implementado na classe base.")

    @classmethod
    @abstractmethod
    def from_dic(cls, dic, schema):
        """ Cria um objeto Relation a partir de um dicionário """
        raise NotImplementedError("Método não implementado na classe base.")

    def set_columns(self, columns):
        self.__columns = columns


class Table(Relation):

    """ Representa uma tabela no banco de dados """

    def __init__(self, schema, name, description):
        super(Table, self).__init__(schema, name, description)
        self.__constraints = None
        self.__indexes = None

    @classmethod
    def all(cls, schema):

        """ Retorna uma lista com objetos do tipo Table
            referente às tabelas do schema.
        """

        data = Connection.query(
            "SELECT table_name, "
            "obj_description((%s || '.' || table_name)::regclass, 'pg_class') "
            "as description, table_type "
            "FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
            "ORDER BY table_name", (schema, schema,))

        return [Table(schema=schema, name=r[0], description=r[1])
                for r in data]

    def sync_description(self):
        try:
            if self.description is not None:
                Connection.execute(
                    u"""COMMENT ON TABLE "{0}"."{1}" IS %s"""
                    .format(self.schema, self.name,),

                    (self.description,)
                )

                for col in self.columns():
                    col.sync_description()
            else:
                Connection.execute(
                    u"""COMMENT ON TABLE "{0}"."{1}" IS NULL"""
                    .format(self.schema, self.name,)
                )

        except Exception, e:
            warnings.warn(
                "Erro ao sincronizar a tabela {0}.{1}: {2}"
                .format(self.schema, self.name, e),
                RuntimeWarning)

    @classmethod
    def from_dic(cls, dic, schema):

        """ Cria um objeto Table a partir de um dicionário """

        rel = Table(name=dic["1. name"], schema=schema,
                    description=dic["2. description"])

        columns = []
        for c in dic["3. columns"]:
            column = Column.from_dic(dic=c, schema=schema, table=rel.name)
            columns.append(column)
        rel.set_columns(columns)

        return rel

    def constraints(self):
        if self.__constraints is None:
            self.__constraints = Constraint.all(self.schema, self.name)

        return self.__constraints

    def indexes(self):
        if self.__indexes is None:
            self.__indexes = Index.all(self.schema, self.name)

        return self.__indexes


class Index(object):
    def __init__(self, name, itype, fields):
        self.name = name
        self.itype = itype
        self.fields = fields

    @classmethod
    def all(cls, schema, table):
        data = Connection.query(
            """SELECT i.relname, am.amname,
               ARRAY(
                   SELECT pg_get_indexdef(idx.indexrelid, k + 1, true)
                   FROM generate_subscripts(idx.indkey, 1) as k
                   ORDER BY k
               ) as indkey_names

               FROM   pg_index as idx
               JOIN   pg_class as i ON i.oid = idx.indexrelid
               JOIN   pg_am as am ON i.relam = am.oid

               WHERE indrelid =  (%s || '.' || %s)::regclass""",

            (schema, table,)
        )

        return [Index(name=reg[0], itype=reg[1], fields=reg[2])
                for reg in data]


class Constraint(object):
    def __init__(self, name, definition):
        self.name = name
        self.definition = definition

    @classmethod
    def all(cls, schema, table):
        data = Connection.query(
            """ SELECT conname,
                pg_catalog.pg_get_constraintdef(r.oid, true) as condef
                FROM pg_catalog.pg_constraint r
                WHERE conrelid::regclass = (%s || '.' || %s)::regclass
                """,

            (schema, table,)
        )

        return [Constraint(name=reg[0], definition=reg[1]) for reg in data]


class View(Relation):

    """ Representa uma view no banco de dados """

    @classmethod
    def all(cls, schema):

        """ Retorna uma lista com objetos do tipo View
            referente às views do schema.
        """

        data = Connection.query(
            "SELECT table_name, "
            "obj_description((%s || '.' || table_name)::regclass, 'pg_class') "
            "as description, table_type "
            "FROM information_schema.tables WHERE table_schema = %s "
            "AND table_type = 'VIEW' "
            "ORDER BY table_name",

            (schema, schema,)
        )

        return [View(schema=schema, name=r[0], description=r[1]) for r in data]

    def sync_description(self):
        try:
            if self.description is not None:
                Connection.execute(
                    u"""COMMENT ON VIEW "{0}"."{1}" IS %s"""
                    .format(self.schema, self.name,),

                    (self.description,)
                )

                for col in self.columns():
                    col.sync_description()
            else:
                Connection.execute(
                    u"""COMMENT ON VIEW "{0}"."{1}" IS NULL"""
                    .format(self.schema, self.name,)
                )

        except Exception, e:
            warnings.warn(
                "Erro ao sincronizar a view {0}.{1}: {2}"
                .format(self.schema, self.name, e),
                RuntimeWarning)

    @classmethod
    def from_dic(cls, dic, schema):

        """ Cria um objeto View a partir de um dicionário """

        rel = View(name=dic["1. name"], schema=schema,
                   description=dic["2. description"])

        columns = []
        for c in dic["3. columns"]:
            column = Column.from_dic(dic=c, schema=schema, table=rel.name)
            columns.append(column)
        rel.set_columns(columns)

        return rel


class Column(object):

    """ Representa uma coluna de uma tabela no banco de dados """

    def __init__(self, schema, table, name, data_type="", description=u"",
                 default=None, is_nullable=True, character_maximum_length=None,
                 numeric_precision=None):

        self.schema = schema
        self.table = table
        self.name = name
        self.description = description
        self.default = default
        self.is_nullable = is_nullable
        self.data_type = data_type
        self.character_maximum_length = character_maximum_length
        self.numeric_precision = numeric_precision

    def formatted_type(self):

        """ Retorna o tipo da tabela com a formatação correta """

        if (self.data_type == "character varying"
           and self.character_maximum_length):
            return u"%s(%d)" % (self.data_type, self.character_maximum_length)

        elif (self.data_type == "integer"
              or self.data_type == "double precision"):
            return u"%s(%d)" % (self.data_type, self.numeric_precision)

        else:
            return self.data_type

    def formatted_default(self):

        """ Formata o default da coluna,
            retornando 'Nenhum' caso não haja um default.
        """

        return self.default or u"Nenhum"

    def formatted_is_nullable(self):

        """ Formata o atributo is_nullable, retornando 'Sim' ou 'Não'. """

        return (self.is_nullable == "NO") and u"Não" or u"Sim"

    def to_dic(self):

        """ Transforma o objeto Column em um dicionário """

        return {
            "1. name": self.name,
            "2. description": self.description
        }

    @classmethod
    def from_dic(cls, dic, schema, table):
        return Column(schema=schema, table=table, name=dic["1. name"],
                      description=dic["2. description"])

    @classmethod
    def all(cls, schema, table):

        """ Retorna uma lista com objetos do tipo Column
            referente à todas colunas da tabela 'table' do schema 'schema'
        """

        data = Connection.query(
            "SELECT column_name as name, "
            "col_description((%s || '.' || %s)::regclass, ordinal_position) "
            "as description, column_default, is_nullable, data_type, "
            "character_maximum_length, numeric_precision "
            "FROM information_schema.columns "
            "WHERE table_schema=%s and table_name=%s",

            (schema, table, schema, table,)
        )

        return [Column(schema=schema, table=table, name=r[0], description=r[1],
                       default=r[2], is_nullable=r[3], data_type=r[4],
                       character_maximum_length=r[5], numeric_precision=r[6])
                for r in data]

    def sync_description(self):

        """ Salva a descrição da coluna no banco de dados """

        try:
            if self.description is not None:
                Connection.execute(
                    u"""COMMENT ON COLUMN "{0}"."{1}"."{2}" IS %s"""
                    .format(self.schema, self.table, self.name,),

                    (self.description,)
                )

            else:
                Connection.execute(
                    u"""COMMENT ON COLUMN "{0}"."{1}"."{2}" IS NULL"""
                    .format(self.schema, self.table, self.name,)
                )

        except Exception, e:
            warnings.warn(
                "Erro ao sincronizar a coluna {0}.{1}.{2}: {3}"
                .format(self.schema, self.table, self.name, e),
                RuntimeWarning
            )
