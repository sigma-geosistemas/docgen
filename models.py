# -*- coding: utf-8 -*-
from connection import Connection

class Schema(object):

	"""Representa um Schema no banco de dados"""
	
	def __init__(self, name, description):
		self.name = name
		self.description = description
		self.__tables = None
		self.__views = None

	@staticmethod
	def all():
		
		"""Retorna uma lista com objetos do tipo Schema para todos os Schemas do banco de dados"""

		data = Connection.query("SELECT nspname as name, pg_catalog.obj_description(ns.oid, 'pg_namespace') as description FROM pg_catalog.pg_namespace ns  WHERE nspname != 'information_schema' AND nspname not LIKE 'pg_%' ORDER BY nspname")
		return [Schema(name=reg[0], description=reg[1]) for reg in data]

	@staticmethod
	def with_name(name):

		""" Retorna um objeto Schema referente ao schema com nome indicado. None caso não haja nenhum. """

		data = Connection.query("SELECT nspname as name, pg_catalog.obj_description(ns.oid, 'pg_namespace') as description FROM pg_catalog.pg_namespace ns  WHERE nspname = %s", (name,))

		if data:
			return Schema(name=data[0][0], description=data[0][1])
		else:
			return None

	def tables(self):

		""" Retorna todas tabelas que fazem parte do schema """

		# Executa a query para buscar elas somente uma vez
		if self.__tables is None:
			self.__tables = Relation.all(schema=self.name)

		return self.__tables

	def views(self):

		""" Retorna todas views que fazem parte do schema """

		# Executa a query para buscar elas somente uma vez
		if self.__views is None:
			self.__views = Relation.all(schema=self.name, table_type=u"VIEW")

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

	@staticmethod
	def from_dic(dic):

		""" Cria um objeto Schema a partir de um dicionário """

		s = Schema(name=dic["1. name"], description=dic["2. description"])

		tables = []
		for t in dic["3. tables"]:
			tables.append(Relation.from_dic(t,s.name))
		s.set_tables(tables)


		views = []
		for v in dic["4. views"]:
			views.append(Relation.from_dic(v,s.name))
		s.set_views(views)

		return s


	def set_tables(self, tables):
		self.__tables = tables

	def set_views(self, views):
		self.__views = views


	def sync_description(self):
		
		""" Salva a descrição do schema e de suas tabelas e views no banco de dados """

		if self.description is not None:
			Connection.execute(u"""COMMENT ON SCHEMA {0} IS %s""".format(self.name,), (self.description,))
		else:
			Connection.execute(u"""COMMENT ON SCHEMA {0} IS NULL""".format(self.name,))

		for table in self.tables():
			table.sync_description()

		for view in self.views():
			view.sync_description()


class Relation(object):

	""" Representa uma tabela ou view no banco de dados """
	
	def __init__(self, schema, name, description, table_type):
		self.schema = schema
		self.name = name
		self.description = description
		self.table_type = table_type
		self.__columns = None

	def is_table(self):
		return self.table_type == "BASE TABLE"

	def is_view(self):
		return self.table_type == "VIEW"

	def columns(self):

		""" Retorna todas colunas que fazem parte da tabela """

		# Executa a query para buscar elas somente uma vez
		if self.__columns is None:
			self.__columns = Column.all(self.schema, self.name)

		return self.__columns

	@staticmethod
	def all(schema, table_type="BASE TABLE"):

		""" Retorna uma lista com objetos do tipo table referente às tabelas do schema conforme o tipo. table_type pode ser BASE TABLE ou VIEW """

		data = Connection.query("SELECT table_name, obj_description((%s || '.' || table_name)::regclass, 'pg_class') as description, table_type FROM information_schema.tables WHERE table_schema = %s AND table_type = %s ORDER BY table_name", (schema,schema,table_type,))
		return [Relation(schema=schema, name=r[0], description=r[1], table_type=r[2]) for r in data]

	def to_dic(self):

		""" Transforma o objeto Relation em um dicionário """

		dic = {
			"1. name": self.name,
			"2. description": self.description,
		}

		if self.table_type == "BASE TABLE":
			columns = []
			for column in self.columns():
				columns.append(column.to_dic())
			dic["3. columns"] = columns

		return dic


	def sync_description(self):

		""" Salva a descrição da relação e de suas colunas (caso seja uma tabela) no banco de dados """

		if self.is_table():
			if self.description is not None:
				Connection.execute(u"""COMMENT ON TABLE "{0}"."{1}" IS %s""".format(self.schema,self.name,), (self.description,))
				for col in self.columns():
					col.sync_description()
			else:
				Connection.execute(u"""COMMENT ON TABLE "{0}"."{1}" IS NULL""".format(self.schema,self.name,))

		elif self.is_view():
			if self.description is not None:
				Connection.execute(u"""COMMENT ON VIEW "{0}"."{1}" IS %s""".format(self.schema,self.name,),(self.description,))
			else:
				Connection.execute(u"""COMMENT ON VIEW "{0}"."{1}" IS NULL""".format(self.schema,self.name,))


	@staticmethod
	def from_dic(dic, schema):
		
		""" Cria um objeto Relation a partir de um dicionário """

		tt = ("3. columns" in dic) and "BASE TABLE" or "VIEW"

		rel = Relation(name=dic["1. name"], schema=schema, description=dic["2. description"], table_type=tt)

		if rel.is_table():
			columns = []
			for c in dic["3. columns"]:
				column = Column.from_dic(dic=c, schema=schema, table=rel.name)
				columns.append(column)
			rel.set_columns(columns)

		return rel


	def set_columns(self,columns):
		self.__columns = columns




class Column(object):

	""" Representa uma coluna de uma tabela no banco de dados """
	
	def __init__(self, schema, table, name, data_type="", description=u"", default=None, is_nullable=True, character_maximum_length=None, numeric_precision=None):
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

		if self.data_type == "character varying" and self.character_maximum_length:
			return u"%s(%d)" % (self.data_type, self.character_maximum_length)
		elif self.data_type == "integer" or self.data_type == "double precision":
			return u"%s(%d)" % (self.data_type, self.numeric_precision)
		else:
			return self.data_type

	def formatted_default(self):

		""" Formata o default da coluna, retornando 'Nenhum' caso não haja um default. """

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

	@staticmethod
	def from_dic(dic,schema,table):
		return Column(schema=schema, table=table, name=dic["1. name"], description=dic["2. description"])

	@staticmethod
	def all(schema, table):

		""" Retorna uma lista com objetos do tipo Column referente à todas colunas da tabela 'table' do schema 'schema' """

		data = Connection.query("SELECT column_name as name, col_description((%s || '.' || %s)::regclass, ordinal_position) as description, column_default, is_nullable, data_type, character_maximum_length, numeric_precision FROM information_schema.columns WHERE table_schema=%s and table_name=%s" , (schema, table, schema, table,))
		return [Column(schema=schema, table=table, name=r[0], description=r[1], default=r[2], is_nullable=r[3], data_type=r[4], character_maximum_length=r[5], numeric_precision=r[6]) for r in data]
	

	def sync_description(self):

		""" Salva a descrição da coluna no banco de dados """

		if self.description is not None:
			Connection.execute(u"""COMMENT ON COLUMN "{0}"."{1}"."{2}" IS %s""".format(self.schema, self.table, self.name,), (self.description,))
		else:
			Connection.execute(u"""COMMENT ON COLUMN "{0}"."{1}"."{2}" IS NULL""".format(self.schema, self.table, self.name,))