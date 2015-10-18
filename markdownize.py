#!/usr/bin/python
#coding:utf-8
#
#  Joomla to Markdown converter
#
import os
import sys
import click
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.sql import select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy_utils import database_exists

def make_markdown(result, target):
    print u"Converting '%d' to Markdown in '%s'" % (result.id, target)
    fh = open(os.path.join(target, "%05d-%s.md" % (result.id, result.alias)), "w+")
    fh.write("----\n")
    fh.write("title: '%s'\n" % result.title)
    fh.write("alias: '%s'\n" % result.alias)
    fh.write("language: %s\n" % result.language)
    fh.write("author: '%s'\n" % result.created_by)
    fh.write("timestamp: %s\n" % result.created)
    fh.write("----\n")
    fh.write(result.fulltext)

def joomla_get_articles(connection, prefix):
    if prefix: prefix = "%s_" % prefix
    metadata = MetaData()
    joomla_articles = Table('%scontent' % prefix, metadata,
        Column('id', Integer, primary_key=True),
        Column('title', String),
        Column('alias', String),
        Column('fulltext', String),
        Column('state', String),
        Column('language', String),
        Column('created_by', Integer),
        Column('created', String),
        Column('modified', String),
        Column('modified_by', Integer),
    )
    s = select([joomla_articles])
    print str(s)
    try:
        results = connection.execute(s)
    except ProgrammingError, e:
        print e, e[0]
        sys.exit()
    return results


@click.command()
@click.option('--joomla-table-prefix', default='')
@click.option('--database', prompt='Database to connect to?',
    help='Database to connect to')
@click.option('--target', prompt='Target directory?', help='Target directory')
def main(database, target, joomla_table_prefix, **kwargs):
    # 1. Connect to PostgreSQL database
    engine = create_engine(database)
    connection = engine.connect()

    # if not database_exists(engine):
    #    print "Database %s does not exist" % database
    #    return

    # 2. List articles
    results = joomla_get_articles(connection, joomla_table_prefix)

    # 3. Generate Markdown
    for result in results:
        make_markdown(result, target)


if __name__ == "__main__":
    main()
