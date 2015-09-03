#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.handlers.imaging import ContextHandler
from thumbor.handlers.imaging import ImagingHandler
from thumbor.context import RequestParameters
from thumbor.utils import logger
import thumbor.filters
import tornado.gen as gen
import tornado.web
import re


class BuzzFeedHandler(ImagingHandler):
    @classmethod
    def regex(cls):
        ''' 
        URLs matching this regex will be handled with this handler.
        The ?P<image> is an identifier that will be used as a key
        when the matching group[s] are passed to the handler.
        
        For example, the regex matches the word /static/ and 
        everything that follows it (basically the URI of the image),
        and that URI will be passed as {image:<uri>} to the get handler.
        At least I think that's what's going on... really it's just 
        a crapshoot.
        '''
        return r'(?P<image>/static/.*)'

    @tornado.web.asynchronous
    def get(self, **kw):
        '''
        Handler for GET requests. kw is a hash of matches from the regex.
        Pretty much all it has is the URI of the image.
        '''
        # It's the dev environment; keep it simple by supporting any image
        # Prepend the buzzfeed dev environment domain to the URI to get
        # the image URI (apache takes care of redirecting 404s to prod)
        # And default the quality setting
        kw['unsafe'] = u'unsafe' 
        kw['image'] = self.context.config.BUZZFEED_DOMAIN + kw['image']
        kw['quality'] = self.context.config.QUALITY

        # Set/override values based on URL params
        if self.request.query_arguments.has_key( 'output-quality' ):
            self.__handle_output_quality__( kw )
        if self.request.query_arguments.has_key( 'crop' ):
            self.__handle_crop__( kw )
        if self.request.query_arguments.has_key( 'resize' ):
            self.__handle_resize__( kw )

        # Proceed with the magic that thumbor does so well
        self.check_image( kw )

    def __handle_output_quality__( self, kw ):
        # Akamai param value is simply an int, which is what thumbor wants
        kw['quality'] = int(self.request.query_arguments['output-quality'][0])

    def __handle_resize__( self, kw ):
        # Akamai param is w:h; px can be appended to either value (has no effect).
        # If * is passed for either value, original aspect ratio is used.
        # Not supported: 
        #     Multiplying dimensions (2xw:2xh to double x and y);
        #     Fractional dimensions (1/3x:* to reduce width by a third);
        #     Original width or height (100:h)
        [w,h] = re.split( r':', self.request.query_arguments['resize'][0] )
        kw['width'] = w.replace('px','')
        kw['height'] = h.replace('px','')
        if kw['width'] == '*':
            del(kw['width'])
        if kw['height'] == '*':
            del(kw['height'])

    def __handle_crop__( self, kw ):
        # Akamai param is: w:h;x,y
        #
        # tornado uses ; as query param separator, so must use URI here
        # instead of query params.

        # Pull out the substring of URI that holds the crop value
        uri = self.request.uri
        startAt = uri.find( 'crop=' ) + 5
        endAt = uri.find( '&', startAt )
        if endAt == -1:
            endAt = len( uri )    
        crop_part_of_uri = uri[ startAt : endAt ]

        # Split it and assign parts
        [w,h,x,y] = re.split( r'[:|;|,]', crop_part_of_uri )
        kw['crop_left'] = x
        kw['crop_top'] = y
        kw['crop_right'] = int(x) + int(w)
        kw['crop_bottom'] = int(y) + int(h)

    @gen.coroutine
    def execute_image_operations (self):
        '''
        Behavior defined in base handler is to always set quality to None, 
        regardless of whether it was specified on the URL. 
        With the exception of that one deleted line, this is the same as 
        what's in the base handler.
        '''
        req = self.context.request
        conf = self.context.config

        should_store = self.context.config.RESULT_STORAGE_STORES_UNSAFE or not self.context.request.unsafe
        if self.context.modules.result_storage and should_store:
            start = datetime.datetime.now()
            result = self.context.modules.result_storage.get()
            finish = datetime.datetime.now()
            self.context.metrics.timing('result_storage.incoming_time', (finish - start).total_seconds() * 1000)
            if result is None:
                self.context.metrics.incr('result_storage.miss')
            else:
                self.context.metrics.incr('result_storage.hit')
                self.context.metrics.incr('result_storage.bytes_read', len(result))

            if result is not None:
                mime = BaseEngine.get_mimetype(result)
                if mime == 'image/gif' and self.context.config.USE_GIFSICLE_ENGINE:
                    self.context.request.engine = self.context.modules.gif_engine
                    self.context.request.engine.load(result, '.gif')
                else:
                    self.context.request.engine = self.context.modules.engine

                logger.debug('[RESULT_STORAGE] IMAGE FOUND: %s' % req.url)
                self.finish_request(self.context, result)
                return

        if conf.MAX_WIDTH and (not isinstance(req.width, basestring)) and req.width > conf.MAX_WIDTH:
            req.width = conf.MAX_WIDTH
        if conf.MAX_HEIGHT and (not isinstance(req.height, basestring)) and req.height > conf.MAX_HEIGHT:
            req.height = conf.MAX_HEIGHT

        req.meta_callback = conf.META_CALLBACK_NAME or self.request.arguments.get('callback', [None])[0]

        self.filters_runner = self.context.filters_factory.create_instances(self.context, self.context.request.filters)
        self.filters_runner.apply_filters(thumbor.filters.PHASE_PRE_LOAD, self.get_image)

