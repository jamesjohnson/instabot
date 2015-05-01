import random
import argparse
import datetime
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from pyvirtualdisplay import Display
from raven import Client


from models import Session, Prospect, ProspectProfile, UserLike

SENTRY_DNS = "https://71d9ea2ad3784e1bbd276ac91097a01b:b0efbe285d4444b4a5b544b3639a1aab@app.getsentry.com/38083"
client = Client(SENTRY_DNS)

session = Session()

class InstagramBot(object):

    def __init__(self, *args, **kwargs):
        self.display = Display(visible=0, size=(1024, 768))
        self.display.start()
        time.sleep(2)
        self.driver = webdriver.Firefox()
        self.is_logged_in = False
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")
        self.prospects = kwargs.get("prospects", [])
        self.completed = 0
        self.failed = 0
        self.prospects_completed = 0
        self.start_time = None
        self.successful_prospects = []

    def _login(self):
        self.driver.get("https://instagram.com/accounts/login")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.liSpinnerLayer")))
        username = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='username']")))
        password = WebDriverWait(self.driver,\
                10).until(EC.visibility_of_element_located((By.CSS_SELECTOR,\
                    "input[name='password']")))
        username.send_keys(self.username)
        password.send_keys(self.password)
        self.driver.find_elements_by_class_name("lfSubmit")[0].click()
        self.driver.implicitly_wait(5)
        self.is_logged_in = True
        return True

    def _find_links(self, username):
        self.driver.get("https://instagram.com/")
        time.sleep(2)
        self.driver.get("https://instagram.com/%s" % username)
        time.sleep(2)
        return self.driver.find_elements_by_xpath("//a[@class='pgmiImageLink']")

    def _print_time(self):
        current_time = datetime.timedelta(seconds=time.time() - \
                self.start_time)
        print "Time Elapsed: {0} {1}: liked {2}: failed\n".format(\
                    current_time,
                    self.completed,\
                    self.failed)

    def _get_media_id(self):
        user_media = self.driver.execute_script("return window._sharedData")
        return user_media.get('entry_data').get('UserProfile')[0]\
                .get('userMedia')[0].get('id')

    def like(self):
        liked_media = {}
        self.start_time = time.time()
        if not self.is_logged_in:
            self._login()
            time.sleep(10)
        for prospect in self.prospects:
	    print prospect
            try:
                links = self._find_links(prospect)
                if len(links) > 1:
                    link = links[0]
                    link.click()
                    time.sleep(5)
                    element_to_like = self.driver.find_element_by_xpath("//a[contains(@class, 'LikeButton')]")
                    element_to_like.click()
                    time.sleep(6)
                    if "ButtonActive" in element_to_like.get_attribute("class"):
                        self.driver.find_element_by_xpath("//i[@class='igDialogClose']").click()
                        self.completed += 1
                        try:
                            media_id =self._get_media_id()
                        except:
                            media_id = None
                        print media_id
                        liked_media[prospect] = media_id
                        time.sleep(22)
                    else:
                        self.failed += 1
                        print "like failed"
                        time.sleep(60)
                    self._print_time()
            except Exception, e:
                self.failed += 1
                client.captureException()
                print e, prospect, prospect_id
        self.driver.quit()
        self.display.popen.kill()
        return liked_media

    def comment(self, text):
        self.start_time = time.time()
        if not self.is_logged_in:
            self._login()
            time.sleep(10)
        for prospect_id in self.prospects:
            prospect = session.query(ProspectProfile).get(prospect_id)
            prospect.done = True
            session.commit()
            links = self._find_links(prospect.prospect.username)
            if len(links) > 1:
                try:
                    link = links[0]
                    link.click()
                    time.sleep(5)
                    element_to_comment = self.driver.find_element_by_xpath("//input[@class='fbInput']")
                    element_to_comment.send_keys(text)
                    element_to_comment.send_keys(Keys.RETURN)
                    self._print_time()
                    self.completed += 1
                    self.successful_prospects.append(prospect)
                    time.sleep(15)
                except Exception, e:
                    self.failed += 1
                    client.captureException()
                    print e
        self.driver.quit()
        self.display.popen.kill()
        print self.successful_prospects, "old_insta 142"
        return self.successful_prospects

def run(username, password, prospects):
    ig = InstagramBot(
            username=username,
            password=password,
            prospects=prospects.split(","))
    ig.like()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("prospects")
    args = parser.parse_args()
    run(args.username, args.password, args.prospects)

