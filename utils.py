import random
import datetime
import logging
import time

import urlparse
import requests
import instagram

from redis import Redis
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore

from models import Session, User, Campaign, Prospect, ProspectProfile
from old_insta import InstagramBot

from settings import INSTAGRAM_KEY, INSTAGRAM_SECRET, INSTAGRAM_REDIRECT

session = Session()
redis_url = "redis://localhost:6379"
logger = logging.getLogger('instagram')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

def get_scheduler():
    urlparse.uses_netloc.append('redis')
    redis_url_parsed = urlparse.urlparse(redis_url)
    jobstores = {
            'default': RedisJobStore(
                            host=redis_url_parsed.hostname,
                            port=redis_url_parsed.port,
                            db=0,
                            password=redis_url_parsed.password
                        )
            }
    return BackgroundScheduler(jobstores=jobstores)

def create_user(user, campaign):
    try:
        prospect = session.query(Prospect).filter_by(\
                username=user.username).first()
        if not prospect:
            prospect = Prospect(
                    username=user.username,
                    instagram_id=user.id,
                    )
            session.add(prospect)
        prospect_profile = ProspectProfile(
                campaign=campaign.id,
                prospect=prospect.id,
                done=False,
                followed_back=False)
        session.add(prospect)
        session.commit()
    except Exception, e:
        print (e, "111")

def downloads(campaign, api):
    created_user_count = 0
    counter = 0
    if not campaign.next_items:
        print "not next items"
        users, next_items = api.user_followed_by(campaign.instagram_id)
        for user in users:
            try:
                relationship = api.user_relationship(user.id)
                if not (relationship.target_user_is_private or \
                        "followed_by" in relationship.incoming_status or \
                        "follows" in relationship.outgoing_status):
                    #media, next = api.user_recent_media(user.id)
                    create_user(user, campaign)
                    created_user_count += 1
            except Exception, e:
                print (e, "121")
    else:
        next_items=campaign.next_items

    while next_items and counter < 10:
        counter += 1
        users, next_items = api.user_followed_by(with_next_url=next_items)
        for user in users:
            try:
                relationship = api.user_relationship(user.id)
                if not (relationship.target_user_is_private or \
                        "followed_by" in relationship.incoming_status or \
                        "follows" in relationship.outgoing_status):
                    #media, next = api.user_recent_media(user.id)
                    create_user(user, campaign)
                    created_user_count += 1
            except Exception, e:
                print (e, "131")
    campaign.next_items = next_items
    session.commit()
    print "{0} users created".format(created_user_count)
    return True

def update_likes(campaign, api):
    user = session.query(User).filter_by(id=campaign.user).first()
    downloaded_results = downloads(campaign, api)
    prospects = Prospect.get_unliked_requests(session, campaign.id, 65)
    ig = InstagramBot(
            username=user.username,
            password=user.password,
            prospects=prospects)
    result = ig.like()
    campaign.generate_stats(session, total_likes=ig.completed)
    return True

def pause_job(job_id):
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)
    new_time = job.next_run_time + datetime.timedelta(hours=1)
    job._modify(next_run_time=new_time)
    return True

def start_like_scheduler(campaign, api):
    logging.basicConfig()
    scheduler = get_scheduler()
    job = scheduler.add_job(update_likes, 'cron', minute=51, args=(campaign,api,))
    #scheduler.add_job(pause_job, 'cron', minute=4, hour="4,8,12,16", args=(job.id,))
    scheduler.start()
    campaign.job_id=job.id
    session.commit()
    return scheduler

def update_and_download(campaign_id):
    campaign = session.query(Campaign).filter_by(id=campaign_id).first()
    user = session.query(User).filter_by(id=campaign.user).first()
    access_token = user.access_token
    api = instagram.client.InstagramAPI(access_token=access_token)#,
                                        #client_ips="72.69.141.254",
                                        #client_secret=INSTAGRAM_SECRET)
    return start_like_scheduler(campaign, api)

