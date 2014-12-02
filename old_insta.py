import random
import argparse
import datetime
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


from models import Session, Prospect

session = Session()

class InstagramBot(object):

    def __init__(self, *args, **kwargs):
        self.driver = webdriver.Firefox()
        self.session = Session()
        self.is_logged_in = False
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")
        self.prospects = kwargs.get("prospects", [])
        self.completed = 0
        self.failed = 0
        self.prospects_completed = 0
        self.start_time = None

    def _login(self):
        self.driver.get("https://instagram.com/accounts/login")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.liSpinnerLayer")))
        my_iframe = self.driver.find_element_by_css_selector("iframe.hiFrame")
        self.driver.switch_to_frame(my_iframe)
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

    def like(self):
        self.start_time = time.time()
        if not self.is_logged_in:
            self._login()
            time.sleep(10)
        for prospect in self.prospects:
            prospect.done = True
            session.commit()
            self.driver.get("https://instagram.com/")
            time.sleep(2)
            self.driver.get("https://instagram.com/%s" % prospect.username)
            #We want to randomly choose between 2-4 pictures to like in variable
            #positions
            links = self.driver.find_elements_by_xpath("//ul[@class='photo-feed']/li/div/a")
            if len(links) > 1:
                try:
                    link = links[0]
                    link.click()
                    time.sleep(5)
                    element_to_like = self.driver.find_element_by_xpath("//a[@class='LikeButton IconButton Button bbBaseButton']")
                    element_to_like.click()
                    time.sleep(2)
                    if "ButtonActive" in element_to_like.get_attribute("class"):
                        self.driver.find_element_by_xpath("//i[@class='igDialogClose']").click()
                        self.completed += 1
                        time.sleep(15)
                    else:
                        self.failed += 1
                        print "like failed"
                        time.sleep(60)
                    current_time = datetime.timedelta(seconds=time.time() - \
                            self.start_time)
                    print "Time Elapsed: {0} {1}: liked {2}: failed\n".format(\
                                current_time,
                                self.completed,\
                                self.failed)
                except Exception, e:
                    self.failed += 1
                    print e
        self.driver.quit()
        return True


def run(username, password):
    campaign = session.query(Campaign).first()
    prospects = Prospect.get_unliked_requests(session, campaign_id, 100)
    ig = InstagramBot(
            username=username,
            password=password,
            prospects=prospects)
    ig.like()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("password")
    args = parser.parse_args()
    run(args.username, args.password)

