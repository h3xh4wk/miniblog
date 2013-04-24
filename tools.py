MAX_POSTS_PER_PAGE = 15


# add custom libs to path (e.g. import lib.my_lib)
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))


# TODO: potentially shorten stopwords file (left as found from internet)
import os
def get_title_path(word_string, character_limit=30, stopwords='stopwords.txt'):

    # get stopwords, remove from wordlist, and only allow alphanumeric characters
    stopwords_path = os.path.join('static', stopwords)
    stopwords = set(word.strip() for word in open(stopwords_path))

    word_list = word_string.lower().split()
    word_list = filter(lambda word: not word in stopwords, word_list)
    
    word_list = map(lambda word: ''.join(l for l in word if l.isalnum()), word_list)
    
    # hyphen join & character limit title path
    title = '-'.join(word_list)
    title = title[:character_limit].rstrip('-')
    
    return title


import datetime
from lib.dateutil import relativedelta
def elapsed_human_time(dt1, dt2):
    
    # check - must be datetime    
    if not isinstance(dt1, datetime.datetime) or \
       not isinstance(dt2, datetime.datetime):
        raise TypeError
    
    if dt1 > dt2:
        time_rel = relativedelta.relativedelta(dt1, dt2)
    else:
        time_rel = relativedelta.relativedelta(dt2, dt1)
    
    # go through time
    time_machine = "just now"
    time_units = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']                   
    for idx, unit in enumerate(time_units):
        unit_val = getattr(time_rel, unit)
        
        # good enough
        if unit_val > 1:
            time_machine = "%i %s ago" % (unit_val, unit)
            
            break
            
        # need more info - special cases    
        elif unit_val == 1 and unit != 'seconds':
            next_unit = time_units[idx+1]
            next_unit_val = getattr(time_rel, next_unit)
            
            # basically just checking plural time_units (e.g. second(s))
            if next_unit_val > 1:
                time_machine = "%i %s, %i %s ago" % (unit_val, unit[:-1],
                                                    next_unit_val, next_unit)
            elif next_unit_val == 1:
                time_machine = "%i %s, %i %s ago" % (unit_val, unit[:-1],
                                                    next_unit_val, next_unit[:-1])
            else:
                time_machine = "%i %s ago" % (unit_val, unit[:-1])
                
            break

    return time_machine


import logging
from google.appengine.api import search    
def user_query(query, limit=1000):

    # put together the search query    
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
        limit=limit)

    options = search.QueryOptions(
        limit=limit,
        sort_options=sort)

    # do the query and get the blog posts
    try:
        query = search.Query(query_string=query, options=options)
        index = search.Index(name='post-search')
        results = index.search(query)
        
    except (TypeError, ValueError):
        logging.error('Document search QUERY failed')
     
    post_keys = [result.doc_id for result in results.results]
       
    return post_keys
