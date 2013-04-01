import os
import re
import sys
import webapp2
import jinja2
import logging
import datetime

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import search
from google.appengine.ext.webapp.util import run_wsgi_app

# non-GAE libs (located in app's 'lib/' directory)
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
from lib.markdown2 import markdown

# jinja setup (custom template formatting for date)
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
loader = jinja2.FileSystemLoader(template_dir)
jinja_env = jinja2.Environment(loader=loader, autoescape = False)
jinja_env.filters['date'] = lambda date: date.strftime("%Y-%m-%d")


# quick hack (and not a very good one); write a better solution
def elapsed_human_time(dt1, dt2):
    years = abs(dt1.year - dt2.year)
    if years > 1:
        return [str(years), "years"]

    temp = []    
    months = abs(dt1.month - dt2.month)
    if years:
        temp = [str(years), "year"]
    if months > 1:
        temp += [str(months), "months"]
        return temp
     
    days = abs(dt1.day - dt2.day)
    if months:
        temp = [str(months), "month"]
    if days > 1:
        temp += [str(days), "days"]
        return temp
    
    hours = abs(dt1.hour - dt2.hour)
    if days:
        temp = [str(days), "day"]
    if hours > 1:
        temp += [str(hours), "hours"]
        return temp

    mins = abs(dt1.minute - dt2.minute)
    if hours:
        temp = [str(hours), "hour"]
    if mins > 1:
        temp += [str(mins), "minutes"]
        return temp

    secs = abs(dt1.second - dt2.second)
    if mins:
        temp = [str(mins), "minute"]
    if secs > 1:
        temp += [str(secs), "seconds"]
        return temp
            
    return [str(secs), "second"]

def format_post(post, output="html5"):
    post.body = markdown(post.body, output=output)
    tdelta = elapsed_human_time(datetime.datetime.now(), post.birthday)
    post.tdelta = ' '.join(tdelta) + " " + "ago"
    return post

def get_posts_by_date(date):
    if isinstance(date, datetime.datetime):
        date = date.date()
    
    tomorrow = date + datetime.timedelta(days=1)
    query_range = {'today': date, 
                   'tomorrow': tomorrow}
    
    post_query = " ".join(['WHERE',
                          'birthday >= DATE(\'%(today)s\')',
                          'AND',
                          'birthday <= DATE(\'%(tomorrow)s\')',
                          'ORDER BY birthday ASC']) % query_range
                          
    try:
        posts = Mail.gql(post_query)
    except db.BadQueryError:
        logging.exception('Bad query: %s' % post_query)
        
    return posts      
        

class Mail(db.Model):
    title = db.StringProperty(required=True)
    body = db.TextProperty(required=True)
    birthday = db.DateTimeProperty(auto_now_add=True)
    editday = db.DateTimeProperty(auto_now=True)
    bday_offset = db.IntegerProperty(required=True)
                               
class Handler(webapp2.RequestHandler):
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
            self.redirect(login_url, abort=True)


class PostHandler(Handler):
    def get(self):
        self.admin_or_login()
        self.render('new-blog-post.html')

class MailManHandler(Handler):
    def post(self):
        self.admin_or_login()

        today = datetime.date.today()
        posts = get_posts_by_date(today)
        offset = posts.count()
          
        title = self.request.get('post-title')
        body = self.request.get('post-body')
        mail_key = Mail(title=title, body=body, bday_offset=offset).put()
        
        doc = search.Document(doc_id=str(mail_key),
                              fields=[search.TextField(name='title', value=title),
                                      search.TextField(name='body', value=body)])
        try:
            search.Index(name='post-search').put(doc)
        except search.Error:
            logging.exception('Mail put failed')
        
        self.redirect('/blog')
        
class FrontHandler(Handler):
    def get(self):
        posts = []
        limit = 10
        query = self.request.get('q')
        
        if query:
            try:
                title_desc = search.SortExpression(
                    expression='post-title',
                    direction=search.SortExpression.DESCENDING,
                    default_value='')
                    
                body_desc = search.SortExpression(
                    expression='post-body',
                    direction=search.SortExpression.DESCENDING,
                    default_value='')
                    
                sort = search.SortOptions(
                    expressions=[title_desc, body_desc],
                    limit=1000)
                
                options = search.QueryOptions(
                    limit=limit,
                    sort_options=sort)
                
                query = search.Query(query_string=query, options=options)
                index = search.Index(name='post-search')
                results = index.search(query)

                post_keys = [result.doc_id for result in results.results] 
                posts = [db.get(key) for key in post_keys]
                posts = [format_post(post) for post in posts]
            except:
                self.redirect('/404', abort=True)

        else:
            posts = Mail.gql('ORDER BY birthday DESC').fetch(limit=limit)
            posts = [format_post(post) for post in posts]
        
        self.render('view-blog.html', posts=posts)

class DateHandler(Handler):
    def get(self, year, month, day, offset=0):
        date = datetime.date(int(year), int(month), int(day))
        try:
            posts = get_posts_by_date(date)
            posts = posts.fetch(limit=1, offset=int(offset))
        except db.BadQueryError:
            self.redirect('/404', abort=True)
                       
        posts = [format_post(post) for post in posts]
        
        if posts:
            self.render('view-blog.html', posts=posts)
        else:
            self.redirect('/404', abort=True)
        
class NotFoundPage(Handler):
    def get(self):
        self.error(404)
        self.render('404.html')


routes = [('/post', PostHandler),
          ('/post-already', MailManHandler),
          ('/blog/?', FrontHandler),
          ('/blog/(\d{4})[-. /](\d{1,2})[-. /](\d{1,2})/?', DateHandler),
          ('/blog/(\d{4})[-. /](\d{1,2})[-. /](\d{1,2})/(\d+)', DateHandler),
          ('/.*', NotFoundPage)]
        
app = webapp2.WSGIApplication(routes, debug=True)

if __name__ == "__main__":    
    main = run_wsgi_app
    main(app)
