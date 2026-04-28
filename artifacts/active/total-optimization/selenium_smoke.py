from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
opts=Options(); opts.binary_location='/usr/bin/google-chrome'
for a in ['--no-sandbox','--disable-dev-shm-usage','--window-size=800,600','--no-first-run','--no-default-browser-check']:
 opts.add_argument(a)
d=webdriver.Chrome(service=Service('/root/.local/share/undetected_chromedriver/undetected_chromedriver'), options=opts)
print('session', d.session_id)
d.get('about:blank')
print('ok', d.title)
d.quit()
