import datetime
import logging

from flask import Flask
from flask import render_template
from flask import request
from flask import redirect, url_for
from flask.ext.login import login_user, LoginManager, logout_user, current_user, fresh_login_required
from werkzeug.debug import DebuggedApplication

from models import Session, User, Campaign, Prospect, ProspectProfile,\
ProspectComment
from utils import update_and_download, get_scheduler, update_comments
from settings import INSTAGRAM_KEY, INSTAGRAM_SECRET, INSTAGRAM_REDIRECT

import instagram
app = Flask(__name__)
app.secret_key = 'why would I tell you my secret key?'
app.debug = True
login_manager = LoginManager()
login_manager.init_app(app)
session = Session()


@login_manager.user_loader
def load_user(userid):
    return session.query(User).get(userid)

@app.route("/logout")
def logout_view():
    logout_user()
    return redirect(url_for("instagram_start"))

@app.route("/")
def instagram_start():
    if current_user.is_authenticated():
        return redirect(url_for("home"))
    CONFIG = {
        'client_id': INSTAGRAM_KEY,
        'client_secret': INSTAGRAM_SECRET,
        'redirect_uri': INSTAGRAM_REDIRECT
    }
    unauthenticated_api = instagram.client.InstagramAPI(**CONFIG)
    link = unauthenticated_api.get_authorize_url(scope=["likes","comments","relationships"])
    return render_template('instagram.html', link=link)

@app.route("/instagram/oauth")
def instagram_oauth():
    provided_ips = request.headers.getlist("X-Forwarded-For")
    if len(provided_ips) > 0:
        ip = provided_ips[0]
    else:
        ip = "72.69.141.254"
    code = request.args.get("code")
    if not code:
        return 'Missing code'
    try:
        CONFIG = {
            'client_id': INSTAGRAM_KEY,
            'client_secret': INSTAGRAM_SECRET,
            'redirect_uri': INSTAGRAM_REDIRECT
        }
        unauthenticated_api = instagram.client.InstagramAPI(**CONFIG)
        access_token, user_info = unauthenticated_api.exchange_code_for_access_token(code)
        if not access_token:
            return 'Could not get access token'
        api = instagram.client.InstagramAPI(access_token=access_token)#,
                                            #client_ips=ip,
                                            #client_secret=INSTAGRAM_SECRET)

        user = api.user()
        print access_token
        if session.query(User).filter_by(username=user.username).first():
            new_user = session.query(User).filter_by(username=user.username).first()
            new_user.access_token=access_token
        else:
            new_user = User(
                    username=user.username,
                    followers=user.__dict__.get("counts").get("followed_by"),
                    access_token=access_token,
                    )
            session.add(new_user)
        session.commit()
        login_user(new_user)
        return redirect(url_for("home"))
    except Exception, e:
        print e
        return redirect(url_for("instagram_start"))

@app.route("/home", methods=['GET', 'POST'])
def home():
    if request.method == "POST":
        username = request.form.get("username")
        api = instagram.client.InstagramAPI(access_token=current_user.access_token)#,
                                            #client_ips="127.0.0.1",
                                            #client_secret=INSTAGRAM_SECRET)
        user = api.user_search(q=username)[0]
        campaign = Campaign(current=False,
                        username=user.username,
                        instagram_id=user.id,
                        like_campaign=True,
                        user=current_user)
        session.add(campaign)
        session.commit()
        campaigns = session.query(Campaign).filter_by(user=current_user, \
                like_campaign=True)
    else:
        campaigns = session.query(Campaign).filter_by(user=current_user, \
                like_campaign=True)

    return render_template("home.html", campaigns=campaigns)

@app.route("/comments", methods=['GET', 'POST'])
def comments():
    if request.method == "POST":
        usernames = [u.strip() for u in
                request.form.get("usernames").split(",")]
        comment = request.form.get("comment")
        api = instagram.client.InstagramAPI(access_token=current_user.access_token)#,
                                            #client_ips="127.0.0.1",
                                            #client_secret=INSTAGRAM_SECRET)
        campaign = Campaign(current=False,
                        like_campaign=False,
                        comment=comment,
                        user=current_user)
        session.add(campaign)
        session.commit()
        for username in usernames:
            user = api.user_search(q=username)[0]
            prospect = session.query(Prospect).filter_by(\
                    username=user.username).first()
            if not prospect:
                prospect = Prospect(
                        username=user.username,
                        instagram_id=user.id,
                        )
                session.add(prospect)
            prospect_profile = ProspectProfile(
                    campaign=campaign,
                    prospect=prospect,
                    done=False,
                    followed_back=False)
            session.add(prospect_profile)
            session.commit()
        soon = datetime.datetime.now() + datetime.timedelta(minutes=1)
        logging.basicConfig()
        scheduler = get_scheduler()
        job = scheduler.add_job(update_comments, 'date', run_date=soon, \
                args=(campaign.id,api,))
        scheduler.start()
        campaign.job_id=job.id
        session.commit()
        campaigns = session.query(Campaign).filter_by(user=current_user, \
                like_campaign=False)
    else:
        campaigns = session.query(Campaign).filter_by(user=current_user, \
                like_campaign=False)

    return render_template("comments.html", campaigns=campaigns)

@app.route("/password", methods=['POST'])
def password():
    if request.method == "POST":
        password = request.form.get("password")
        current_user.password = password
        session.commit()
    return redirect(url_for("home"))

@app.route("/campaign/<int:campaign_id>")
def campaign(campaign_id):
    campaign = session.query(Campaign).get(campaign_id)
    scheduler = get_scheduler()
    job = scheduler.get_job(campaign.job_id)
    if campaign.comment:
        template = "comments/campaign.html"
    else:
        template = "campaign.html"
    return render_template(template, campaign=campaign, job=job)

@app.route("/update/<int:campaign_id>")
def turn_on(campaign_id):
    print "updated"
    campaign = session.query(Campaign).get(campaign_id)
    update_and_download(campaign.id)
    return redirect(url_for("campaign", campaign_id=campaign.id))


if __name__ == "__main__":
    app.debug = True
    app.run()
