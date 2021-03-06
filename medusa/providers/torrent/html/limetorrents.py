# coding=utf-8
# Author: Gonçalo M. (aka duramato/supergonkas) <supergonkas@gmail.com>
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re
import traceback

from contextlib2 import suppress
import requests
from requests.compat import urljoin
from ..TorrentProvider import TorrentProvider
from .... import logger, tvcache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size, try_int

id_regex = re.compile(r'(?:\/)(.*)(?:-torrent-([0-9]*)\.html)', re.I)
hash_regex = re.compile(r'(.*)([0-9a-f]{40})(.*)', re.I)


class LimeTorrentsProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """LimeTorrents Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'LimeTorrents')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://www.limetorrents.cc/'
        self.urls = {
            'index': self.url,
            'update': urljoin(self.url, '/post/updatestats.php'),
            'search': urljoin(self.url, '/search/tv/{query}/'),
            'rss': urljoin(self.url, '/browse-torrents/TV-shows/date/{page}/')
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Miscellaneous Options
        self.confirmed = False

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, min_time=10)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        Search a provider and parse the results

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    if self.confirmed:
                        logger.log('Searching only confirmed torrents', logger.DEBUG)

                    search_url = self.urls['search'].format(query=search_string)
                else:
                    search_url = self.urls['rss'].format(page=1)

                response = self.get_url(search_url, returns='response')
                if not response or not response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                results += self.parse(response.text, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html('table', class_='table2')

            if mode != 'RSS' and torrent_table and len(torrent_table) < 2:
                logger.log('Data returned from provider does not contain any {0}torrents'.format(
                           'confirmed ' if self.confirmed else ''), logger.DEBUG)
                return items

            torrent_table = torrent_table[0 if mode == 'RSS' else 1]
            torrent_rows = torrent_table('tr')

            # Skip the first row, since it isn't a valid result
            for row in torrent_rows[1:]:
                cells = row('td')
                try:
                    verified = row('img', title='Verified torrent')
                    if self.confirmed and not verified:
                        continue

                    url = row.find('a', rel='nofollow')
                    title_info = row('a')
                    info = title_info[1]['href']
                    if not all([url, title_info, info]):
                        continue

                    title = title_info[1].get_text(strip=True)
                    title2 = id_regex.search(info).group(1)
                    if len(title) < len(title2):
                        title = title2.replace('-', ' ')
                    torrent_id = id_regex.search(info).group(2)
                    torrent_hash = hash_regex.search(url['href']).group(2)
                    if not all([title, torrent_id, torrent_hash]):
                        continue

                    with suppress(requests.exceptions.Timeout):
                        # Suppress the timeout since we are not interested in actually getting the results
                        self.session.get(self.urls['update'], timeout=0.1,
                                         params={'torrent_id': torrent_id,
                                                 'infohash': torrent_hash})

                    # Remove comma as thousands separator from larger number like 2,000 seeders = 2000
                    seeders = try_int(cells[3].get_text(strip=True).replace(',', ''))
                    leechers = try_int(cells[4].get_text(strip=True).replace(',', ''))
                    size = convert_size(cells[2].get_text(strip=True)) or -1
                    download_url = 'magnet:?xt=urn:btih:{hash}&dn={title}{trackers}'.format(
                        hash=torrent_hash, title=title, trackers=self._custom_trackers)

                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': None,
                        'torrent_hash': torrent_hash,
                    }
                    if mode != 'RSS':
                        logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                   (title, seeders, leechers), logger.DEBUG)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    logger.log('Failed parsing provider. Traceback: {0!r}'.format
                               (traceback.format_exc()), logger.ERROR)

        return items


provider = LimeTorrentsProvider()
