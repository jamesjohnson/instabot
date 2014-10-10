from selenium import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



driver = webdriver.Firefox()
driver.get("https://instagram.com/accounts/login")
#Wait for spinner to disappear
WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.liSpinnerLayer")))
#Get iframe and switch to it
my_iframe = driver.find_element_by_css_selector("iframe.hiFrame")
driver.switch_to_frame(my_iframe)
element = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='username']")))
import pdb
pdb.set_trace()
password = WebDriverWait(driver,\
        10).until(EC.visibility_of_element_located((By.CSS_SELECTOR,\
            "input[name='password']")))
username.send_keys("jamesjohnsona")
password.send_keys("homie4king")
driver.implicity_wait(2)
driver.find_element_by_link_text("Log in").submit()
driver.implicity_wait(4)

"""
for (var i=0;i<media.length;i++) {
   for (var j=0;j<media[i].likes.data.length;j++) {
      console.log(media[i].likes.data[j].username)
      counter++;
   }
   for (var k=0;k<media[i].comments.data.length;k++) {
       console.log(media[i].comments.data[k].from.username)
       counter++;
   }
}
"""
