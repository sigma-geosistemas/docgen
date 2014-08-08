# -*- coding: utf-8 -*-
from jinja2 import Environment, PackageLoader

from .models import Schema

__env = Environment(loader=PackageLoader('docgen', 'templates'))


def __create_doc(path, schema):

    """ Cria a documentação em markdown de um objeto Schema na pasta 'path' """

    template = __env.get_template('schema.md')
    fo = open(path+"/"+schema.name+".md", "w")
    fo.write(template.render(schema=schema).encode('utf-8'))
    fo.close()


def doc_schema(path, schema):

    """ Cria a documentação para um schema de nome 'schema' na pasta 'path' """

    s = Schema.with_name(schema)

    if not s:
        print "Schema com nome '%s' não encontrado." % (schema,)
    else:
        __create_doc(path, s)


def doc_all(path):

    """ Cria na pasta 'path' as documentações
        para todos os schemas do banco de dados
    """

    schemas = Schema.all()

    if not schemas:
        print "Nenhum schema encontrado."

    for s in schemas:
        __create_doc(path, s)
