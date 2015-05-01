import random
import os
import datetime
import logging
import time
import subprocess
import signal

import urlparse
import requests
import instagram

from celery import Celery
from celery.task.control import revoke
from redis import Redis

from scheduler import get_scheduler

from models import Session, User, Campaign, Prospect, ProspectProfile, \
ProspectComment, UserLike
from models import session as global_session
from old_insta import InstagramBot

from settings import INSTAGRAM_KEY, INSTAGRAM_SECRET, INSTAGRAM_REDIRECT

from raven import Client
from raven.contrib.celery import register_signal

redis_url = os.environ.get("REDIS_URL", "redis://ec2-works.nazo6k.0001.use1.cache.amazonaws.com:6379")
app = Celery('tasks', broker=redis_url, backend=redis_url)


SENTRY_DNS = "https://71d9ea2ad3784e1bbd276ac91097a01b:b0efbe285d4444b4a5b544b3639a1aab@app.getsentry.com/38083"
client = Client(SENTRY_DNS)
register_signal(client)

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
                client.captureException()
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
                client.captureException()
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


def kill_firefox_and_xvfb():
    p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
    out, err = p.communicate()
    for i, line in enumerate(out.splitlines()):
        if i > 0:
            if 'firefox' in line or 'xvfb' in line.lower():
                print line
                pid = int(line.split(None, 1)[0])
                os.kill(pid, signal.SIGKILL)
                print "killed"


@app.task
def update_likes(campaign_id, api):
    kill_firefox_and_xvfb()
    session = Session()
    campaign = session.query(Campaign).get(campaign_id)
    user = session.query(User).get(campaign.user.id)
    downloaded_results = downloads(session, campaign, api)
    prospect_array = []
    prospects = ProspectProfile.get_unliked_requests(session, campaign.id, 50)
    for prospect in prospects:
        prospect.done = True
        session.commit()
        prospect_array.append(prospect.prospect.username)
    ig = InstagramBot(
            username=user.username,
            password=user.password,
            prospects=prospect_array)
    result = ig.like()
    for k, v in result.iteritems():
        prospect = session.query(Prospect).filter_by(username=k).first()
	if prospect:
	    user_like = UserLike(user=user, prospect=prospect, media_id=v)
	    session.add(user_like)
	    session.commit()

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

@app.task
def launch_instance(campaign_id, username):
    conn = boto.ec2.connect_to_region('us-east-1',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

@app.task
def update_comments(campaign_id, api):
    logging.basicConfig()
    session = Session()
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
        prospect = session.query(ProspectProfile).get(prospect.id)
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

def find_media(api, prospect, comment_text):
    print "prospect:", prospect.prospect.username
    print "========"
    try:
        media, _ = api.user_recent_media(user_id=prospect.prospect.instagram_id)
        for image in media:
            print "image id", image.id
            comments = api.media_comments(image.id)
            for comment in comments:
                print comment.text
                if comment.text == comment_text:
                    return image.id
    except:
        pass
    print "none"
    return None

def add_comments(campaign_id):
    session = Session()
    campaign = session.query(Campaign).get(campaign_id)
    api = instagram.client.InstagramAPI(access_token=campaign.user.access_token)
    for prospect in campaign.prospect_profiles:
        print prospect.prospect.instagram_id
        media_id = find_media(api, prospect, campaign.comment)
        if media_id:
            prospect_comment = ProspectComment(
                    media_id=media_id,
                    prospect_profile=prospect
                    )
            session.add(prospect_comment)
            session.commit()
