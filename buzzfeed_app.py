#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com
import tornado.web
import tornado.ioloop

from thumbor.app import ThumborServiceApp
from thumbor.handlers.buzzfeed import BuzzFeedHandler
from thumbor.handlers.imaging import ImagingHandler
from thumbor.url import Url

class BuzzFeedApp(ThumborServiceApp):

    def __init__(self, context):
        self.context = context
        super(ThumborServiceApp, self).__init__(self.get_handlers())

    def get_handlers(self):
        # Imaging handler (GET)
        return [
            (BuzzFeedHandler.regex(), BuzzFeedHandler, {'context':self.context} ),
            (Url.regex(), ImagingHandler, {'context': self.context})
        ]
