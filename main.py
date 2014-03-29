#!/usr/bin/env python
#coding:utf-8
"""
  Author:   --<zhiyuan>--
  Purpose: 
  Created: 2014/3/28
"""

import os.path

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

import datetime
import torndb
import math
import uimodules

from sphinxapi import *

from tornado.options import define, options

define("port", default=8000, help="run on the given port", type=int)

sphinx_conf = {'q' : '',
               'mode' : SPH_MATCH_ALL,
               'host' : 'localhost',
               'port' : 9312,
               'index' : '*',
               'filtercol' : 'group_id',
               'filtervals' : [],
               'sortby' : '',
               'groupby' : '',
               'groupsort' : '@group desc',
               'limit' : 200
               }

db = torndb.Connection("127.0.0.1", "dht", "root", "admin")

class Sphinx_search():
    def __init__(self):
        self.cl = SphinxClient()
        self.cl.SetServer ( sphinx_conf['host'], sphinx_conf['port'] )
        self.cl.SetMatchMode ( sphinx_conf['mode'] )
        if sphinx_conf['filtervals']:
            self.cl.SetFilter ( sphinx_conf['filtercol'], sphinx_conf['filtervals'] )
        if sphinx_conf['groupby']:
            self.cl.SetGroupBy ( sphinx_conf['groupby'], SPH_GROUPBY_ATTR, groupsort )
        if sphinx_conf['sortby']:
            self.cl.SetSortMode ( SPH_SORT_EXTENDED, sphinx_conf['sortby'] )
        if sphinx_conf['limit']:
            self.cl.SetLimits ( 0, sphinx_conf['limit'], max(sphinx_conf['limit'],200) )
        
    def query(self, q=sphinx_conf['q']):
        res = self.cl.Query ( q, sphinx_conf['index'] )
        results = []
        if res.has_key('matches'):
            for match in res['matches']:
                sql = "select * from magnet where id = %s"
                result = db.query(sql,match['id'])
                results.append(result[0])
        return results

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')

class ListHandler(tornado.web.RequestHandler):
    def get(self, q, currentPage):

        def listfile(files):
            return [(file.split("$||$")) for file in files.split("@||@")]

        q=tornado.escape.url_unescape(q)
        if q[0] in (u'$', u'\uffe5'):
            sql = "select * from magnet where name like %s"
            results = db.query(sql,("%"+q[1:]+"%"))
        elif q =='top100':
            sql = u'SELECT magnet.*,query from magnet LEFT JOIN hash_info ON magnet.info_hash\
            = hash_info.`hash` WHERE hash_info.`query` > 1000 ORDER BY hash_info.`query` DESC LIMIT 100'
            results = db.query(sql)
        else:
            try:
                results = ss.query(q)
            except:
                results = None

        if results:
            
            #pagination code
            try:
                currentPage = int(currentPage)
            except:
                currentPage = 1
            newsItemsPerPage = 20
            totalNewsItems = len(results)
            totalPages = int(math.ceil(totalNewsItems/newsItemsPerPage))+1
            if not totalNewsItems%newsItemsPerPage:
                totalPages = totalPages-1
       
            startNewsItemNumber = (int(currentPage) - 1) * newsItemsPerPage
            lastNewsItemNumber = startNewsItemNumber + newsItemsPerPage
            results = results[startNewsItemNumber:lastNewsItemNumber]
            self.render('list.html', results=enumerate(results), currentPage=currentPage, totalPages=totalPages, listfile=listfile)
        else:
            self.render('list.html', results=results)

class LogHandler(tornado.web.RequestHandler):
    
    def get(self, ym, d):
        if ym == '0000-00':
            ym = datetime.datetime.now().strftime("%Y-%m")
        if d == '-00':
            d = datetime.datetime.now().strftime("-%d")
        format = '%Y-%m-%d'
        dt=datetime.datetime.strptime(ym+d,format)
        sql = "SELECT * FROM run_log WHERE log_date = %s ORDER BY id DESC"
        logs = db.query(sql,dt.date())
        self.render('log.html',logs=logs, dt=dt)
        
if __name__ == '__main__':
    tornado.options.parse_command_line()

    settings = {
        "template_path": os.path.join(os.path.dirname(__file__), "templates"),
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "ui_modules": uimodules
    }

    app = tornado.web.Application(
        handlers=[(r'/', IndexHandler), 
                  (r'/(.+)/(\d{,2})', ListHandler),
                  (r'/log/(\d{4}-\d{1,2})/(-\d{1,2})', LogHandler)],
        **settings
)
    ss = Sphinx_search()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
