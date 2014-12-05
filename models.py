import argparse
import os
import instagram
import datetime
import logging
import random
import code

from sqlalchemy import create_engine, Column, Integer, Boolean, String, \
BigInteger, ForeignKey, Date, DateTime
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL

import settings
logger = logging.getLogger('instagram')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

Base = declarative_base()

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    username = Column(String)
    access_token = Column(String)
    followers = Column(BigInteger)
    campaigns = relationship("Campaign")
    password = Column(String)

    @property
    def insta_client(self):
        return instagram.client.InstagramAPI(access_token=self.access_token)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User id={0} username={1}>'.format(
                self.id,
                self.username,
                )


class Campaign(Base):
    __tablename__ = "campaign"

    id = Column(Integer, primary_key=True)
    like_campaign = Column(Boolean, default=True)
    current = Column(Boolean, default=False)
    username = Column(String)
    instagram_id = Column(Integer)
    comment = Column(String)
    active = Column(String)
    next_items = Column(String)
    job_id = Column(String)

    user_id = Column(Integer, ForeignKey("user.id"))

    user = relationship('User', foreign_keys='Campaign.user_id')
    statistics = relationship("Statistic")


    def generate_stats(self, session, total_likes=0):
        today = datetime.date.today()
        user = campaign.user
        statistic = session.query(Statistic).filter_by(campaign=self.id, \
                date=today).first()
        if not statistic:
            statistic = Statistic(campaign=self.id,
                                    date=today,
                                    total_likes=0)
            session.add(statistic)
        statistic.total_likes += total_likes
        api = instagram.client.InstagramAPI(access_token=user.access_token)
        insta_user = api.user()
        statistic.total_followers=insta_user.__dict__.get("counts").get("followed_by"),
        session.commit()
        return True

    def __repr__(self):
        return '<Campaign id={0} user_id={1}>'.format(
                self.id,
                self.user.id
                )


class Prospect(Base):
    __tablename__ = 'prospect'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    instagram_id = Column(Integer)
    followers = Column(BigInteger, default=0)
    profiles = relationship("ProspectProfile")

    def __repr__(self):
        return '<Prospect id={0} done={1} username={2}>'.format(
                self.id,
                self.username,
                self.instagram_id
                )


class ProspectProfile(Base):
    __tablename__ = 'prospect_profile'

    id = Column(Integer, primary_key=True)
    done = Column(Boolean, default=False)
    followed_back = Column(Boolean, default=False)

    prospect_id = Column(Integer, ForeignKey("prospect.id"))
    campaign_id = Column(Integer, ForeignKey("campaign.id"))

    prospect = relationship('Prospect', foreign_keys='ProspectProfile.prospect_id')
    campaign = relationship('Campaign',
            foreign_keys='ProspectProfile.campaign_id',
            backref="prospect_profiles")
    prospect_comment = relationship("ProspectComment")

    @classmethod
    def get_unliked_requests(cls, session, campaign_id, number):
        return session.query(ProspectProfile).filter_by(\
                done=False,\
                campaign_id=campaign_id\
                ).limit(number)

    def __repr__(self):
        return '<ProspectProfile id={0} done={1} username={2}>'.format(
                self.id,
                self.done,
                self.prospect.username
                )


class ProspectComment(Base):
    __tablename__ = "prospect_comment"

    id = Column(Integer, primary_key=True)
    created = Column(Boolean, default=False)
    reply = Column(String)
    reply_date = Column(DateTime)
    media_id = Column(String)
    prospect_profile_id = Column(Integer, ForeignKey("prospect_profile.id"))
    prospect_profile = relationship('ProspectProfile',
            foreign_keys='ProspectComment.prospect_profile_id')

    def check_reply(self, session, api):
        media_id = self.media_id
        username = self.prospect_profile.campaign.user.username
        api = instagram.client.InstagramAPI(access_token=user.access_token)
        comments = api.media_comments(media_id)
        for comment in comments:
            if username in comment.text:
                self.reply=comment.text
                self.reply_date=comment.created_at
                session.commit()
                return True
        return False



    def __repr__(self):
        return '<ProspectProfile id={0} done={1} username={2}>'.format(
                self.id,
                self.d,
                self.username
                )


class Statistic(Base):
    __tablename__ = "statistic"

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    campaign = Column(Integer, ForeignKey("campaign.id"))
    total_followers = Column(BigInteger)
    total_likes = Column(Integer)
    total_comments = Column(Integer)


    @property
    def new_followers(self):
        today = datetime.datetime.today()
        yesterday = today - datetime.timedelta(days=1)

    def __repr__(self):
        return '<Statistic id={0} date={1} campaign={2}>'.format(
                self.id,
                self.date,
                self.campaign
                )


engine_url = URL(
    settings.DB_CONNECTION['drivername'],
    **settings.DB_CONNECTION['kwargs']
    )

print engine_url
engine = create_engine(engine_url)

Session = sessionmaker(bind=engine)

def create():
    Base.metadata.create_all(engine)

def shell():
    session = Session()
    code.InteractiveConsole(locals=locals()).interact()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--create', action='store_true')
    parser.add_argument('--shell',  action='store_true')

    args = parser.parse_args()

    if args.create:
        create()
    if args.shell:
        shell()
