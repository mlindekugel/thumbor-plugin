# thumbor-plugin
pip install thumbor
cp ~/work/thumbor/thumbor/config.py /usr/local/lib/python2.7/site-packages/thumbor/config.py
cp ~/work/thumbor/thumbor/buzzfeed_app.py /usr/local/lib/python2.7/site-packages/thumbor/
cp ~/work/thumbor/thumbor/handlers/buzzfeed.py /usr/local/lib/python2.7/site-packages/thumbor/handlers/
thumbor --app=thumbor.buzzfeed_app.BuzzFeedApp
