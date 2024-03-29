# -*- coding: utf-8 -*-

# Plugin para o Dia, para importar tabelas do PostgreSQL para um diagrama
# Colocar em /usr/share/dia/python

import dia
import gtk
import psycopg2
import psycopg2.extensions
from abc import ABCMeta, abstractmethod

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)


class Connection(object):

    __connection = None

    @staticmethod
    def connect(host, port, user, passwd, db):

        pg_params = ("host='{0}' port='{1}' user='{2}' password='{3}' "
                     "dbname='{4}'".format(host, port, user, passwd, db))

        Connection.__connection = psycopg2.connect(pg_params)

    @staticmethod
    def query(query, qargs=None):
        cursor = Connection.__connection.cursor()
        cursor.execute(query, qargs)
        data = cursor.fetchall()
        cursor.close()

        return data


class Schema(object):

    def __init__(self, name):
        self.name = name
        self.__tables = None
        self.__views = None

    @classmethod
    def with_name(cls, name):

        data = Connection.query(
            "SELECT nspname as name FROM pg_catalog.pg_namespace ns "
            "WHERE nspname = %s",

            (name,)
        )

        if data:
            return Schema(name=data[0][0])
        else:
            return None

    @property
    def tables(self):

        if self.__tables is None:
            self.__tables = Table.all(schema=self)

        return self.__tables

    @property
    def views(self):

        if self.__views is None:
            self.__views = View.all(schema=self)

        return self.__views

    def __unicode__(self):
        return self.name

    def __str__(self):
        return unicode(self).encode('utf-8')


class Relation(object):

    __metaclass__ = ABCMeta

    def __init__(self, schema, name):
        self.schema = schema
        self.name = name
        self.__columns = None

    @property
    def columns(self):

        if self.__columns is None:
            self.__columns = Column.all(self.schema, self)

        return self.__columns

    @classmethod
    @abstractmethod
    def all(cls, schema):
        raise NotImplementedError

    def __unicode__(self):
        return self.name

    def __str__(self):
        return unicode(self).encode('utf-8')

    @classmethod
    def with_name(cls, schema, table_name):
        data = Connection.query(
            "SELECT table_name, table_type FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s",

            (schema.name, table_name,)
        )

        if not data:
            return None
        else:
            r = data[0]
            if r[1] == 'BASE TABLE':
                return Table(schema=schema, name=r[0])
            else:
                return View(schema=schema, name=r[0])


class Table(Relation):

    def __init__(self, schema, name):
        super(Table, self).__init__(schema, name)
        self.__constraints = None
        self.__indexes = None

    @classmethod
    def all(cls, schema):

        data = Connection.query(
            "SELECT table_name, table_type FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
            "ORDER BY table_name",

            (schema.name,)
        )
        return [Table(schema=schema, name=r[0]) for r in data]

    @property
    def constraints(self):
        if self.__constraints is None:
            self.__constraints = Constraint.all(self.schema, self)

        return self.__constraints

    def has_constraint(self, definition):
        return definition in self.constraints


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
            """, (schema.name, table.name,))

        return [Constraint(name=reg[0], definition=reg[1]) for reg in data]


class View(Relation):

    @classmethod
    def all(cls, schema):

        data = Connection.query(
            "SELECT table_name, table_type FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type = 'VIEW' "
            "ORDER BY table_name",

            (schema.name,)
        )
        return [View(schema=schema, name=r[0]) for r in data]


class Column(object):

    def __init__(self, schema, table, name, data_type="", is_nullable=True,
                 character_maximum_length=None, numeric_precision=None):
        self.schema = schema
        self.table = table
        self.name = name
        self.__is_nullable = is_nullable
        self.__data_type = data_type
        self.__character_maximum_length = character_maximum_length
        self.__numeric_precision = numeric_precision

    @classmethod
    def all(cls, schema, table):

        data = Connection.query(
            "SELECT column_name as name, is_nullable, data_type, "
            "character_maximum_length, numeric_precision "
            "FROM information_schema.columns "
            "WHERE table_schema=%s and table_name=%s",

            (schema.name, table.name,)
        )

        return [Column(schema=schema, table=table, name=r[0], is_nullable=r[1],
                       data_type=r[2], character_maximum_length=r[3],
                       numeric_precision=r[4])
                for r in data]

    @property
    def data_type(self):

        if (self.__data_type == "character varying"
           and self.__character_maximum_length):
            return u"%s(%d)" % (self.__data_type,
                                self.__character_maximum_length)

        elif (self.__data_type == "integer"
              or self.__data_type == "double precision"):
            return u"%s(%d)" % (self.__data_type, self.__numeric_precision)

        else:
            return self.__data_type

    @property
    def is_nullable(self):
        return isinstance(self.table, Table) and self.__is_nullable == "YES"

    @property
    def is_pk(self):
        return (isinstance(self.table, Table)
                and self.table.has_constraint(
                    'PRIMARY KEY ({0})'.format(self.name)
                    )
                )

    @property
    def is_unique(self):
        return (isinstance(self.table, Table)
                and self.table.has_constraint('UNIQUE ({0})'.format(self.name))
                )

    def __unicode__(self):
        return self.name

    def __str__(self):
        return unicode(self).encode('utf-8')


def attribute(name, ftype, pk=False, nullable=True, unique=False):
    return (name, ftype, '', int(pk), int(nullable), int(unique))


class PgImportDialog(object):

    def __init__(self, layer):

        self.dia_layer = layer

        self.window = gtk.Window()
        self.window.set_title("Import PostgreSQL Tables")

        vbox = gtk.VBox(True, 0)

        self.host_entry = self._create_entry("Host: ",     vbox, "localhost")
        self.port_entry = self._create_entry("Port: ",     vbox, "5432")
        self.user_entry = self._create_entry("Username: ", vbox, "postgres")
        self.passwd_entry = self._create_entry("Password: ", vbox)
        self.db_entry = self._create_entry("Database: ", vbox)
        self.schema_entry = self._create_entry("Schema: ",   vbox)
        self.table_entry = self._create_entry("Table (blank for all): ", vbox)

        self.passwd_entry.set_visibility(False)

        self.prefix_opt = gtk.CheckButton("Use schema prefix on name", False)
        vbox.pack_start(self.prefix_opt)
        self.prefix_opt.show()

        import_btn = gtk.Button("Import")
        import_btn.connect("clicked", self._on_import_btn_click)

        cancel_btn = gtk.Button("Cancel")
        cancel_btn.connect("clicked", self._on_cancel)

        btn_hbox = gtk.HBox(True, 0)
        btn_hbox.pack_start(import_btn, True, True, 2)
        btn_hbox.pack_start(cancel_btn, True, True, 2)

        import_btn.show()
        cancel_btn.show()

        vbox.pack_start(btn_hbox, True, True, 2)
        btn_hbox.show()

        self.window.add(vbox)
        vbox.show()

        self.window.show()

    def _create_entry(self, text, vbox, placeholder=""):

        hbox = gtk.HBox(True, 0)

        label = gtk.Label(text)
        hbox.pack_start(label, expand=True, fill=True, padding=2)
        label.show()

        entry = gtk.Entry()
        hbox.pack_start(entry, expand=True, fill=True, padding=2)
        entry.set_text(placeholder)
        entry.show()

        vbox.pack_start(hbox, expand=True, fill=True, padding=2)
        hbox.show()

        return entry

    def _add_table(self, table, x, y, schema_prefix=False):
        dia_table, h1, h2 = (dia.get_object_type("Database - Table")
                             .create(x, y))

        dia_table.properties['name'] = (schema_prefix and
                                        "{0}.{1}".format(table.schema.name,
                                                         table.name)
                                        or table.name)

        dia_table.properties['bold_primary_keys'] = True

        dia_table.properties['attributes'] = tuple(
            [attribute(name=c.name, ftype=c.data_type, nullable=c.is_nullable,
                       pk=c.is_pk, unique=c.is_unique)
             for c in table.columns]
        )

        self.dia_layer.add_object(dia_table)
        return dia_table

    def _add_view(self, view, x, y, schema_prefix=False):
        dia_table, h1, h2 = (dia.get_object_type("Database - Table")
                                .create(x, y))

        dia_table.properties['name'] = (schema_prefix and
                                        "{0}.{1}".format(view.schema.name,
                                                         view.name)
                                        or view.name)

        dia_table.properties['attributes'] = tuple(
            [attribute(name=c.name, ftype=c.data_type, nullable=False)
             for c in view.columns]
        )

        dia_table.properties['comment'] = 'view'
        dia_table.properties['visible_comment'] = True
        self.dia_layer.add_object(dia_table)
        return dia_table

    def _on_import_btn_click(self, *args):

        SPACING = 3
        MAX_X = 100

        try:
            Connection.connect(host=self.host_entry.get_text(),
                               port=self.port_entry.get_text(),
                               user=self.user_entry.get_text(),
                               passwd=self.passwd_entry.get_text(),
                               db=self.db_entry.get_text())

            schema = Schema.with_name(self.schema_entry.get_text())
            table_name = self.table_entry.get_text().strip()

            if table_name:

                rel = Relation.with_name(schema, table_name)

                if isinstance(rel, Table):
                    self._add_table(rel, 0, 0, self.prefix_opt.get_active())
                elif isinstance(rel, View):
                    self._add_view(rel, 0, 0, self.prefix_opt.get_active())
                else:
                    dia.message(2, "Table not found")

            else:
                x, y, max_y = 0, 0, 0

                for table in schema.tables:

                    dia_table = self._add_table(table, x, y,
                                                self.prefix_opt.get_active())

                    x = dia_table.bounding_box.right + SPACING
                    max_y = max(max_y, dia_table.bounding_box.bottom)

                    if x > MAX_X:
                        x = 0
                        y = max_y + SPACING

                for view in schema.views:

                    dia_table = self._add_view(view, x, y,
                                               self.prefix_opt.get_active())

                    x = dia_table.bounding_box.right + SPACING
                    max_y = max(max_y, dia_table.bounding_box.bottom)

                    if x > MAX_X:
                        x = 0
                        y = max_y + SPACING

        except Exception as e:
            import sys
            import os
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            dia.message(2, "{0}, {1}, {2}, {3}".format(exc_type, e.message,
                                                       fname, exc_tb.tb_lineno)
                        )

        else:
            dia.update_all()
            self._on_cancel()

    def _on_cancel(self, *args):
        self.window.destroy()


def main(data, flags):
    try:
        active_display = dia.active_display()
        diagram = active_display.diagram
        active_layer = diagram.data.active_layer
        PgImportDialog(active_layer)

    except ImportError:

        dia.message(0, "Dialog creation failed. Missing pygtk?")


dia.register_action("PgImport", "Import PostgreSQL Tables",
                    "/DisplayMenu/Dialogs/DialogsExtensionStart",
                    main)
