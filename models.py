import argparse
import instagram
import datetime
import logging
import random
import code

from sqlalchemy import create_engine, Column, Integer, Boolean, String, \
BigInteger, ForeignKey, Date
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
    user = Column(Integer, ForeignKey("user.id"))
    next_items = Column(String)
    job_id = Column(String)
    statistics = relationship("Statistic")


    def generate_stats(self, session, total_likes=0):
        today = datetime.date.today()
        user = session.query(User).filter_by(id=self.user).first()
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
                self.user
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
    prospect = Column(Integer, ForeignKey("prospect.id"))
    done = Column(Boolean, default=False)
    followed_back = Column(Boolean, default=False)
    campaign = Column(Integer, ForeignKey("campaign.id"))

    def like_photos(self, session, api, number):
        if self.media_ids:
            media_ids = self.media_ids.replace("{", "").replace("}", "").split(",")
            photos = [random.choice(media_ids) for i in range(number)]
            for photo in photos:
                try:
                    api.like_media(photo)
                    logger.debug('Liked Image: {} for user {}'.format(id,\
                        self.username))
                except Exception, e:
                    print (e)
            self.done = True
            session.add(self)
            session.commit()
        return []

    @classmethod
    def get_unliked_requests(cls, session, campaign_id, number):
        return session.query(ProspectProfile).filter_by(\
                done=False,\
                campaign=campaign_id
                ).limit(number)

    def __repr__(self):
        return '<ProspectProfile id={0} done={1} username={2}>'.format(
                self.id,
                self.done,
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
