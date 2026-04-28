import sys, time
sys.path.insert(0,'.')
import gplinks_live_browser as glb
print('start')
d=glb.build_driver()
print('built', d.session_id)
d.get('about:blank')
print('title', d.title)
d.quit()
print('ok')
