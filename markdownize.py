#!/usr/bin/python
#coding:utf-8
#
#  Joomla to Markdown converter
#
import os
import sys
import click
import html2text
import slugify
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.sql import select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy_utils import database_exists

class Article:
    def __init__(self):
        self.id = None
        self.title = None
        self.language = None
        self.body = None
        self.slug = None
        self.metadata = {}

    def output(self, target, fallback=True):
        outfile = os.path.join(target, "%06d-%s.md" % (self.id, self.slug))
        print u"%06d -> %s" % (self.id, outfile)
        h = html2text.HTML2Text()
        try:
            if self.language == 'en':
                md = h.handle(self.body.decode('iso-8859-1'))
            else:
                md = h.handle(self.body.decode('utf-8'))
        except Exception, e:
            if not fallback:
                return
            print "Couldn't convert to Markdown; falling back to HTML: ", e
            md = self.body
        with open(outfile, "wb+") as fh:
            fh.write("---\n")
            fh.write("title: \"%s\"\n" % self.title)
            fh.write("slug: \"%s\"\n" % self.slug)
            fh.write("language: \"%s\"\n" % self.language)
            for key,value in self.metadata.iteritems():
                fh.write("%s: \"%s\"\n" % (key, value))
            fh.write("---\n")
            try:
                fh.write(md.encode("utf-8"))
            except:
                fh.write(md)


def joomla_get_articles(connection, prefix, even_drafts):
    joomla_tag_map = Table('%scontentitem_tag_map' % prefix, MetaData(),
        Column('type_alias', String),
        Column('core_content_id', Integer),
        Column('content_item_id', Integer),
        Column('tag_id', Integer),
        Column('tag_date', String),
        Column('type_id', Integer),
    )

    joomla_tags = Table('%stags' % prefix, MetaData(),
        Column('id', Integer, primary_key=True),
        Column('parent_id', Integer),
        Column('title', String),
    )

    joomla_articles = Table('%scontent' % prefix, MetaData(),
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

    s = select([joomla_tags])
    results = connection.execute(s)
    tags = {}
    for t in results:
        tags[t.id] = t.title

    s = select([joomla_articles])
    if not even_drafts:
        s = s.where(joomla_articles.c.state=='1')
    try:
        results = connection.execute(s)
    except ProgrammingError, e:
        print e, e[0]
        sys.exit()

    articles = []
    cnt = 0
    for r in results:
        cnt += 1
        print "\r%d" % (cnt),
        sys.stdout.flush()
        ts = select([joomla_tag_map])
        ts.where(joomla_tag_map.c.content_item_id==r.id)
        try:
            article_tags = connection.execute(ts)
            article_tags = ", ".join([tags[x.tag_id] for x in article_tags])
        except ProgrammingError, e:
            print e, e[0]
            sys.exit()
        # pass
        a = Article()
        a.id = r.id
        a.title = r.title
        a.body = r.fulltext
        a.slug = r.alias
        a.language = r.language[:2]
        a.metadata['tags'] = article_tags
        a.metadata['author'] = r.created_by
        a.metadata['timestamp'] = r.created
        a.metadata['editor'] = r.modified_by
        a.metadata['timestamp_modified'] = r.modified
        articles.append(a)

    print "Done."

    return articles


def wordpress_get_articles(connection, prefix, even_drafts):
    if prefix: prefix = "%s_" % prefix
    metadata = MetaData()
    wp_articles = Table('%swp_posts' % prefix, metadata,
        Column('ID', Integer, primary_key=True),
        Column('post_title', String),
        Column('post_content', String),
        Column('post_status', String),
        Column('post_author', Integer),
        Column('post_date', String),
        Column('post_modified', String),
    )
    s = select([joomla_articles])
    if not even_drafts:
        s = s.where(joomla_articles.c.status=='publish')
    try:
        results = connection.execute(s)
    except ProgrammingError, e:
        print e, e[0]
        sys.exit()

    articles = []
    for r in results:
        a = Article()
        a.id = r.ID
        a.title = r.post_title
        a.body = r.post_content
        a.slug = slugify.slugify(r.post_title)
        a.metadata['author'] = r.post_author
        a.metadata['timestamp'] = r.post_date
        a.metadata['timestamp_modified'] = r.post_modified
        articles.append(a)

    return articles

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
@click.option('--verbose', default=False, is_flag=True)
@click.option('--fallback/--no-fallback', default=True, is_flag=True)
def main(mode, database, target, table_prefix, even_drafts, verbose, fallback):
    # 1. Connect to PostgreSQL database
    engine = create_engine(database)
    connection = engine.connect()

    # 2. List articles
    results = article_handlers[mode](connection, table_prefix, even_drafts)

    # 3. Generate Markdown
    for result in results:
        result.output(target, fallback)

if __name__ == "__main__":
    main()
