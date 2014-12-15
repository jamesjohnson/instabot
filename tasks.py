import random
import os
import datetime
import logging
import time

import urlparse
import requests
import instagram

from celery import Celery
from celery.task.control import revoke
from redis import Redis

from scheduler import get_scheduler

from models import Session, User, Campaign, Prospect, ProspectProfile, \
ProspectComment
from models import session as global_session
from old_insta import InstagramBot

from settings import INSTAGRAM_KEY, INSTAGRAM_SECRET, INSTAGRAM_REDIRECT


redis_url = os.environ.get("REDIS_URL", "redis://ec2-works.nazo6k.0001.use1.cache.amazonaws.com:6379")
app = Celery('tasks', broker=redis_url, backend=redis_url)

logger = logging.getLogger('instagram')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


def create_user(session, user, campaign):
    try:
        prospect = session.query(Prospect).filter_by(\
                username=user.username).first()
        if not prospect:
            prospect = Prospect(
                    username=user.username,
                    instagram_id=user.id,
                    )
            session.add(prospect)
            session.flush()
        prospect_profile = ProspectProfile(
                campaign_id=campaign.id,
                prospect_id=prospect.id,
                done=False,
                followed_back=False)
        session.add(prospect_profile)
        session.commit()
    except Exception, e:
        session.rollback()
        print (e, "111")

def downloads(session, campaign, api):
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
                    create_user(session, user, campaign)
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
                    create_user(session, user, campaign)
                    created_user_count += 1
            except Exception, e:
                print (e, "131")
    campaign.next_items = next_items
    session.commit()
    if session.query(Campaign).get(campaign.id).next_items != next_items:
        print "FAIL: next items still causing issues"
    print "{0} users created".format(created_user_count)
    return True

def update_likes_q(campaign_id, api):
    print "once"
    update_likes.delay(campaign_id, api)
    return True


@app.task
def update_likes(campaign_id, api):
    session = Session()
    campaign = session.query(Campaign).get(campaign_id)
    user = session.query(User).get(campaign.user.id)
    downloaded_results = downloads(session, campaign, api)
    prospects = (prospect.id for prospect \
            in ProspectProfile.get_unliked_requests(session, campaign.id, 50))
    ig = InstagramBot(
            username=user.username,
            password=user.password,
            prospects=prospects)
    result = ig.like()
    campaign.generate_stats(session, total_likes=ig.completed)
    campaign = session.query(Campaign).get(campaign_id)
    if campaign.job_id:
        result = update_likes.apply_async(countdown=1000, args=(campaign.id, api,))
        print "old", campaign.job_id
        campaign.job_id=result.id
        session.commit()
        print "new", campaign.job_id
    else:
        print "no longer doing this"
    return True

def update_comments(campaign_id, api):
    logging.basicConfig()
    campaign = session.query(Campaign).get(campaign_id)
    user = session.query(User).get(campaign.user.id)
    prospects = (prospect.id for prospect in \
            session.query(ProspectProfile).filter_by(campaign=campaign))
    ig = InstagramBot(
            username=user.username,
            password=user.password,
            prospects=prospects)
    results = ig.comment(text=campaign.comment)
    print results, "utils 125"
    for prospect in results:
        media = user.insta_client.user_recent_media()[0][0]
        prospect_comment=ProspectComment(
                prospect_profile=prospect,
                created=True,
                media_id=media.id
                )
        session.add(prospect_comment)
        session.commit()
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
    print "added"
    start = datetime.datetime.today().minute + 1
    job = scheduler.add_job(update_likes_q, 'cron', minute=start, \
            misfire_grace_time=None, args=(campaign.id,api,))
    #scheduler.add_job(pause_job, 'cron', minute=4, hour="4,8,12,16", args=(job.id,))
    campaign.job_id=job.id
    print "Job ID: {}".format(job.id)
    global_session.commit()
    return scheduler

def update_and_download(campaign_id):
    campaign = global_session.query(Campaign).get(campaign_id)
    print "update and download"
    api = instagram.client.InstagramAPI(access_token=campaign.user.access_token)#,
                                        #client_ips="72.69.141.254",
                                        #client_secret=INSTAGRAM_SECRET)
    return start_like_scheduler(campaign, api)

