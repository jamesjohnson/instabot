import random
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


from models import Session, ScrapeRequest


class InstagramBot(object):

    def __init__(self, *args, **kwargs):
        self.driver = webdriver.Firefox()
        self.session = Session()
        self.is_logged_in = False
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")

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
        session = Session()
        if not self.is_logged_in:
            self._login()
            time.sleep(10)
        profile = ScrapeRequest.get_unliked_request(session)
        profile.liked = True
        self.driver.get("https://instagram.com/%s" % profile.url)
        #We want to randomly choose between 2-4 pictures to like in variable
        #positions
        links = self.driver.find_elements_by_xpath("//ul[@class='photo-feed']/li/div/a")
        if len(links) > 4:
            photos = random.sample(range(0,20), random.choice(range(2,5)))
            for photo in photos:
                try:
                    print photo
                    link = links[photo]
                    link.click()
                    time.sleep(2)
                    self.driver.find_element_by_xpath("//a[@class='LikeButton IconButton Button bbBaseButton']").click()
                    time.sleep(2)
                    self.driver.find_element_by_xpath("//i[@class='igDialogClose']").click()
                    time.sleep(2)
                    print "liked"
                except Exception, e:
                    print e
        session.commit()
        return True

ig = InstagramBot(username='sarahjrose', password='boykin')
for i in range(0,100):
    ig.like()
    time.sleep(random.choice(range(5, 20)))

