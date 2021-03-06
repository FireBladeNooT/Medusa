# coding=utf-8

from __future__ import unicode_literals

from tornado.routes import route
from .handler import Home
from ..core import PageTemplate


@route('/IRC(/?.*)')
class HomeIRC(Home):
    def __init__(self, *args, **kwargs):
        super(HomeIRC, self).__init__(*args, **kwargs)

    def index(self):

        t = PageTemplate(rh=self, filename='IRC.mako')
        return t.render(topmenu='system', header='IRC', title='IRC', controller='IRC', action='index')
