from selenium import webdriver

from rq.decorators import job

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from models import ScrapeRequest, Session
import logging

from rq import Queue
from redis import Redis
from settings import REDIS

redis_conn = Redis(**REDIS)
queue = Queue(connection=redis_conn)
driver = webdriver.Firefox()

javascript = """
            var usernames = []
            var media = window._sharedData.entry_data.UserProfile[0].userMedia
            for (var i=0;i<media.length;i++) {
               for (var j=0;j<media[i].likes.data.length;j++) {
                  usernames.push(media[i].likes.data[j].username)
               }
               for (var k=0;k<media[i].comments.data.length;k++) {
                   usernames.push(media[i].comments.data[k].from.username)
               }
            }
            return usernames
            """


def crawl(profile='merrittbeck'):
    driver.get("https://instagram.com/%s" % profile)
    driver.implicitly_wait(10)
    results = driver.execute_script(javascript)
    return list(set(results))


def process_next_request(request_id=None):
    session = Session()

    if request_id is None:
        request = ScrapeRequest.get_unfinished_request(session)
    else:
        request = session.query(ScrapeRequest).get(request_id)

    if request:
        logging.debug('Processing request {}'.format(request))

        linked_profiles = crawl(request.url)
        request.done = True
        print linked_profiles

        for link in linked_profiles:
            add_url(link, session, commit=False, add_task=True)
    else:
        linked_profiles = crawl()
        for link in linked_profiles:
            add_url(link, session, commit=False, add_task=True)
        logging.debug('There are currently no unfinished requests')

    session.commit()


def add_url(url, session=None, commit=True, add_task=True):
    if session is None:
        session = Session()

    if not session.query(ScrapeRequest).filter(ScrapeRequest.url==url).count():
        logging.debug('Adding scrape request for {} to the queue'.format(url))
        new_request =  ScrapeRequest(
                url = url
                )
        session.add(new_request)
        session.commit()
        print new_request

        if add_task:
            process_next_request_task.delay(new_request.id)

    else:
        logging.debug('Skipping adding {} to the queue, already exists'.format(url))

    session.commit()


def process_forever():
    i = 0
    while True:
        process_next_request()
        logging.debug('Processed request #{}'.format(i))
        i+=1


@job('instagram', connection = redis_conn)
def process_next_request_task(request_id):
    process_next_request(request_id)

if __name__ == '__main__':
    process_forever()
