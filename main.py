import os
import sys
import webapp2
import jinja2
import logging
import datetime

from google.appengine.api import users
from google.appengine.api import search
from google.appengine.ext.webapp.util import run_wsgi_app

# add custom libs to path (e.g. import lib.my_lib)
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

from lib.markdown2 import markdown
from mail import Mail
from tools import get_title_path, \
                  user_query, \
                  elapsed_human_time, \
                  MAX_POSTS_PER_PAGE

# jinja setup (including custom formatting for date for template rendering)
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
loader = jinja2.FileSystemLoader(template_dir)
jinja_env = jinja2.Environment(loader=loader, autoescape = False)
jinja_env.filters['date'] = lambda date: date.strftime("%Y-%m-%d")
jinja_env.filters['datetime'] = lambda dt: dt.strftime("%Y-%m-%d %H:%M:%S")   

        
class Handler(webapp2.RequestHandler):

    # some handy reusable handlers for template rendering and some basic routing
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
        
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))
    
    def admin_or_login(self):
        user = users.get_current_user()
        if not user or not users.is_current_user_admin():
            login_url = users.create_login_url(self.request.uri)
            self.redirect(login_url)
            
    def view_posts(self, posts):
        if posts:
            for p in posts:
                p.tdelta = elapsed_human_time(datetime.datetime.now(),
                                              p.birthday)
                p.body = markdown(p.body, output="html5")
                                              
            self.render('view-blog.html', posts=posts)
        else:
            self.redirect('/404', abort=True)        

class NewHandler(Handler):

    # let's start off with a clean slate and start a new blog post
    def get(self):
        self.admin_or_login()
        self.render('new-blog-post.html')

    # new post coming in
    def post(self):
        self.admin_or_login()

        # get new post DB properties  
        title = self.request.get('post-title')
        body = self.request.get('post-body')
        if not title or not body:   # forgot something - make user go back
            return self.render('new-blog-post.html',
                                post_title=title,
                                post_body=body)
        
        title_path = get_title_path(title, character_limit=30)
        
        today = datetime.date.today()
        offset = len(Mail.get_posts_by_date(today)) # TODO: use gql.count() instead of len(posts)
        
        # put post in DB
        mail_key = Mail(title=title,
                        title_path=title_path,
                        body=body,
                        bday_offset=offset).put()
        
        # get blog post document search properties
        fields = [search.TextField(name='title', value=title),
                  search.TextField(name='body', value=body)]
        doc = search.Document(doc_id=mail_key.urlsafe(), fields=fields)
        
        # put blog post in document search
        try:
            search.Index(name='post-search').put(doc)
        except search.Error:
            logging.error('Document search PUT failed')
        
        # TODO: small bug - have to refresh after redirect
        self.redirect('/blog')
        
class FrontHandler(Handler):

    # either take a user search query or show the top posts
    def get(self, limit=MAX_POSTS_PER_PAGE):
        query = self.request.get('q') or \
                self.request.get('query') or \
                self.request.get('s') or \
                self.request.get('search')
        
        if query:        
            post_keys = user_query(query)
            posts = Mail.get_posts_by_key_list(post_keys, limit=limit)
        else:
            posts = Mail.get_top_posts(limit=limit)
            
        self.view_posts(posts)

class DateHandler(Handler):

    # show your posts for a day in history (optional offset for specific post)
    def get(self, year, month, day, offset=None, limit=MAX_POSTS_PER_PAGE):
        if offset is not None:
            offset = int(offset)
            limit = 1
            
        year, month, day = map(int, (year, month, day))
        date = datetime.datetime(year, month, day)
        
        posts = Mail.get_posts_by_date(date, limit=limit, offset=offset)
        self.view_posts(posts)

class TitlePathHandler(Handler):

    # get your post by the title (shows duplicate titles in descending order)
    def get(self, title_path, limit=MAX_POSTS_PER_PAGE):
        posts = Mail.get_posts_by_title_path(title_path, limit=limit)
        self.view_posts(posts)
        
class NotFoundPage(Handler):
    def get(self):
        self.error(404)
        self.render('404.html')


routes = [('/post/?', NewHandler),
          ('/blog/?', FrontHandler),
          ('/blog/(\d{4})[-. /](\d{1,2})[-. /](\d{1,2})/?', DateHandler),
          ('/blog/(\d{4})[-. /](\d{1,2})[-. /](\d{1,2})/(\d+)/?', DateHandler), #TODO: combine date regexes
          ('/blog/(.*)/', TitlePathHandler),
          ('/blog/(.*)', TitlePathHandler), # TODO: this was a hack for optional ending '/'
          ('/.*', NotFoundPage)]
        
app = webapp2.WSGIApplication(routes, debug=True)

if __name__ == "__main__":    
    run_wsgi_app(app)
