# -*- coding: utf-8 -*-
import sys
import doc
import sync


def __not_found():
    print "Comando '%s' não econtrado." % (sys.argv[1],)


def __doc_all():

    """ Gera a documentação de todos os schemas
        Utilização: doc_all path
    """

    if len(sys.argv) < 3:
        print "Caminho não especificado. Utilize 'doc_all path'"
        return

    doc.doc_all(sys.argv[2])


def __doc_schema():
    """ Gera a documentação de um schema específico
        Utilização: doc_schema path schema
    """

    if len(sys.argv) < 4:
        print "Argumentos inválidos. Utilize 'doc_schema path schema'"
        return

    doc.doc_schema(sys.argv[2], sys.argv[3])


def __all_yamls():

    """ Gera todos yamls de todos os schemas
        Utilização: doc_all path
    """

    if len(sys.argv) < 3:
        print "Caminho não especificado. Utilize 'all_yaml path'"
        return

    sync.all_yamls(sys.argv[2])


def __schema_yaml():
    """ Gera o yaml de um schema específico
        Utilização: doc_schema path schema
    """

    if len(sys.argv) < 4:
        print "Argumentos inválidos. Utilize 'schema_yaml path schema'"
        return

    sync.schema_yaml(sys.argv[2], sys.argv[3])


def __sync_schema():
    """ Sincroniza as descrições do banco de dados
        com as do yaml que descreve o schema.
        Utilização: sync_schema path schema
    """

    if len(sys.argv) < 4:
        print "Argumentos inválidos. Utilize 'sync_schema path schema'"
        return

    sync.sync_schema(sys.argv[2], sys.argv[3])


def __sync_all():

    """ Sincroniza as descrições do banco de dados de todos
        schemas cujos yamls se encontram na pasta passada
        como argumento.
    """

    if len(sys.argv) < 3:
        print "Caminho não especificado. Utilize 'sync_all path'"
        return

    sync.sync_all(sys.argv[2])


def __switch_command():
    return {
        "doc_all": __doc_all,
        "doc_schema": __doc_schema,
        "schema_yaml": __schema_yaml,
        "all_yamls": __all_yamls,
        "sync_schema": __sync_schema,
        "sync_all": __sync_all
    }.get(sys.argv[1], __not_found)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Comando não especificado."
    else:
        __switch_command()()
