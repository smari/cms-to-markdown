#!/usr/bin/python
#coding:utf-8
#
#  Joomla to Markdown converter
#
import os
import sys
import click
import html2text
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.sql import select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy_utils import database_exists

def make_markdown(result, target):
    outfile = os.path.join(target, "%06d-%s.md" % (result.id, result.alias))
    print u"%06d -> %s" % (result.id, outfile)
    h = html2text.HTML2Text()
    try:
        md = h.handle(result.fulltext)
    except:
        print "Couldn't convert to Markdown; falling back to HTML."
        md = result.fulltext
    with open(outfile, "wb+") as fh:
        fh.write("----\n")
        fh.write("title: '%s'\n" % result.title)
        fh.write("alias: '%s'\n" % result.alias)
        fh.write("language: %s\n" % result.language)
        fh.write("author: '%s'\n" % result.created_by)
        fh.write("timestamp: %s\n" % result.created)
        fh.write("----\n")
        # print md
        try:
            fh.write(md.encode("utf-8"))
        except:
            fh.write(md)


def joomla_get_articles(connection, prefix, even_drafts):
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
    if not even_drafts:
        s = s.where(state='1')
    print str(s)
    try:
        results = connection.execute(s)
    except ProgrammingError, e:
        print e, e[0]
        sys.exit()
    return results

def wordpress_get_articles(connection, prefix, even_drafts):
    raise NotImplementedError()
    return []

article_handlers = {
    'joomla': joomla_get_articles,
    'wordpress': wordpress_get_articles,
}


@click.command()
@click.option('--mode', type=click.Choice(['joomla', 'wordpress']))
@click.option('--database', prompt='Database to connect to?',
    help='Database to connect to')
@click.option('--target', prompt='Target directory?', help='Target directory')
@click.option('--even-drafts', default=False, is_flag=True, help='Include unpublished drafts')
@click.option('--table-prefix', default='', help='Database table prefix, if any')
def main(mode, database, target, table_prefix, even_drafts):
    # 1. Connect to PostgreSQL database
    engine = create_engine(database)
    connection = engine.connect()

    # 2. List articles
    results = article_handlers[mode](connection, table_prefix, even_drafts)

    # 3. Generate Markdown
    for result in results:
        make_markdown(result, target)


if __name__ == "__main__":
    main()
