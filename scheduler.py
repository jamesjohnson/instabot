from redis import Redis
import urlparse

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore

redis_url = "redis://localhost:6379"

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
    sched = BackgroundScheduler(jobstores=jobstores)
    if not sched.running:
        sched.start()
    return sched


