# -*- coding: utf-8 -*-
""" Comandos da sincronização de comentários YAML/Banco de Dados """

import yaml
import os
from models import Schema


def __create_yaml(path, schema):
	
	""" Cria o yaml de um objeto Schema na pasta 'path' """

	stream = file(path+"/"+schema.name+".yaml", 'w')
	yaml.safe_dump(schema.to_dic(), stream=stream, encoding=('utf-8'), allow_unicode=True, default_flow_style=False)


def schema_yaml(path, schema):

	""" Cria o yaml para um schema de nome 'schema' na pasta 'path' """

	s = Schema.with_name(schema)

	if not s:
		print "Schema com nome '%s' não encontrado." % (schema,)
	else:
		__create_yaml(path, s)


def all_yamls(path):

	""" Cria na pasta 'path' os yamls para todos os schemas do banco de dados """
	
	schemas = Schema.all()

	if not schemas:
		print "Nenhum schema encontrado."

	for s in schemas:
		__create_yaml(path, s)


def __sync(fname):
	stream = file(fname, 'r')
	print "syncing "+fname
	dic = yaml.safe_load(stream=stream)

	s = Schema.from_dic(dic)

	s.sync_description()

def sync_schema(path,schema):

	""" Sincroniza as descrições de um schema no banco de dados
		de acordo com as descrições num arquivo 'schema'.yaml no
		path especificado.
	"""

	fname = "%s/%s.yaml" % (path,schema)
	if not os.path.isfile(fname):
		print "Arquivo '%s' para o schema '%s' não encontrado." % (fname,schema)
		return

	__sync(fname)

def sync_all(path):

	""" Sincroniza as descrições de todos schemas cujos yamls
		com as descrições estiverem em 'path'
	"""

	for root, dirs, files in os.walk(path):
	    for f in files:
	        fullpath = os.path.join(root, f)
	        if os.path.splitext(fullpath)[1] == '.yaml':
	            __sync(fullpath)
