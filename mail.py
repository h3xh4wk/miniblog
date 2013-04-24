# DB model for all blog posts (+ all functions for DB queries)

import logging
import datetime

from google.appengine.ext import ndb

class Mail(ndb.Model):
    title = ndb.StringProperty(required=True)
    title_path = ndb.StringProperty(required=False)
    title_hover_text = ndb.StringProperty(required=False)
    body = ndb.TextProperty(required=True)
    birthday = ndb.DateTimeProperty(auto_now_add=True)
    bday_offset = ndb.IntegerProperty(required=True)
    editday = ndb.DateTimeProperty(auto_now=True)

    @staticmethod
    def get_top_posts(limit=None, offset=None):
        post_query = 'ORDER BY birthday DESC'
        posts = Mail.gql(post_query).fetch(limit=limit, offset=offset)
        
        return posts
    
    @staticmethod
    def get_posts_by_date(post_date, limit=None, offset=None):
        if isinstance(post_date, datetime.date):
            post_date = datetime.datetime.combine(post_date, datetime.time())
        elif not isinstance(post_date, datetime.datetime):
            raise TypeError
        
        tomorrow = post_date + datetime.timedelta(days=1)
        
        ndb_date_format = "%Y-%m-%d %H:%M:%S"
        query_range = {'today': post_date.strftime(ndb_date_format), 
                       'tomorrow': tomorrow.strftime(ndb_date_format)}
        
        post_query = ['WHERE',
                      'birthday >= DATETIME(\'%(today)s\')',
                      'AND',
                      'birthday <= DATETIME(\'%(tomorrow)s\')']
        
        # this preserves links using a date offset (essentially so we can
        # index from the *oldest* post being index 0) - this is in contrast
        # to wanting to have the *newest* post when showing more than one
        if offset is None:
            post_query.append('ORDER BY birthday DESC')
        else:
            post_query.append('ORDER BY birthday ASC')
            
        post_query = ' '.join(post_query) % query_range
                              
        posts = Mail.gql(post_query).fetch(limit=limit, offset=offset)
        
        return posts
    
    @staticmethod    
    def get_posts_by_title_path(title_path, limit=None, offset=None):
        post_query = ' '.join(['WHERE',
                               'title_path = \'%s\'',
                               'ORDER BY birthday DESC']) % title_path
                                                    
        posts = Mail.gql(post_query).fetch(limit=limit, offset=offset)
        
        return posts
    
    @staticmethod    
    def get_posts_by_key_list(key_list, limit=None, offset=None):
        if offset:
            key_list = key_list[offset:]
        if limit:
            key_list = key_list[:limit]
            
        try:
            posts = [ndb.get(key) for key in key_list]
        except ndb.BadQueryError:
            logging.error('Bad Mail query: %s' % post_query)
        
        return posts
