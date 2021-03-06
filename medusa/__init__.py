# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
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
# pylint: disable=too-many-lines

import datetime
import os
import os.path
import random
import re
import shutil
import socket
import sys
from threading import Lock
from xmlrpclib import APPLICATION_ERROR

from configobj import ConfigObj
import requests
import shutil_custom
from . import (
    app, auto_postprocessor, cache, db, helpers, logger, metadata, naming, providers,
    scheduler, showUpdater, show_queue, subtitles, traktChecker, versionChecker
)
from .common import SD, SKIPPED, WANTED
from .config import (
    CheckSection, ConfigMigrator, check_provider_setting, check_setting_bool, check_setting_float,
    check_setting_int, check_setting_str, load_provider_setting, save_provider_setting
)
from .databases import cache_db, failed_db, main_db
from .github_client import authenticate
from .helper import exceptions
from .indexers import indexer_api
from .indexers.indexer_exceptions import (
    indexer_attributenotfound, indexer_episodenotfound, indexer_error, indexer_exception,
    indexer_seasonnotfound, indexer_showincomplete, indexer_shownotfound, indexer_userabort
)
from .providers import NewznabProvider, TorrentRssProvider
from .providers.GenericProvider import GenericProvider
from .search import backlog, daily, proper
from .search.backlog import BacklogSearchScheduler, BacklogSearcher
from .search.daily import DailySearcher
from .search.proper import ProperFinder
from .search.queue import ForcedSearchQueue, SearchQueue, SnatchQueue
from .system.Shutdown import Shutdown

shutil.copyfile = shutil_custom.copyfile_custom
requests.packages.urllib3.disable_warnings()

indexerApi = indexer_api.indexerApi

ex = exceptions.ex

# Fixed values
__title__ = __name__
SRC_FOLDER = __name__
LEGACY_SRC_FOLDERS = ('sickbeard', 'sickrage', 'gui')
LIB_FOLDER = 'lib'
STATIC_FOLDER = 'static'
UNKNOWN_RELEASE_GROUP = 'Medusa'
BACKUP_DIR = 'backup'
BACKUP_FILENAME_PREFIX = 'backup'
BACKUP_FILENAME = BACKUP_FILENAME_PREFIX + '-{timestamp}.zip'
LEGACY_DB = 'sickbeard.db'
APPLICATION_DB = 'main.db'
FAILED_DB = 'failed.db'
CACHE_DB = 'cache.db'
LOG_FILENAME = 'application.log'
CONFIG_INI = 'config.ini'
GIT_ORG = 'pymedusa'
GIT_REPO = 'Medusa'
CHANGES_URL = 'https://cdn.pymedusa.com/news/CHANGES.md'
APPLICATION_URL = 'https://github.com/{org}/{repo}'.format(org=GIT_ORG, repo=GIT_REPO)
DONATIONS_URL = '{0}/wiki/Donations'.format(APPLICATION_URL)
WIKI_URL = '{0}/wiki'.format(APPLICATION_URL)
GITHUB_IO_URL = 'http://github.com/pymedusa/medusa.github.io/'
EXTRA_SCRIPTS_URL = '{0}/wiki/Post-Processing#extra-scripts'.format(APPLICATION_URL)
SUBTITLES_URL = '{0}/wiki/Subtitle%20Scripts'.format(APPLICATION_URL)
# TODO: create an app in pushover
PUSHOVER_URL = 'https://pushover.net/apps/clone/sickrage'
RARBG_APPID = 'medusa'
SECURE_TOKEN = 'medusa_user'

PID = None
CFG = None
CONFIG_FILE = None

# This is the version of the config we EXPECT to find
CONFIG_VERSION = 9

# Default encryption version (0 for None)
ENCRYPTION_VERSION = 0
ENCRYPTION_SECRET = None

PROG_DIR = '.'
MY_FULLNAME = None
MY_NAME = None
MY_ARGS = []
SYS_ENCODING = ''
DATA_DIR = ''
CREATEPID = False
PIDFILE = ''

DAEMON = None
NO_RESIZE = False

# system events
events = None

# schedulers
dailySearchScheduler = None
backlogSearchScheduler = None
showUpdateScheduler = None
versionCheckScheduler = None
showQueueScheduler = None
searchQueueScheduler = None
forcedSearchQueueScheduler = None
manualSnatchScheduler = None
properFinderScheduler = None
autoPostProcessorScheduler = None
subtitlesFinderScheduler = None
traktCheckerScheduler = None


showList = []

providerList = []
newznabProviderList = []
torrentRssProviderList = []
metadata_provider_dict = {}

NEWEST_VERSION = None
NEWEST_VERSION_STRING = None
VERSION_NOTIFY = False
AUTO_UPDATE = False
NOTIFY_ON_UPDATE = False
CUR_COMMIT_HASH = None
BRANCH = ''

GIT_RESET = True
GIT_RESET_BRANCHES = 'develop,master'
GIT_REMOTE_BRANCHES = ''
GIT_REMOTE = ''
GIT_REMOTE_URL = ''
CUR_COMMIT_BRANCH = ''
GIT_USERNAME = None
GIT_PASSWORD = None
GIT_PATH = None
DEVELOPER = False

NEWS_URL = 'https://cdn.pymedusa.com/news/news.md'
LOGO_URL = 'https://cdn.pymedusa.com/images/ico/favicon-64.png'

NEWS_LAST_READ = None
NEWS_LATEST = None
NEWS_UNREAD = 0

BROKEN_PROVIDERS = ''

INIT_LOCK = Lock()
started = False

ACTUAL_LOG_DIR = None
LOG_DIR = None
LOG_NR = 5
LOG_SIZE = 10.0

SOCKET_TIMEOUT = None

WEB_PORT = None
WEB_LOG = None
WEB_ROOT = None
WEB_USERNAME = None
WEB_PASSWORD = None
WEB_HOST = None
WEB_IPV6 = None
WEB_COOKIE_SECRET = None
WEB_USE_GZIP = True

SUBLIMINAL_LOG = False

DOWNLOAD_URL = None

HANDLE_REVERSE_PROXY = False
PROXY_SETTING = None
PROXY_INDEXERS = True
SSL_VERIFY = True

LOCALHOST_IP = None

CPU_PRESET = None

ANON_REDIRECT = None

API_KEY = None
API_ROOT = None

ENABLE_HTTPS = False
NOTIFY_ON_LOGIN = False
HTTPS_CERT = None
HTTPS_KEY = None

INDEXER_DEFAULT_LANGUAGE = None
EP_DEFAULT_DELETED_STATUS = None
LAUNCH_BROWSER = False
CACHE_DIR = None
ACTUAL_CACHE_DIR = None
ROOT_DIRS = None

TRASH_REMOVE_SHOW = False
TRASH_ROTATE_LOGS = False
SORT_ARTICLE = False
DEBUG = False
DBDEBUG = False
DISPLAY_ALL_SEASONS = True
DEFAULT_PAGE = 'home'
SEEDERS_LEECHERS_IN_NOTIFY = True


USE_LISTVIEW = False
METADATA_KODI = None
METADATA_KODI_12PLUS = None
METADATA_MEDIABROWSER = None
METADATA_PS3 = None
METADATA_WDTV = None
METADATA_TIVO = None
METADATA_MEDE8ER = None

QUALITY_DEFAULT = None
STATUS_DEFAULT = None
STATUS_DEFAULT_AFTER = None
FLATTEN_FOLDERS_DEFAULT = False
SUBTITLES_DEFAULT = False
INDEXER_DEFAULT = None
INDEXER_TIMEOUT = None
SCENE_DEFAULT = False
ANIME_DEFAULT = False
PROVIDER_ORDER = []

NAMING_MULTI_EP = False
NAMING_ANIME_MULTI_EP = False
NAMING_PATTERN = None
NAMING_ABD_PATTERN = None
NAMING_CUSTOM_ABD = False
NAMING_SPORTS_PATTERN = None
NAMING_CUSTOM_SPORTS = False
NAMING_ANIME_PATTERN = None
NAMING_CUSTOM_ANIME = False
NAMING_FORCE_FOLDERS = False
NAMING_STRIP_YEAR = False
NAMING_ANIME = None

USE_NZBS = False
USE_TORRENTS = False

NZB_METHOD = None
NZB_DIR = None
USENET_RETENTION = None
CACHE_TRIMMING = None
MAX_CACHE_AGE = None
TORRENT_METHOD = None
TORRENT_DIR = None
DOWNLOAD_PROPERS = False
CHECK_PROPERS_INTERVAL = None
ALLOW_HIGH_PRIORITY = False
SAB_FORCED = False
RANDOMIZE_PROVIDERS = False

AUTOPOSTPROCESSOR_FREQUENCY = None
DAILYSEARCH_FREQUENCY = None
UPDATE_FREQUENCY = None
BACKLOG_FREQUENCY = None
SHOWUPDATE_HOUR = None

DEFAULT_AUTOPOSTPROCESSOR_FREQUENCY = 10
DEFAULT_DAILYSEARCH_FREQUENCY = 40
DEFAULT_BACKLOG_FREQUENCY = 21
DEFAULT_UPDATE_FREQUENCY = 1
DEFAULT_SHOWUPDATE_HOUR = random.randint(2, 4)

MIN_AUTOPOSTPROCESSOR_FREQUENCY = 1
MIN_DAILYSEARCH_FREQUENCY = 10
MIN_BACKLOG_FREQUENCY = 10
MIN_UPDATE_FREQUENCY = 1

BACKLOG_DAYS = 7

ADD_SHOWS_WO_DIR = False
CREATE_MISSING_SHOW_DIRS = False
RENAME_EPISODES = False
AIRDATE_EPISODES = False
FILE_TIMESTAMP_TIMEZONE = None
PROCESS_AUTOMATICALLY = False
NO_DELETE = False
KEEP_PROCESSED_DIR = False
PROCESS_METHOD = None
DELRARCONTENTS = False
MOVE_ASSOCIATED_FILES = False
POSTPONE_IF_SYNC_FILES = True
POSTPONE_IF_NO_SUBS = False
NFO_RENAME = True
TV_DOWNLOAD_DIR = None
UNPACK = False
SKIP_REMOVED_FILES = False
ALLOWED_EXTENSIONS = "srt,nfo,sub,idx"

NZBS = False
NZBS_UID = None
NZBS_HASH = None

OMGWTFNZBS = False
OMGWTFNZBS_USERNAME = None
OMGWTFNZBS_APIKEY = None

NEWZBIN = False
NEWZBIN_USERNAME = None
NEWZBIN_PASSWORD = None

SAB_USERNAME = None
SAB_PASSWORD = None
SAB_APIKEY = None
SAB_CATEGORY = None
SAB_CATEGORY_BACKLOG = None
SAB_CATEGORY_ANIME = None
SAB_CATEGORY_ANIME_BACKLOG = None
SAB_HOST = ''

NZBGET_USERNAME = None
NZBGET_PASSWORD = None
NZBGET_CATEGORY = None
NZBGET_CATEGORY_BACKLOG = None
NZBGET_CATEGORY_ANIME = None
NZBGET_CATEGORY_ANIME_BACKLOG = None
NZBGET_HOST = None
NZBGET_USE_HTTPS = False
NZBGET_PRIORITY = 100

TORRENT_USERNAME = None
TORRENT_PASSWORD = None
TORRENT_HOST = ''
TORRENT_PATH = ''
TORRENT_SEED_TIME = None
TORRENT_PAUSED = False
TORRENT_HIGH_BANDWIDTH = False
TORRENT_LABEL = ''
TORRENT_LABEL_ANIME = ''
TORRENT_VERIFY_CERT = False
TORRENT_RPCURL = 'transmission'
TORRENT_AUTH_TYPE = 'none'

USE_KODI = False
KODI_ALWAYS_ON = True
KODI_NOTIFY_ONSNATCH = False
KODI_NOTIFY_ONDOWNLOAD = False
KODI_NOTIFY_ONSUBTITLEDOWNLOAD = False
KODI_UPDATE_LIBRARY = False
KODI_UPDATE_FULL = False
KODI_UPDATE_ONLYFIRST = False
KODI_HOST = ''
KODI_USERNAME = None
KODI_PASSWORD = None
KODI_LIBRARY_CLEAN_PENDING = False
KODI_CLEAN_LIBRARY = False

USE_PLEX_SERVER = False
PLEX_NOTIFY_ONSNATCH = False
PLEX_NOTIFY_ONDOWNLOAD = False
PLEX_NOTIFY_ONSUBTITLEDOWNLOAD = False
PLEX_UPDATE_LIBRARY = False
PLEX_SERVER_HOST = None
PLEX_SERVER_TOKEN = None
PLEX_CLIENT_HOST = None
PLEX_SERVER_USERNAME = None
PLEX_SERVER_PASSWORD = None

USE_PLEX_CLIENT = False
PLEX_CLIENT_USERNAME = None
PLEX_CLIENT_PASSWORD = None
PLEX_SERVER_HTTPS = None

USE_EMBY = False
EMBY_HOST = None
EMBY_APIKEY = None

USE_GROWL = False
GROWL_NOTIFY_ONSNATCH = False
GROWL_NOTIFY_ONDOWNLOAD = False
GROWL_NOTIFY_ONSUBTITLEDOWNLOAD = False
GROWL_HOST = ''
GROWL_PASSWORD = None

USE_FREEMOBILE = False
FREEMOBILE_NOTIFY_ONSNATCH = False
FREEMOBILE_NOTIFY_ONDOWNLOAD = False
FREEMOBILE_NOTIFY_ONSUBTITLEDOWNLOAD = False
FREEMOBILE_ID = ''
FREEMOBILE_APIKEY = ''

USE_TELEGRAM = False
TELEGRAM_NOTIFY_ONSNATCH = False
TELEGRAM_NOTIFY_ONDOWNLOAD = False
TELEGRAM_NOTIFY_ONSUBTITLEDOWNLOAD = False
TELEGRAM_ID = ''
TELEGRAM_APIKEY = ''

USE_PROWL = False
PROWL_NOTIFY_ONSNATCH = False
PROWL_NOTIFY_ONDOWNLOAD = False
PROWL_NOTIFY_ONSUBTITLEDOWNLOAD = False
PROWL_API = None
PROWL_PRIORITY = 0
PROWL_MESSAGE_TITLE = 'Medusa'

USE_TWITTER = False
TWITTER_NOTIFY_ONSNATCH = False
TWITTER_NOTIFY_ONDOWNLOAD = False
TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD = False
TWITTER_USERNAME = None
TWITTER_PASSWORD = None
TWITTER_PREFIX = None
TWITTER_DMTO = None
TWITTER_USEDM = False

USE_BOXCAR2 = False
BOXCAR2_NOTIFY_ONSNATCH = False
BOXCAR2_NOTIFY_ONDOWNLOAD = False
BOXCAR2_NOTIFY_ONSUBTITLEDOWNLOAD = False
BOXCAR2_ACCESSTOKEN = None

USE_PUSHOVER = False
PUSHOVER_NOTIFY_ONSNATCH = False
PUSHOVER_NOTIFY_ONDOWNLOAD = False
PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD = False
PUSHOVER_USERKEY = None
PUSHOVER_APIKEY = None
PUSHOVER_DEVICE = None
PUSHOVER_SOUND = None

USE_LIBNOTIFY = False
LIBNOTIFY_NOTIFY_ONSNATCH = False
LIBNOTIFY_NOTIFY_ONDOWNLOAD = False
LIBNOTIFY_NOTIFY_ONSUBTITLEDOWNLOAD = False

USE_NMJ = False
NMJ_HOST = None
NMJ_DATABASE = None
NMJ_MOUNT = None

ANIMESUPPORT = False
USE_ANIDB = False
ANIDB_USERNAME = None
ANIDB_PASSWORD = None
ANIDB_USE_MYLIST = False
ADBA_CONNECTION = None
ANIME_SPLIT_HOME = False

USE_SYNOINDEX = False

USE_NMJv2 = False
NMJv2_HOST = None
NMJv2_DATABASE = None
NMJv2_DBLOC = None

USE_SYNOLOGYNOTIFIER = False
SYNOLOGYNOTIFIER_NOTIFY_ONSNATCH = False
SYNOLOGYNOTIFIER_NOTIFY_ONDOWNLOAD = False
SYNOLOGYNOTIFIER_NOTIFY_ONSUBTITLEDOWNLOAD = False

USE_TRAKT = False
TRAKT_USERNAME = None
TRAKT_ACCESS_TOKEN = None
TRAKT_REFRESH_TOKEN = None
TRAKT_REMOVE_WATCHLIST = False
TRAKT_REMOVE_SERIESLIST = False
TRAKT_REMOVE_SHOW_FROM_APPLICATION = False
TRAKT_SYNC_WATCHLIST = False
TRAKT_METHOD_ADD = None
TRAKT_START_PAUSED = False
TRAKT_USE_RECOMMENDED = False
TRAKT_SYNC = False
TRAKT_SYNC_REMOVE = False
TRAKT_DEFAULT_INDEXER = None
TRAKT_TIMEOUT = None
TRAKT_BLACKLIST_NAME = None

USE_PYTIVO = False
PYTIVO_NOTIFY_ONSNATCH = False
PYTIVO_NOTIFY_ONDOWNLOAD = False
PYTIVO_NOTIFY_ONSUBTITLEDOWNLOAD = False
PYTIVO_UPDATE_LIBRARY = False
PYTIVO_HOST = ''
PYTIVO_SHARE_NAME = ''
PYTIVO_TIVO_NAME = ''

USE_NMA = False
NMA_NOTIFY_ONSNATCH = False
NMA_NOTIFY_ONDOWNLOAD = False
NMA_NOTIFY_ONSUBTITLEDOWNLOAD = False
NMA_API = None
NMA_PRIORITY = 0

USE_PUSHALOT = False
PUSHALOT_NOTIFY_ONSNATCH = False
PUSHALOT_NOTIFY_ONDOWNLOAD = False
PUSHALOT_NOTIFY_ONSUBTITLEDOWNLOAD = False
PUSHALOT_AUTHORIZATIONTOKEN = None

USE_PUSHBULLET = False
PUSHBULLET_NOTIFY_ONSNATCH = False
PUSHBULLET_NOTIFY_ONDOWNLOAD = False
PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD = False
PUSHBULLET_API = None
PUSHBULLET_DEVICE = None

USE_EMAIL = False
EMAIL_NOTIFY_ONSNATCH = False
EMAIL_NOTIFY_ONDOWNLOAD = False
EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD = False
EMAIL_HOST = None
EMAIL_PORT = 25
EMAIL_TLS = False
EMAIL_USER = None
EMAIL_PASSWORD = None
EMAIL_FROM = None
EMAIL_LIST = None
EMAIL_SUBJECT = None

HOME_LAYOUT = None
HISTORY_LAYOUT = None
HISTORY_LIMIT = 0
DISPLAY_SHOW_SPECIALS = False
COMING_EPS_LAYOUT = None
COMING_EPS_DISPLAY_PAUSED = False
COMING_EPS_SORT = None
COMING_EPS_MISSED_RANGE = None
FUZZY_DATING = False
TRIM_ZERO = False
DATE_PRESET = None
TIME_PRESET = None
TIME_PRESET_W_SECONDS = None
TIMEZONE_DISPLAY = None
THEME_NAME = None
POSTER_SORTBY = None
POSTER_SORTDIR = None
FANART_BACKGROUND = None
FANART_BACKGROUND_OPACITY = None

USE_SUBTITLES = False
SUBTITLES_LANGUAGES = []
SUBTITLES_DIR = ''
SUBTITLES_SERVICES_LIST = []
SUBTITLES_SERVICES_ENABLED = []
SUBTITLES_HISTORY = False
SUBTITLES_PERFECT_MATCH = False
EMBEDDED_SUBTITLES_ALL = False
EMBEDDED_SUBTITLES_UNKNOWN_LANG = False
SUBTITLES_STOP_AT_FIRST = False
SUBTITLES_HEARING_IMPAIRED = False
SUBTITLES_FINDER_FREQUENCY = 1
SUBTITLES_MULTI = False
SUBTITLES_EXTRA_SCRIPTS = []
SUBTITLES_PRE_SCRIPTS = []
SUBTITLES_KEEP_ONLY_WANTED = False

ADDIC7ED_USER = None
ADDIC7ED_PASS = None

ITASA_USER = None
ITASA_PASS = None

LEGENDASTV_USER = None
LEGENDASTV_PASS = None

OPENSUBTITLES_USER = None
OPENSUBTITLES_PASS = None

USE_FAILED_DOWNLOADS = False
DELETE_FAILED = False

EXTRA_SCRIPTS = []

IGNORE_WORDS = "german,french,core2hd,dutch,swedish,reenc,MrLss,dubbed"

PREFERRED_WORDS = ""

UNDESIRED_WORDS = ""

TRACKERS_LIST = "udp://coppersurfer.tk:6969/announce,udp://open.demonii.com:1337,"
TRACKERS_LIST += "udp://exodus.desync.com:6969,udp://9.rarbg.me:2710/announce,"
TRACKERS_LIST += "udp://glotorrents.pw:6969/announce,udp://tracker.openbittorrent.com:80/announce,"
TRACKERS_LIST += "udp://9.rarbg.to:2710/announce"

REQUIRE_WORDS = ""
IGNORED_SUBS_LIST = "dk,fin,heb,kor,nor,nordic,pl,swe"
IGNORE_UND_SUBS = False
SYNC_FILES = "!sync,lftp-pget-status,part,bts,!qb,!qB"

CALENDAR_UNPROTECTED = False
CALENDAR_ICONS = False
NO_RESTART = False

TMDB_API_KEY = 'edc5f123313769de83a71e157758030b'
# TRAKT_API_KEY = 'd4161a7a106424551add171e5470112e4afdaf2438e6ef2fe0548edc75924868'

TRAKT_API_KEY = '5c65f55e11d48c35385d9e8670615763a605fad28374c8ae553a7b7a50651ddd'
TRAKT_API_SECRET = 'b53e32045ac122a445ef163e6d859403301ffe9b17fb8321d428531b69022a82'
TRAKT_PIN_URL = 'https://trakt.tv/pin/4562'
TRAKT_OAUTH_URL = 'https://trakt.tv/'
TRAKT_API_URL = 'https://api.trakt.tv/'

FANART_API_KEY = '9b3afaf26f6241bdb57d6cc6bd798da7'

SHOWS_RECENT = []

__INITIALIZED__ = False

NEWZNAB_DATA = None

RECENTLY_DELETED = set()

RELEASES_IN_PP = []

PRIVACY_LEVEL = 'normal'


def get_backlog_cycle_time():
    cycletime = DAILYSEARCH_FREQUENCY * 2 + 7
    return max([cycletime, 720])


def initialize(consoleLogging=True):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    with INIT_LOCK:
        # pylint: disable=global-statement
        global BRANCH, GIT_RESET, GIT_RESET_BRANCHES, GIT_REMOTE, GIT_REMOTE_URL, CUR_COMMIT_HASH, CUR_COMMIT_BRANCH, ACTUAL_LOG_DIR, LOG_DIR, LOG_NR, LOG_SIZE, WEB_PORT, WEB_LOG, ENCRYPTION_VERSION, ENCRYPTION_SECRET, WEB_ROOT, WEB_USERNAME, WEB_PASSWORD, WEB_HOST, WEB_IPV6, WEB_COOKIE_SECRET, WEB_USE_GZIP, API_KEY, ENABLE_HTTPS, HTTPS_CERT, HTTPS_KEY, \
            HANDLE_REVERSE_PROXY, USE_NZBS, USE_TORRENTS, NZB_METHOD, NZB_DIR, DOWNLOAD_PROPERS, RANDOMIZE_PROVIDERS, CHECK_PROPERS_INTERVAL, ALLOW_HIGH_PRIORITY, SAB_FORCED, TORRENT_METHOD, NOTIFY_ON_LOGIN, SUBLIMINAL_LOG, PRIVACY_LEVEL, \
            SAB_USERNAME, SAB_PASSWORD, SAB_APIKEY, SAB_CATEGORY, SAB_CATEGORY_BACKLOG, SAB_CATEGORY_ANIME, SAB_CATEGORY_ANIME_BACKLOG, SAB_HOST, \
            NZBGET_USERNAME, NZBGET_PASSWORD, NZBGET_CATEGORY, NZBGET_CATEGORY_BACKLOG, NZBGET_CATEGORY_ANIME, NZBGET_CATEGORY_ANIME_BACKLOG, NZBGET_PRIORITY, NZBGET_HOST, NZBGET_USE_HTTPS, backlogSearchScheduler, \
            TORRENT_USERNAME, TORRENT_PASSWORD, TORRENT_HOST, TORRENT_PATH, TORRENT_SEED_TIME, TORRENT_PAUSED, TORRENT_HIGH_BANDWIDTH, TORRENT_LABEL, TORRENT_LABEL_ANIME, TORRENT_VERIFY_CERT, TORRENT_RPCURL, TORRENT_AUTH_TYPE, \
            USE_KODI, KODI_ALWAYS_ON, KODI_NOTIFY_ONSNATCH, KODI_NOTIFY_ONDOWNLOAD, KODI_NOTIFY_ONSUBTITLEDOWNLOAD, KODI_UPDATE_FULL, KODI_UPDATE_ONLYFIRST, \
            KODI_UPDATE_LIBRARY, KODI_HOST, KODI_USERNAME, KODI_PASSWORD, BACKLOG_FREQUENCY, KODI_LIBRARY_CLEAN_PENDING, KODI_CLEAN_LIBRARY, \
            USE_TRAKT, TRAKT_USERNAME, TRAKT_ACCESS_TOKEN, TRAKT_REFRESH_TOKEN, TRAKT_REMOVE_WATCHLIST, TRAKT_SYNC_WATCHLIST, TRAKT_REMOVE_SHOW_FROM_APPLICATION, TRAKT_METHOD_ADD, TRAKT_START_PAUSED, traktCheckerScheduler, TRAKT_USE_RECOMMENDED, TRAKT_SYNC, TRAKT_SYNC_REMOVE, TRAKT_DEFAULT_INDEXER, TRAKT_REMOVE_SERIESLIST, TRAKT_TIMEOUT, TRAKT_BLACKLIST_NAME, \
            USE_PLEX_SERVER, PLEX_NOTIFY_ONSNATCH, PLEX_NOTIFY_ONDOWNLOAD, PLEX_NOTIFY_ONSUBTITLEDOWNLOAD, PLEX_UPDATE_LIBRARY, USE_PLEX_CLIENT, PLEX_CLIENT_USERNAME, PLEX_CLIENT_PASSWORD, \
            PLEX_SERVER_HOST, PLEX_SERVER_TOKEN, PLEX_CLIENT_HOST, PLEX_SERVER_USERNAME, PLEX_SERVER_PASSWORD, PLEX_SERVER_HTTPS, MIN_BACKLOG_FREQUENCY, SKIP_REMOVED_FILES, ALLOWED_EXTENSIONS, \
            USE_EMBY, EMBY_HOST, EMBY_APIKEY, \
            showUpdateScheduler, __INITIALIZED__, INDEXER_DEFAULT_LANGUAGE, EP_DEFAULT_DELETED_STATUS, LAUNCH_BROWSER, TRASH_REMOVE_SHOW, TRASH_ROTATE_LOGS, SORT_ARTICLE, \
            NEWZNAB_DATA, NZBS, NZBS_UID, NZBS_HASH, INDEXER_DEFAULT, INDEXER_TIMEOUT, USENET_RETENTION, CACHE_TRIMMING, MAX_CACHE_AGE, TORRENT_DIR, \
            QUALITY_DEFAULT, FLATTEN_FOLDERS_DEFAULT, SUBTITLES_DEFAULT, STATUS_DEFAULT, STATUS_DEFAULT_AFTER, \
            GROWL_NOTIFY_ONSNATCH, GROWL_NOTIFY_ONDOWNLOAD, GROWL_NOTIFY_ONSUBTITLEDOWNLOAD, TWITTER_NOTIFY_ONSNATCH, TWITTER_NOTIFY_ONDOWNLOAD, TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD, USE_FREEMOBILE, FREEMOBILE_ID, FREEMOBILE_APIKEY, FREEMOBILE_NOTIFY_ONSNATCH, FREEMOBILE_NOTIFY_ONDOWNLOAD, FREEMOBILE_NOTIFY_ONSUBTITLEDOWNLOAD, \
            USE_TELEGRAM, TELEGRAM_ID, TELEGRAM_APIKEY, TELEGRAM_NOTIFY_ONSNATCH, TELEGRAM_NOTIFY_ONDOWNLOAD, TELEGRAM_NOTIFY_ONSUBTITLEDOWNLOAD, \
            USE_GROWL, GROWL_HOST, GROWL_PASSWORD, USE_PROWL, PROWL_NOTIFY_ONSNATCH, PROWL_NOTIFY_ONDOWNLOAD, PROWL_NOTIFY_ONSUBTITLEDOWNLOAD, PROWL_API, PROWL_PRIORITY, PROWL_MESSAGE_TITLE, \
            USE_PYTIVO, PYTIVO_NOTIFY_ONSNATCH, PYTIVO_NOTIFY_ONDOWNLOAD, PYTIVO_NOTIFY_ONSUBTITLEDOWNLOAD, PYTIVO_UPDATE_LIBRARY, PYTIVO_HOST, PYTIVO_SHARE_NAME, PYTIVO_TIVO_NAME, \
            USE_NMA, NMA_NOTIFY_ONSNATCH, NMA_NOTIFY_ONDOWNLOAD, NMA_NOTIFY_ONSUBTITLEDOWNLOAD, NMA_API, NMA_PRIORITY, \
            USE_PUSHALOT, PUSHALOT_NOTIFY_ONSNATCH, PUSHALOT_NOTIFY_ONDOWNLOAD, PUSHALOT_NOTIFY_ONSUBTITLEDOWNLOAD, PUSHALOT_AUTHORIZATIONTOKEN, \
            USE_PUSHBULLET, PUSHBULLET_NOTIFY_ONSNATCH, PUSHBULLET_NOTIFY_ONDOWNLOAD, PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD, PUSHBULLET_API, PUSHBULLET_DEVICE, \
            versionCheckScheduler, VERSION_NOTIFY, AUTO_UPDATE, NOTIFY_ON_UPDATE, PROCESS_AUTOMATICALLY, NO_DELETE, UNPACK, CPU_PRESET, \
            KEEP_PROCESSED_DIR, PROCESS_METHOD, DELRARCONTENTS, TV_DOWNLOAD_DIR, UPDATE_FREQUENCY, \
            showQueueScheduler, searchQueueScheduler, forcedSearchQueueScheduler, manualSnatchScheduler, ROOT_DIRS, CACHE_DIR, ACTUAL_CACHE_DIR, TIMEZONE_DISPLAY, \
            NAMING_PATTERN, NAMING_MULTI_EP, NAMING_ANIME_MULTI_EP, NAMING_FORCE_FOLDERS, NAMING_ABD_PATTERN, NAMING_CUSTOM_ABD, NAMING_SPORTS_PATTERN, NAMING_CUSTOM_SPORTS, NAMING_ANIME_PATTERN, NAMING_CUSTOM_ANIME, NAMING_STRIP_YEAR, \
            RENAME_EPISODES, AIRDATE_EPISODES, FILE_TIMESTAMP_TIMEZONE, properFinderScheduler, PROVIDER_ORDER, autoPostProcessorScheduler, \
            providerList, newznabProviderList, torrentRssProviderList, \
            EXTRA_SCRIPTS, USE_TWITTER, TWITTER_USERNAME, TWITTER_PASSWORD, TWITTER_PREFIX, DAILYSEARCH_FREQUENCY, TWITTER_DMTO, TWITTER_USEDM, \
            USE_BOXCAR2, BOXCAR2_ACCESSTOKEN, BOXCAR2_NOTIFY_ONDOWNLOAD, BOXCAR2_NOTIFY_ONSUBTITLEDOWNLOAD, BOXCAR2_NOTIFY_ONSNATCH, \
            USE_PUSHOVER, PUSHOVER_USERKEY, PUSHOVER_APIKEY, PUSHOVER_DEVICE, PUSHOVER_NOTIFY_ONDOWNLOAD, PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD, PUSHOVER_NOTIFY_ONSNATCH, PUSHOVER_SOUND, \
            USE_LIBNOTIFY, LIBNOTIFY_NOTIFY_ONSNATCH, LIBNOTIFY_NOTIFY_ONDOWNLOAD, LIBNOTIFY_NOTIFY_ONSUBTITLEDOWNLOAD, USE_NMJ, NMJ_HOST, NMJ_DATABASE, NMJ_MOUNT, USE_NMJv2, NMJv2_HOST, NMJv2_DATABASE, NMJv2_DBLOC, USE_SYNOINDEX, \
            USE_SYNOLOGYNOTIFIER, SYNOLOGYNOTIFIER_NOTIFY_ONSNATCH, SYNOLOGYNOTIFIER_NOTIFY_ONDOWNLOAD, SYNOLOGYNOTIFIER_NOTIFY_ONSUBTITLEDOWNLOAD, \
            USE_EMAIL, EMAIL_HOST, EMAIL_PORT, EMAIL_TLS, EMAIL_USER, EMAIL_PASSWORD, EMAIL_FROM, EMAIL_NOTIFY_ONSNATCH, EMAIL_NOTIFY_ONDOWNLOAD, EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD, EMAIL_LIST, EMAIL_SUBJECT, \
            USE_LISTVIEW, METADATA_KODI, METADATA_KODI_12PLUS, METADATA_MEDIABROWSER, METADATA_PS3, metadata_provider_dict, \
            NEWZBIN, NEWZBIN_USERNAME, NEWZBIN_PASSWORD, GIT_PATH, MOVE_ASSOCIATED_FILES, SYNC_FILES, POSTPONE_IF_SYNC_FILES, POSTPONE_IF_NO_SUBS, dailySearchScheduler, NFO_RENAME, \
            HOME_LAYOUT, HISTORY_LAYOUT, DISPLAY_SHOW_SPECIALS, COMING_EPS_LAYOUT, COMING_EPS_SORT, COMING_EPS_DISPLAY_PAUSED, COMING_EPS_MISSED_RANGE, FUZZY_DATING, TRIM_ZERO, DATE_PRESET, TIME_PRESET, TIME_PRESET_W_SECONDS, THEME_NAME, \
            POSTER_SORTBY, POSTER_SORTDIR, HISTORY_LIMIT, CREATE_MISSING_SHOW_DIRS, ADD_SHOWS_WO_DIR, \
            METADATA_WDTV, METADATA_TIVO, METADATA_MEDE8ER, IGNORE_WORDS, PREFERRED_WORDS, UNDESIRED_WORDS, TRACKERS_LIST, IGNORED_SUBS_LIST, REQUIRE_WORDS, CALENDAR_UNPROTECTED, CALENDAR_ICONS, NO_RESTART, IGNORE_UND_SUBS, \
            USE_SUBTITLES, SUBTITLES_LANGUAGES, SUBTITLES_DIR, SUBTITLES_SERVICES_LIST, SUBTITLES_SERVICES_ENABLED, SUBTITLES_HISTORY, SUBTITLES_FINDER_FREQUENCY, SUBTITLES_MULTI, SUBTITLES_KEEP_ONLY_WANTED, EMBEDDED_SUBTITLES_ALL, SUBTITLES_EXTRA_SCRIPTS, SUBTITLES_PRE_SCRIPTS, SUBTITLES_PERFECT_MATCH, subtitlesFinderScheduler, EMBEDDED_SUBTITLES_UNKNOWN_LANG, SUBTITLES_STOP_AT_FIRST, \
            SUBTITLES_HEARING_IMPAIRED, ADDIC7ED_USER, ADDIC7ED_PASS, ITASA_USER, ITASA_PASS, LEGENDASTV_USER, LEGENDASTV_PASS, OPENSUBTITLES_USER, OPENSUBTITLES_PASS, \
            USE_FAILED_DOWNLOADS, DELETE_FAILED, ANON_REDIRECT, LOCALHOST_IP, DEBUG, DBDEBUG, DEFAULT_PAGE, SEEDERS_LEECHERS_IN_NOTIFY, PROXY_SETTING, PROXY_INDEXERS, \
            AUTOPOSTPROCESSOR_FREQUENCY, SHOWUPDATE_HOUR, \
            ANIME_DEFAULT, NAMING_ANIME, ANIMESUPPORT, USE_ANIDB, ANIDB_USERNAME, ANIDB_PASSWORD, ANIDB_USE_MYLIST, \
            ANIME_SPLIT_HOME, SCENE_DEFAULT, DOWNLOAD_URL, BACKLOG_DAYS, GIT_USERNAME, GIT_PASSWORD, \
            DEVELOPER, DISPLAY_ALL_SEASONS, SSL_VERIFY, NEWS_LAST_READ, NEWS_LATEST, BROKEN_PROVIDERS, SOCKET_TIMEOUT, RECENTLY_DELETED, \
            FANART_BACKGROUND, FANART_BACKGROUND_OPACITY, GIT_REMOTE_BRANCHES, RELEASES_IN_PP

        if __INITIALIZED__:
            return False

        sections = [
            'General', 'Blackhole', 'Newzbin', 'SABnzbd', 'NZBget', 'KODI', 'PLEX', 'Emby', 'Growl', 'Prowl', 'Twitter',
            'Boxcar2', 'NMJ', 'NMJv2', 'Synology', 'SynologyNotifier', 'pyTivo', 'NMA', 'Pushalot', 'Pushbullet',
            'Subtitles', 'pyTivo',
        ]

        for section in sections:
            CheckSection(CFG, section)

        PRIVACY_LEVEL = check_setting_str(CFG, 'General', 'privacy_level', 'normal')
        # Need to be before any passwords
        ENCRYPTION_VERSION = check_setting_int(CFG, 'General', 'encryption_version', 0)
        ENCRYPTION_SECRET = check_setting_str(CFG, 'General', 'encryption_secret', helpers.generateCookieSecret(), censor_log='low')

        # git login info
        GIT_USERNAME = check_setting_str(CFG, 'General', 'git_username', '')
        GIT_PASSWORD = check_setting_str(CFG, 'General', 'git_password', '', censor_log='low')
        DEVELOPER = bool(check_setting_int(CFG, 'General', 'developer', 0))

        # debugging
        DEBUG = bool(check_setting_int(CFG, 'General', 'debug', 0))
        DBDEBUG = bool(check_setting_int(CFG, 'General', 'dbdebug', 0))

        DEFAULT_PAGE = check_setting_str(CFG, 'General', 'default_page', 'home')
        if DEFAULT_PAGE not in ('home', 'schedule', 'history', 'news', 'IRC'):
            DEFAULT_PAGE = 'home'

        SEEDERS_LEECHERS_IN_NOTIFY = check_setting_int(CFG, 'General', 'seeders_leechers_in_notify', 1)
        ACTUAL_LOG_DIR = check_setting_str(CFG, 'General', 'log_dir', 'Logs')
        LOG_DIR = os.path.normpath(os.path.join(DATA_DIR, ACTUAL_LOG_DIR))
        LOG_NR = check_setting_int(CFG, 'General', 'log_nr', 5)  # Default to 5 backup file (application.log.x)
        LOG_SIZE = check_setting_float(CFG, 'General', 'log_size', 10.0)  # Default to max 10MB per logfile

        if LOG_SIZE > 100:
            LOG_SIZE = 10.0

        if not helpers.makeDir(LOG_DIR):
            sys.stderr.write('Unable to create log folder {folder}'.format(folder=LOG_DIR))
            sys.exit(7)

        # init logging
        logger.backwards_compatibility()
        logger.init_logging(console_logging=consoleLogging)

        # git reset on update
        GIT_RESET = bool(check_setting_int(CFG, 'General', 'git_reset', 1))
        GIT_RESET_BRANCHES = check_setting_str(CFG, 'General', 'git_reset_branches', GIT_RESET_BRANCHES).split(',')
        if GIT_RESET_BRANCHES[0] == '':
            GIT_RESET_BRANCHES = []

        # current git branch
        BRANCH = check_setting_str(CFG, 'General', 'branch', '')

        # git_remote
        GIT_REMOTE = check_setting_str(CFG, 'General', 'git_remote', 'origin')
        GIT_REMOTE_URL = check_setting_str(CFG, 'General', 'git_remote_url', APPLICATION_URL)

        repo_url_re = re.compile(r'(?P<prefix>(?:git@github\.com:)|(?:https://github\.com/))(?P<org>\w+)/(?P<repo>\w+)\.git')
        m = repo_url_re.match(GIT_REMOTE_URL)
        if m:
            groups = m.groupdict()
            if groups['org'].lower() != GIT_ORG.lower() or groups['repo'].lower() != GIT_REPO.lower():
                GIT_REMOTE_URL = groups['prefix'] + GIT_ORG + '/' + GIT_REPO + '.git'
        else:
            GIT_REMOTE_URL = APPLICATION_URL

        # current commit hash
        CUR_COMMIT_HASH = check_setting_str(CFG, 'General', 'cur_commit_hash', '')

        # current commit branch
        CUR_COMMIT_BRANCH = check_setting_str(CFG, 'General', 'cur_commit_branch', '')
        ACTUAL_CACHE_DIR = check_setting_str(CFG, 'General', 'cache_dir', 'cache')

        # fix bad configs due to buggy code
        if ACTUAL_CACHE_DIR == 'None':
            ACTUAL_CACHE_DIR = 'cache'

        # unless they specify, put the cache dir inside the data dir
        if not os.path.isabs(ACTUAL_CACHE_DIR):
            CACHE_DIR = os.path.join(DATA_DIR, ACTUAL_CACHE_DIR)
        else:
            CACHE_DIR = ACTUAL_CACHE_DIR

        if not helpers.makeDir(CACHE_DIR):
            logger.log(u"!!! Creating local cache dir failed, using system default", logger.ERROR)
            CACHE_DIR = None

        # Check if we need to perform a restore of the cache folder
        restore_cache_folder(CACHE_DIR)
        cache.configure(CACHE_DIR)

        FANART_BACKGROUND = bool(check_setting_int(CFG, 'GUI', 'fanart_background', 1))
        FANART_BACKGROUND_OPACITY = check_setting_float(CFG, 'GUI', 'fanart_background_opacity', 0.4)

        THEME_NAME = check_setting_str(CFG, 'GUI', 'theme_name', 'dark')

        SOCKET_TIMEOUT = check_setting_int(CFG, 'General', 'socket_timeout', 30)
        socket.setdefaulttimeout(SOCKET_TIMEOUT)

        try:
            WEB_PORT = check_setting_int(CFG, 'General', 'web_port', 8081)
        except Exception:
            WEB_PORT = 8081

        if not 21 < WEB_PORT < 65535:
            WEB_PORT = 8081

        WEB_HOST = check_setting_str(CFG, 'General', 'web_host', '0.0.0.0')
        WEB_IPV6 = bool(check_setting_int(CFG, 'General', 'web_ipv6', 0))
        WEB_ROOT = check_setting_str(CFG, 'General', 'web_root', '').rstrip("/")
        WEB_LOG = bool(check_setting_int(CFG, 'General', 'web_log', 0))
        WEB_USERNAME = check_setting_str(CFG, 'General', 'web_username', '', censor_log='normal')
        WEB_PASSWORD = check_setting_str(CFG, 'General', 'web_password', '', censor_log='low')
        WEB_COOKIE_SECRET = check_setting_str(CFG, 'General', 'web_cookie_secret', helpers.generateCookieSecret(), censor_log='low')
        if not WEB_COOKIE_SECRET:
            WEB_COOKIE_SECRET = helpers.generateCookieSecret()

        WEB_USE_GZIP = bool(check_setting_int(CFG, 'General', 'web_use_gzip', 1))
        SUBLIMINAL_LOG = bool(check_setting_int(CFG, 'General', 'subliminal_log', 0))
        PRIVACY_LEVEL = check_setting_str(CFG, 'General', 'privacy_level', 'normal')

        SSL_VERIFY = bool(check_setting_int(CFG, 'General', 'ssl_verify', 1))

        INDEXER_DEFAULT_LANGUAGE = check_setting_str(CFG, 'General', 'indexerDefaultLang', 'en')
        EP_DEFAULT_DELETED_STATUS = check_setting_int(CFG, 'General', 'ep_default_deleted_status', 6)

        LAUNCH_BROWSER = bool(check_setting_int(CFG, 'General', 'launch_browser', 1))

        DOWNLOAD_URL = check_setting_str(CFG, 'General', 'download_url', "")

        LOCALHOST_IP = check_setting_str(CFG, 'General', 'localhost_ip', '')

        CPU_PRESET = check_setting_str(CFG, 'General', 'cpu_preset', 'NORMAL')

        ANON_REDIRECT = check_setting_str(CFG, 'General', 'anon_redirect', 'http://dereferer.org/?')
        PROXY_SETTING = check_setting_str(CFG, 'General', 'proxy_setting', '')
        PROXY_INDEXERS = bool(check_setting_int(CFG, 'General', 'proxy_indexers', 1))

        # attempt to help prevent users from breaking links by using a bad url
        if not ANON_REDIRECT.endswith('?'):
            ANON_REDIRECT = ''

        TRASH_REMOVE_SHOW = bool(check_setting_int(CFG, 'General', 'trash_remove_show', 0))
        TRASH_ROTATE_LOGS = bool(check_setting_int(CFG, 'General', 'trash_rotate_logs', 0))

        SORT_ARTICLE = bool(check_setting_int(CFG, 'General', 'sort_article', 0))

        API_KEY = check_setting_str(CFG, 'General', 'api_key', '', censor_log='low')

        ENABLE_HTTPS = bool(check_setting_int(CFG, 'General', 'enable_https', 0))

        NOTIFY_ON_LOGIN = bool(check_setting_int(CFG, 'General', 'notify_on_login', 0))

        HTTPS_CERT = check_setting_str(CFG, 'General', 'https_cert', 'server.crt')
        HTTPS_KEY = check_setting_str(CFG, 'General', 'https_key', 'server.key')

        HANDLE_REVERSE_PROXY = bool(check_setting_int(CFG, 'General', 'handle_reverse_proxy', 0))

        ROOT_DIRS = check_setting_str(CFG, 'General', 'root_dirs', '')
        if not re.match(r'\d+\|[^|]+(?:\|[^|]+)*', ROOT_DIRS):
            ROOT_DIRS = ''

        QUALITY_DEFAULT = check_setting_int(CFG, 'General', 'quality_default', SD)
        STATUS_DEFAULT = check_setting_int(CFG, 'General', 'status_default', SKIPPED)
        STATUS_DEFAULT_AFTER = check_setting_int(CFG, 'General', 'status_default_after', WANTED)
        VERSION_NOTIFY = bool(check_setting_int(CFG, 'General', 'version_notify', 1))
        AUTO_UPDATE = bool(check_setting_int(CFG, 'General', 'auto_update', 0))
        NOTIFY_ON_UPDATE = bool(check_setting_int(CFG, 'General', 'notify_on_update', 1))
        FLATTEN_FOLDERS_DEFAULT = bool(check_setting_int(CFG, 'General', 'flatten_folders_default', 0))
        INDEXER_DEFAULT = check_setting_int(CFG, 'General', 'indexer_default', 0)
        INDEXER_TIMEOUT = check_setting_int(CFG, 'General', 'indexer_timeout', 20)
        ANIME_DEFAULT = bool(check_setting_int(CFG, 'General', 'anime_default', 0))
        SCENE_DEFAULT = bool(check_setting_int(CFG, 'General', 'scene_default', 0))

        PROVIDER_ORDER = check_setting_str(CFG, 'General', 'provider_order', '').split()

        NAMING_PATTERN = check_setting_str(CFG, 'General', 'naming_pattern', 'Season %0S/%SN - S%0SE%0E - %EN')
        NAMING_ABD_PATTERN = check_setting_str(CFG, 'General', 'naming_abd_pattern', '%SN - %A.D - %EN')
        NAMING_CUSTOM_ABD = bool(check_setting_int(CFG, 'General', 'naming_custom_abd', 0))
        NAMING_SPORTS_PATTERN = check_setting_str(CFG, 'General', 'naming_sports_pattern', '%SN - %A-D - %EN')
        NAMING_ANIME_PATTERN = check_setting_str(CFG, 'General', 'naming_anime_pattern',
                                                 'Season %0S/%SN - S%0SE%0E - %EN')
        NAMING_ANIME = check_setting_int(CFG, 'General', 'naming_anime', 3)
        NAMING_CUSTOM_SPORTS = bool(check_setting_int(CFG, 'General', 'naming_custom_sports', 0))
        NAMING_CUSTOM_ANIME = bool(check_setting_int(CFG, 'General', 'naming_custom_anime', 0))
        NAMING_MULTI_EP = check_setting_int(CFG, 'General', 'naming_multi_ep', 1)
        NAMING_ANIME_MULTI_EP = check_setting_int(CFG, 'General', 'naming_anime_multi_ep', 1)
        NAMING_FORCE_FOLDERS = naming.check_force_season_folders()
        NAMING_STRIP_YEAR = bool(check_setting_int(CFG, 'General', 'naming_strip_year', 0))

        USE_NZBS = bool(check_setting_int(CFG, 'General', 'use_nzbs', 0))
        USE_TORRENTS = bool(check_setting_int(CFG, 'General', 'use_torrents', 1))

        NZB_METHOD = check_setting_str(CFG, 'General', 'nzb_method', 'blackhole')
        if NZB_METHOD not in ('blackhole', 'sabnzbd', 'nzbget'):
            NZB_METHOD = 'blackhole'

        TORRENT_METHOD = check_setting_str(CFG, 'General', 'torrent_method', 'blackhole')
        if TORRENT_METHOD not in ('blackhole', 'utorrent', 'transmission', 'deluge', 'deluged', 'download_station', 'rtorrent', 'qbittorrent', 'mlnet'):
            TORRENT_METHOD = 'blackhole'

        DOWNLOAD_PROPERS = bool(check_setting_int(CFG, 'General', 'download_propers', 1))
        CHECK_PROPERS_INTERVAL = check_setting_str(CFG, 'General', 'check_propers_interval', '')
        if CHECK_PROPERS_INTERVAL not in ('15m', '45m', '90m', '4h', 'daily'):
            CHECK_PROPERS_INTERVAL = 'daily'

        RANDOMIZE_PROVIDERS = bool(check_setting_int(CFG, 'General', 'randomize_providers', 0))

        ALLOW_HIGH_PRIORITY = bool(check_setting_int(CFG, 'General', 'allow_high_priority', 1))

        SKIP_REMOVED_FILES = bool(check_setting_int(CFG, 'General', 'skip_removed_files', 0))

        ALLOWED_EXTENSIONS = check_setting_str(CFG, 'General', 'allowed_extensions', ALLOWED_EXTENSIONS)

        USENET_RETENTION = check_setting_int(CFG, 'General', 'usenet_retention', 500)

        CACHE_TRIMMING = bool(check_setting_int(CFG, 'General', 'cache_trimming', 0))

        MAX_CACHE_AGE = check_setting_int(CFG, 'General', 'max_cache_age', 30)

        AUTOPOSTPROCESSOR_FREQUENCY = check_setting_int(CFG, 'General', 'autopostprocessor_frequency',
                                                        DEFAULT_AUTOPOSTPROCESSOR_FREQUENCY)
        if AUTOPOSTPROCESSOR_FREQUENCY < MIN_AUTOPOSTPROCESSOR_FREQUENCY:
            AUTOPOSTPROCESSOR_FREQUENCY = MIN_AUTOPOSTPROCESSOR_FREQUENCY

        DAILYSEARCH_FREQUENCY = check_setting_int(CFG, 'General', 'dailysearch_frequency',
                                                  DEFAULT_DAILYSEARCH_FREQUENCY)
        if DAILYSEARCH_FREQUENCY < MIN_DAILYSEARCH_FREQUENCY:
            DAILYSEARCH_FREQUENCY = MIN_DAILYSEARCH_FREQUENCY

        MIN_BACKLOG_FREQUENCY = get_backlog_cycle_time()
        BACKLOG_FREQUENCY = check_setting_int(CFG, 'General', 'backlog_frequency', DEFAULT_BACKLOG_FREQUENCY)
        if BACKLOG_FREQUENCY < MIN_BACKLOG_FREQUENCY:
            BACKLOG_FREQUENCY = MIN_BACKLOG_FREQUENCY

        UPDATE_FREQUENCY = check_setting_int(CFG, 'General', 'update_frequency', DEFAULT_UPDATE_FREQUENCY)
        if UPDATE_FREQUENCY < MIN_UPDATE_FREQUENCY:
            UPDATE_FREQUENCY = MIN_UPDATE_FREQUENCY

        SHOWUPDATE_HOUR = check_setting_int(CFG, 'General', 'showupdate_hour', DEFAULT_SHOWUPDATE_HOUR)
        if SHOWUPDATE_HOUR > 23:
            SHOWUPDATE_HOUR = 0
        elif SHOWUPDATE_HOUR < 0:
            SHOWUPDATE_HOUR = 0

        BACKLOG_DAYS = check_setting_int(CFG, 'General', 'backlog_days', 7)

        NEWS_LAST_READ = check_setting_str(CFG, 'General', 'news_last_read', '1970-01-01')
        NEWS_LATEST = NEWS_LAST_READ

        BROKEN_PROVIDERS = check_setting_str(CFG, 'General', 'broken_providers', ','.join(helpers.get_broken_providers()) or BROKEN_PROVIDERS)

        NZB_DIR = check_setting_str(CFG, 'Blackhole', 'nzb_dir', '')
        TORRENT_DIR = check_setting_str(CFG, 'Blackhole', 'torrent_dir', '')

        TV_DOWNLOAD_DIR = check_setting_str(CFG, 'General', 'tv_download_dir', '')
        PROCESS_AUTOMATICALLY = bool(check_setting_int(CFG, 'General', 'process_automatically', 0))
        NO_DELETE = bool(check_setting_int(CFG, 'General', 'no_delete', 0))
        UNPACK = bool(check_setting_int(CFG, 'General', 'unpack', 0))
        RENAME_EPISODES = bool(check_setting_int(CFG, 'General', 'rename_episodes', 1))
        AIRDATE_EPISODES = bool(check_setting_int(CFG, 'General', 'airdate_episodes', 0))
        FILE_TIMESTAMP_TIMEZONE = check_setting_str(CFG, 'General', 'file_timestamp_timezone', 'network')
        KEEP_PROCESSED_DIR = bool(check_setting_int(CFG, 'General', 'keep_processed_dir', 1))
        PROCESS_METHOD = check_setting_str(CFG, 'General', 'process_method', 'copy' if KEEP_PROCESSED_DIR else 'move')
        DELRARCONTENTS = bool(check_setting_int(CFG, 'General', 'del_rar_contents', 0))
        MOVE_ASSOCIATED_FILES = bool(check_setting_int(CFG, 'General', 'move_associated_files', 0))
        POSTPONE_IF_SYNC_FILES = bool(check_setting_int(CFG, 'General', 'postpone_if_sync_files', 1))
        POSTPONE_IF_NO_SUBS = bool(check_setting_int(CFG, 'General', 'postpone_if_no_subs', 0))
        SYNC_FILES = check_setting_str(CFG, 'General', 'sync_files', SYNC_FILES)
        NFO_RENAME = bool(check_setting_int(CFG, 'General', 'nfo_rename', 1))
        CREATE_MISSING_SHOW_DIRS = bool(check_setting_int(CFG, 'General', 'create_missing_show_dirs', 0))
        ADD_SHOWS_WO_DIR = bool(check_setting_int(CFG, 'General', 'add_shows_wo_dir', 0))

        NZBS = bool(check_setting_int(CFG, 'NZBs', 'nzbs', 0))
        NZBS_UID = check_setting_str(CFG, 'NZBs', 'nzbs_uid', '', censor_log='normal')
        NZBS_HASH = check_setting_str(CFG, 'NZBs', 'nzbs_hash', '', censor_log='low')

        NEWZBIN = bool(check_setting_int(CFG, 'Newzbin', 'newzbin', 0))
        NEWZBIN_USERNAME = check_setting_str(CFG, 'Newzbin', 'newzbin_username', '', censor_log='normal')
        NEWZBIN_PASSWORD = check_setting_str(CFG, 'Newzbin', 'newzbin_password', '', censor_log='low')

        SAB_USERNAME = check_setting_str(CFG, 'SABnzbd', 'sab_username', '', censor_log='normal')
        SAB_PASSWORD = check_setting_str(CFG, 'SABnzbd', 'sab_password', '', censor_log='low')
        SAB_APIKEY = check_setting_str(CFG, 'SABnzbd', 'sab_apikey', '', censor_log='low')
        SAB_CATEGORY = check_setting_str(CFG, 'SABnzbd', 'sab_category', 'tv')
        SAB_CATEGORY_BACKLOG = check_setting_str(CFG, 'SABnzbd', 'sab_category_backlog', SAB_CATEGORY)
        SAB_CATEGORY_ANIME = check_setting_str(CFG, 'SABnzbd', 'sab_category_anime', 'anime')
        SAB_CATEGORY_ANIME_BACKLOG = check_setting_str(CFG, 'SABnzbd', 'sab_category_anime_backlog', SAB_CATEGORY_ANIME)
        SAB_HOST = check_setting_str(CFG, 'SABnzbd', 'sab_host', '', censor_log='high')
        SAB_FORCED = bool(check_setting_int(CFG, 'SABnzbd', 'sab_forced', 0))

        NZBGET_USERNAME = check_setting_str(CFG, 'NZBget', 'nzbget_username', 'nzbget', censor_log='normal')
        NZBGET_PASSWORD = check_setting_str(CFG, 'NZBget', 'nzbget_password', 'tegbzn6789', censor_log='low')
        NZBGET_CATEGORY = check_setting_str(CFG, 'NZBget', 'nzbget_category', 'tv')
        NZBGET_CATEGORY_BACKLOG = check_setting_str(CFG, 'NZBget', 'nzbget_category_backlog', NZBGET_CATEGORY)
        NZBGET_CATEGORY_ANIME = check_setting_str(CFG, 'NZBget', 'nzbget_category_anime', 'anime')
        NZBGET_CATEGORY_ANIME_BACKLOG = check_setting_str(CFG, 'NZBget', 'nzbget_category_anime_backlog', NZBGET_CATEGORY_ANIME)
        NZBGET_HOST = check_setting_str(CFG, 'NZBget', 'nzbget_host', '', censor_log='high')
        NZBGET_USE_HTTPS = bool(check_setting_int(CFG, 'NZBget', 'nzbget_use_https', 0))
        NZBGET_PRIORITY = check_setting_int(CFG, 'NZBget', 'nzbget_priority', 100)

        TORRENT_USERNAME = check_setting_str(CFG, 'TORRENT', 'torrent_username', '', censor_log='normal')
        TORRENT_PASSWORD = check_setting_str(CFG, 'TORRENT', 'torrent_password', '', censor_log='low')
        TORRENT_HOST = check_setting_str(CFG, 'TORRENT', 'torrent_host', '', censor_log='high')
        TORRENT_PATH = check_setting_str(CFG, 'TORRENT', 'torrent_path', '')
        TORRENT_SEED_TIME = check_setting_int(CFG, 'TORRENT', 'torrent_seed_time', 0)
        TORRENT_PAUSED = bool(check_setting_int(CFG, 'TORRENT', 'torrent_paused', 0))
        TORRENT_HIGH_BANDWIDTH = bool(check_setting_int(CFG, 'TORRENT', 'torrent_high_bandwidth', 0))
        TORRENT_LABEL = check_setting_str(CFG, 'TORRENT', 'torrent_label', '')
        TORRENT_LABEL_ANIME = check_setting_str(CFG, 'TORRENT', 'torrent_label_anime', '')
        TORRENT_VERIFY_CERT = bool(check_setting_int(CFG, 'TORRENT', 'torrent_verify_cert', 0))
        TORRENT_RPCURL = check_setting_str(CFG, 'TORRENT', 'torrent_rpcurl', 'transmission')
        TORRENT_AUTH_TYPE = check_setting_str(CFG, 'TORRENT', 'torrent_auth_type', '')

        USE_KODI = bool(check_setting_int(CFG, 'KODI', 'use_kodi', 0))
        KODI_ALWAYS_ON = bool(check_setting_int(CFG, 'KODI', 'kodi_always_on', 1))
        KODI_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'KODI', 'kodi_notify_onsnatch', 0))
        KODI_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'KODI', 'kodi_notify_ondownload', 0))
        KODI_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(CFG, 'KODI', 'kodi_notify_onsubtitledownload', 0))
        KODI_UPDATE_LIBRARY = bool(check_setting_int(CFG, 'KODI', 'kodi_update_library', 0))
        KODI_UPDATE_FULL = bool(check_setting_int(CFG, 'KODI', 'kodi_update_full', 0))
        KODI_UPDATE_ONLYFIRST = bool(check_setting_int(CFG, 'KODI', 'kodi_update_onlyfirst', 0))
        KODI_HOST = check_setting_str(CFG, 'KODI', 'kodi_host', '', censor_log='high')
        KODI_USERNAME = check_setting_str(CFG, 'KODI', 'kodi_username', '', censor_log='normal')
        KODI_PASSWORD = check_setting_str(CFG, 'KODI', 'kodi_password', '', censor_log='low')
        KODI_CLEAN_LIBRARY = bool(check_setting_int(CFG, 'KODI', 'kodi_clean_library', 0))

        USE_PLEX_SERVER = bool(check_setting_int(CFG, 'Plex', 'use_plex_server', 0))
        PLEX_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Plex', 'plex_notify_onsnatch', 0))
        PLEX_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Plex', 'plex_notify_ondownload', 0))
        PLEX_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(CFG, 'Plex', 'plex_notify_onsubtitledownload', 0))
        PLEX_UPDATE_LIBRARY = bool(check_setting_int(CFG, 'Plex', 'plex_update_library', 0))
        PLEX_SERVER_HOST = check_setting_str(CFG, 'Plex', 'plex_server_host', '', censor_log='high')
        PLEX_SERVER_TOKEN = check_setting_str(CFG, 'Plex', 'plex_server_token', '', censor_log='high')
        PLEX_CLIENT_HOST = check_setting_str(CFG, 'Plex', 'plex_client_host', '', censor_log='high')
        PLEX_SERVER_USERNAME = check_setting_str(CFG, 'Plex', 'plex_server_username', '', censor_log='normal')
        PLEX_SERVER_PASSWORD = check_setting_str(CFG, 'Plex', 'plex_server_password', '', censor_log='low')
        USE_PLEX_CLIENT = bool(check_setting_int(CFG, 'Plex', 'use_plex_client', 0))
        PLEX_CLIENT_USERNAME = check_setting_str(CFG, 'Plex', 'plex_client_username', '', censor_log='normal')
        PLEX_CLIENT_PASSWORD = check_setting_str(CFG, 'Plex', 'plex_client_password', '', censor_log='low')
        PLEX_SERVER_HTTPS = bool(check_setting_int(CFG, 'Plex', 'plex_server_https', 0))

        USE_EMBY = bool(check_setting_int(CFG, 'Emby', 'use_emby', 0))
        EMBY_HOST = check_setting_str(CFG, 'Emby', 'emby_host', '', censor_log='high')
        EMBY_APIKEY = check_setting_str(CFG, 'Emby', 'emby_apikey', '', censor_log='low')

        USE_GROWL = bool(check_setting_int(CFG, 'Growl', 'use_growl', 0))
        GROWL_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Growl', 'growl_notify_onsnatch', 0))
        GROWL_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Growl', 'growl_notify_ondownload', 0))
        GROWL_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(CFG, 'Growl', 'growl_notify_onsubtitledownload', 0))
        GROWL_HOST = check_setting_str(CFG, 'Growl', 'growl_host', '')
        GROWL_PASSWORD = check_setting_str(CFG, 'Growl', 'growl_password', '', censor_log='low')

        USE_FREEMOBILE = bool(check_setting_int(CFG, 'FreeMobile', 'use_freemobile', 0))
        FREEMOBILE_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'FreeMobile', 'freemobile_notify_onsnatch', 0))
        FREEMOBILE_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'FreeMobile', 'freemobile_notify_ondownload', 0))
        FREEMOBILE_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(CFG, 'FreeMobile', 'freemobile_notify_onsubtitledownload', 0))
        FREEMOBILE_ID = check_setting_str(CFG, 'FreeMobile', 'freemobile_id', '', censor_log='normal')
        FREEMOBILE_APIKEY = check_setting_str(CFG, 'FreeMobile', 'freemobile_apikey', '', censor_log='low')

        USE_TELEGRAM = bool(check_setting_int(CFG, 'Telegram', 'use_telegram', 0))
        TELEGRAM_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Telegram', 'telegram_notify_onsnatch', 0))
        TELEGRAM_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Telegram', 'telegram_notify_ondownload', 0))
        TELEGRAM_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(CFG, 'Telegram', 'telegram_notify_onsubtitledownload', 0))
        TELEGRAM_ID = check_setting_str(CFG, 'Telegram', 'telegram_id', '', censor_log='normal')
        TELEGRAM_APIKEY = check_setting_str(CFG, 'Telegram', 'telegram_apikey', '', censor_log='low')

        USE_PROWL = bool(check_setting_int(CFG, 'Prowl', 'use_prowl', 0))
        PROWL_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Prowl', 'prowl_notify_onsnatch', 0))
        PROWL_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Prowl', 'prowl_notify_ondownload', 0))
        PROWL_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(CFG, 'Prowl', 'prowl_notify_onsubtitledownload', 0))
        PROWL_API = check_setting_str(CFG, 'Prowl', 'prowl_api', '', censor_log='low')
        PROWL_PRIORITY = check_setting_str(CFG, 'Prowl', 'prowl_priority', "0")
        PROWL_MESSAGE_TITLE = check_setting_str(CFG, 'Prowl', 'prowl_message_title', "Medusa")

        USE_TWITTER = bool(check_setting_int(CFG, 'Twitter', 'use_twitter', 0))
        TWITTER_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Twitter', 'twitter_notify_onsnatch', 0))
        TWITTER_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Twitter', 'twitter_notify_ondownload', 0))
        TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD = bool(
            check_setting_int(CFG, 'Twitter', 'twitter_notify_onsubtitledownload', 0))
        TWITTER_USERNAME = check_setting_str(CFG, 'Twitter', 'twitter_username', '', censor_log='normal')
        TWITTER_PASSWORD = check_setting_str(CFG, 'Twitter', 'twitter_password', '', censor_log='low')
        TWITTER_PREFIX = check_setting_str(CFG, 'Twitter', 'twitter_prefix', GIT_REPO)
        TWITTER_DMTO = check_setting_str(CFG, 'Twitter', 'twitter_dmto', '')
        TWITTER_USEDM = bool(check_setting_int(CFG, 'Twitter', 'twitter_usedm', 0))

        USE_BOXCAR2 = bool(check_setting_int(CFG, 'Boxcar2', 'use_boxcar2', 0))
        BOXCAR2_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Boxcar2', 'boxcar2_notify_onsnatch', 0))
        BOXCAR2_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Boxcar2', 'boxcar2_notify_ondownload', 0))
        BOXCAR2_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(CFG, 'Boxcar2', 'boxcar2_notify_onsubtitledownload', 0))
        BOXCAR2_ACCESSTOKEN = check_setting_str(CFG, 'Boxcar2', 'boxcar2_accesstoken', '', censor_log='low')

        USE_PUSHOVER = bool(check_setting_int(CFG, 'Pushover', 'use_pushover', 0))
        PUSHOVER_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Pushover', 'pushover_notify_onsnatch', 0))
        PUSHOVER_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Pushover', 'pushover_notify_ondownload', 0))
        PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(CFG, 'Pushover', 'pushover_notify_onsubtitledownload', 0))
        PUSHOVER_USERKEY = check_setting_str(CFG, 'Pushover', 'pushover_userkey', '', censor_log='normal')
        PUSHOVER_APIKEY = check_setting_str(CFG, 'Pushover', 'pushover_apikey', '', censor_log='low')
        PUSHOVER_DEVICE = check_setting_str(CFG, 'Pushover', 'pushover_device', '')
        PUSHOVER_SOUND = check_setting_str(CFG, 'Pushover', 'pushover_sound', 'pushover')

        USE_LIBNOTIFY = bool(check_setting_int(CFG, 'Libnotify', 'use_libnotify', 0))
        LIBNOTIFY_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Libnotify', 'libnotify_notify_onsnatch', 0))
        LIBNOTIFY_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Libnotify', 'libnotify_notify_ondownload', 0))
        LIBNOTIFY_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(CFG, 'Libnotify', 'libnotify_notify_onsubtitledownload', 0))

        USE_NMJ = bool(check_setting_int(CFG, 'NMJ', 'use_nmj', 0))
        NMJ_HOST = check_setting_str(CFG, 'NMJ', 'nmj_host', '')
        NMJ_DATABASE = check_setting_str(CFG, 'NMJ', 'nmj_database', '')
        NMJ_MOUNT = check_setting_str(CFG, 'NMJ', 'nmj_mount', '')

        USE_NMJv2 = bool(check_setting_int(CFG, 'NMJv2', 'use_nmjv2', 0))
        NMJv2_HOST = check_setting_str(CFG, 'NMJv2', 'nmjv2_host', '')
        NMJv2_DATABASE = check_setting_str(CFG, 'NMJv2', 'nmjv2_database', '')
        NMJv2_DBLOC = check_setting_str(CFG, 'NMJv2', 'nmjv2_dbloc', '')

        USE_SYNOINDEX = bool(check_setting_int(CFG, 'Synology', 'use_synoindex', 0))

        USE_SYNOLOGYNOTIFIER = bool(check_setting_int(CFG, 'SynologyNotifier', 'use_synologynotifier', 0))
        SYNOLOGYNOTIFIER_NOTIFY_ONSNATCH = bool(
            check_setting_int(CFG, 'SynologyNotifier', 'synologynotifier_notify_onsnatch', 0))
        SYNOLOGYNOTIFIER_NOTIFY_ONDOWNLOAD = bool(
            check_setting_int(CFG, 'SynologyNotifier', 'synologynotifier_notify_ondownload', 0))
        SYNOLOGYNOTIFIER_NOTIFY_ONSUBTITLEDOWNLOAD = bool(
            check_setting_int(CFG, 'SynologyNotifier', 'synologynotifier_notify_onsubtitledownload', 0))

        USE_TRAKT = bool(check_setting_int(CFG, 'Trakt', 'use_trakt', 0))
        TRAKT_USERNAME = check_setting_str(CFG, 'Trakt', 'trakt_username', '', censor_log='normal')
        TRAKT_ACCESS_TOKEN = check_setting_str(CFG, 'Trakt', 'trakt_access_token', '', censor_log='low')
        TRAKT_REFRESH_TOKEN = check_setting_str(CFG, 'Trakt', 'trakt_refresh_token', '', censor_log='low')
        TRAKT_REMOVE_WATCHLIST = bool(check_setting_int(CFG, 'Trakt', 'trakt_remove_watchlist', 0))
        TRAKT_REMOVE_SERIESLIST = bool(check_setting_int(CFG, 'Trakt', 'trakt_remove_serieslist', 0))

        # Check if user has legacy setting and store value in new setting
        if check_setting_int(CFG, 'Trakt', 'trakt_remove_show_from_sickrage', None) is not None:
            TRAKT_REMOVE_SHOW_FROM_APPLICATION = bool(check_setting_int(CFG, 'Trakt', 'trakt_remove_show_from_sickrage', 0))
        else:
            TRAKT_REMOVE_SHOW_FROM_APPLICATION = bool(check_setting_int(CFG, 'Trakt', 'trakt_remove_show_from_application', 0))

        TRAKT_SYNC_WATCHLIST = bool(check_setting_int(CFG, 'Trakt', 'trakt_sync_watchlist', 0))
        TRAKT_METHOD_ADD = check_setting_int(CFG, 'Trakt', 'trakt_method_add', 0)
        TRAKT_START_PAUSED = bool(check_setting_int(CFG, 'Trakt', 'trakt_start_paused', 0))
        TRAKT_USE_RECOMMENDED = bool(check_setting_int(CFG, 'Trakt', 'trakt_use_recommended', 0))
        TRAKT_SYNC = bool(check_setting_int(CFG, 'Trakt', 'trakt_sync', 0))
        TRAKT_SYNC_REMOVE = bool(check_setting_int(CFG, 'Trakt', 'trakt_sync_remove', 0))
        TRAKT_DEFAULT_INDEXER = check_setting_int(CFG, 'Trakt', 'trakt_default_indexer', 1)
        TRAKT_TIMEOUT = check_setting_int(CFG, 'Trakt', 'trakt_timeout', 30)
        TRAKT_BLACKLIST_NAME = check_setting_str(CFG, 'Trakt', 'trakt_blacklist_name', '')

        USE_PYTIVO = bool(check_setting_int(CFG, 'pyTivo', 'use_pytivo', 0))
        PYTIVO_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'pyTivo', 'pytivo_notify_onsnatch', 0))
        PYTIVO_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'pyTivo', 'pytivo_notify_ondownload', 0))
        PYTIVO_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(CFG, 'pyTivo', 'pytivo_notify_onsubtitledownload', 0))
        PYTIVO_UPDATE_LIBRARY = bool(check_setting_int(CFG, 'pyTivo', 'pyTivo_update_library', 0))
        PYTIVO_HOST = check_setting_str(CFG, 'pyTivo', 'pytivo_host', '')
        PYTIVO_SHARE_NAME = check_setting_str(CFG, 'pyTivo', 'pytivo_share_name', '')
        PYTIVO_TIVO_NAME = check_setting_str(CFG, 'pyTivo', 'pytivo_tivo_name', '')

        USE_NMA = bool(check_setting_int(CFG, 'NMA', 'use_nma', 0))
        NMA_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'NMA', 'nma_notify_onsnatch', 0))
        NMA_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'NMA', 'nma_notify_ondownload', 0))
        NMA_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(CFG, 'NMA', 'nma_notify_onsubtitledownload', 0))
        NMA_API = check_setting_str(CFG, 'NMA', 'nma_api', '', censor_log='low')
        NMA_PRIORITY = check_setting_str(CFG, 'NMA', 'nma_priority', "0")

        USE_PUSHALOT = bool(check_setting_int(CFG, 'Pushalot', 'use_pushalot', 0))
        PUSHALOT_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Pushalot', 'pushalot_notify_onsnatch', 0))
        PUSHALOT_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Pushalot', 'pushalot_notify_ondownload', 0))
        PUSHALOT_NOTIFY_ONSUBTITLEDOWNLOAD = bool(
            check_setting_int(CFG, 'Pushalot', 'pushalot_notify_onsubtitledownload', 0))
        PUSHALOT_AUTHORIZATIONTOKEN = check_setting_str(CFG, 'Pushalot', 'pushalot_authorizationtoken', '', censor_log='low')

        USE_PUSHBULLET = bool(check_setting_int(CFG, 'Pushbullet', 'use_pushbullet', 0))
        PUSHBULLET_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Pushbullet', 'pushbullet_notify_onsnatch', 0))
        PUSHBULLET_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Pushbullet', 'pushbullet_notify_ondownload', 0))
        PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD = bool(
            check_setting_int(CFG, 'Pushbullet', 'pushbullet_notify_onsubtitledownload', 0))
        PUSHBULLET_API = check_setting_str(CFG, 'Pushbullet', 'pushbullet_api', '', censor_log='low')
        PUSHBULLET_DEVICE = check_setting_str(CFG, 'Pushbullet', 'pushbullet_device', '')

        USE_EMAIL = bool(check_setting_int(CFG, 'Email', 'use_email', 0))
        EMAIL_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Email', 'email_notify_onsnatch', 0))
        EMAIL_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Email', 'email_notify_ondownload', 0))
        EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(CFG, 'Email', 'email_notify_onsubtitledownload', 0))
        EMAIL_HOST = check_setting_str(CFG, 'Email', 'email_host', '')
        EMAIL_PORT = check_setting_int(CFG, 'Email', 'email_port', 25)
        EMAIL_TLS = bool(check_setting_int(CFG, 'Email', 'email_tls', 0))
        EMAIL_USER = check_setting_str(CFG, 'Email', 'email_user', '', censor_log='normal')
        EMAIL_PASSWORD = check_setting_str(CFG, 'Email', 'email_password', '', censor_log='low')
        EMAIL_FROM = check_setting_str(CFG, 'Email', 'email_from', '')
        EMAIL_LIST = check_setting_str(CFG, 'Email', 'email_list', '')
        EMAIL_SUBJECT = check_setting_str(CFG, 'Email', 'email_subject', '')

        USE_SUBTITLES = bool(check_setting_int(CFG, 'Subtitles', 'use_subtitles', 0))
        SUBTITLES_LANGUAGES = check_setting_str(CFG, 'Subtitles', 'subtitles_languages', '').split(',')
        if SUBTITLES_LANGUAGES[0] == '':
            SUBTITLES_LANGUAGES = []
        SUBTITLES_DIR = check_setting_str(CFG, 'Subtitles', 'subtitles_dir', '')
        SUBTITLES_SERVICES_LIST = check_setting_str(CFG, 'Subtitles', 'SUBTITLES_SERVICES_LIST', '').split(',')
        SUBTITLES_SERVICES_ENABLED = [int(x) for x in
                                      check_setting_str(CFG, 'Subtitles', 'SUBTITLES_SERVICES_ENABLED', '').split('|')
                                      if x]
        SUBTITLES_DEFAULT = bool(check_setting_int(CFG, 'Subtitles', 'subtitles_default', 0))
        SUBTITLES_HISTORY = bool(check_setting_int(CFG, 'Subtitles', 'subtitles_history', 0))
        SUBTITLES_PERFECT_MATCH = bool(check_setting_int(CFG, 'Subtitles', 'subtitles_perfect_match', 1))
        EMBEDDED_SUBTITLES_ALL = bool(check_setting_int(CFG, 'Subtitles', 'embedded_subtitles_all', 0))
        SUBTITLES_STOP_AT_FIRST = bool(check_setting_int(CFG, 'Subtitles', 'subtitles_stop_at_first', 0))
        EMBEDDED_SUBTITLES_UNKNOWN_LANG = bool(check_setting_int(CFG, 'Subtitles', 'embedded_subtitles_unknown_lang', 0))
        SUBTITLES_HEARING_IMPAIRED = bool(check_setting_int(CFG, 'Subtitles', 'subtitles_hearing_impaired', 0))
        SUBTITLES_FINDER_FREQUENCY = check_setting_int(CFG, 'Subtitles', 'subtitles_finder_frequency', 1)
        SUBTITLES_MULTI = bool(check_setting_int(CFG, 'Subtitles', 'subtitles_multi', 1))
        SUBTITLES_KEEP_ONLY_WANTED = bool(check_setting_int(CFG, 'Subtitles', 'subtitles_keep_only_wanted', 0))
        SUBTITLES_EXTRA_SCRIPTS = [x.strip() for x in check_setting_str(CFG, 'Subtitles', 'subtitles_extra_scripts', '').split('|') if x.strip()]
        SUBTITLES_PRE_SCRIPTS = [x.strip() for x in check_setting_str(CFG, 'Subtitles', 'subtitles_pre_scripts', '').split('|') if x.strip()]

        ADDIC7ED_USER = check_setting_str(CFG, 'Subtitles', 'addic7ed_username', '', censor_log='normal')
        ADDIC7ED_PASS = check_setting_str(CFG, 'Subtitles', 'addic7ed_password', '', censor_log='low')

        ITASA_USER = check_setting_str(CFG, 'Subtitles', 'itasa_username', '', censor_log='normal')
        ITASA_PASS = check_setting_str(CFG, 'Subtitles', 'itasa_password', '', censor_log='low')

        LEGENDASTV_USER = check_setting_str(CFG, 'Subtitles', 'legendastv_username', '', censor_log='normal')
        LEGENDASTV_PASS = check_setting_str(CFG, 'Subtitles', 'legendastv_password', '', censor_log='low')

        OPENSUBTITLES_USER = check_setting_str(CFG, 'Subtitles', 'opensubtitles_username', '', censor_log='normal')
        OPENSUBTITLES_PASS = check_setting_str(CFG, 'Subtitles', 'opensubtitles_password', '', censor_log='low')

        USE_FAILED_DOWNLOADS = bool(check_setting_int(CFG, 'FailedDownloads', 'use_failed_downloads', 0))
        DELETE_FAILED = bool(check_setting_int(CFG, 'FailedDownloads', 'delete_failed', 0))

        GIT_PATH = check_setting_str(CFG, 'General', 'git_path', '')

        IGNORE_WORDS = check_setting_str(CFG, 'General', 'ignore_words', IGNORE_WORDS)
        PREFERRED_WORDS = check_setting_str(CFG, 'General', 'preferred_words', PREFERRED_WORDS)
        UNDESIRED_WORDS = check_setting_str(CFG, 'General', 'undesired_words', UNDESIRED_WORDS)
        TRACKERS_LIST = check_setting_str(CFG, 'General', 'trackers_list', TRACKERS_LIST)
        REQUIRE_WORDS = check_setting_str(CFG, 'General', 'require_words', REQUIRE_WORDS)
        IGNORED_SUBS_LIST = check_setting_str(CFG, 'General', 'ignored_subs_list', IGNORED_SUBS_LIST)
        IGNORE_UND_SUBS = bool(check_setting_int(CFG, 'General', 'ignore_und_subs', IGNORE_UND_SUBS))

        CALENDAR_UNPROTECTED = bool(check_setting_int(CFG, 'General', 'calendar_unprotected', 0))
        CALENDAR_ICONS = bool(check_setting_int(CFG, 'General', 'calendar_icons', 0))

        NO_RESTART = bool(check_setting_int(CFG, 'General', 'no_restart', 0))

        EXTRA_SCRIPTS = [x.strip() for x in check_setting_str(CFG, 'General', 'extra_scripts', '').split('|') if
                         x.strip()]

        USE_LISTVIEW = bool(check_setting_int(CFG, 'General', 'use_listview', 0))

        ANIMESUPPORT = False
        USE_ANIDB = bool(check_setting_int(CFG, 'ANIDB', 'use_anidb', 0))
        ANIDB_USERNAME = check_setting_str(CFG, 'ANIDB', 'anidb_username', '', censor_log='normal')
        ANIDB_PASSWORD = check_setting_str(CFG, 'ANIDB', 'anidb_password', '', censor_log='low')
        ANIDB_USE_MYLIST = bool(check_setting_int(CFG, 'ANIDB', 'anidb_use_mylist', 0))

        ANIME_SPLIT_HOME = bool(check_setting_int(CFG, 'ANIME', 'anime_split_home', 0))

        METADATA_KODI = check_setting_str(CFG, 'General', 'metadata_kodi', '0|0|0|0|0|0|0|0|0|0')
        METADATA_KODI_12PLUS = check_setting_str(CFG, 'General', 'metadata_kodi_12plus', '0|0|0|0|0|0|0|0|0|0')
        METADATA_MEDIABROWSER = check_setting_str(CFG, 'General', 'metadata_mediabrowser', '0|0|0|0|0|0|0|0|0|0')
        METADATA_PS3 = check_setting_str(CFG, 'General', 'metadata_ps3', '0|0|0|0|0|0|0|0|0|0')
        METADATA_WDTV = check_setting_str(CFG, 'General', 'metadata_wdtv', '0|0|0|0|0|0|0|0|0|0')
        METADATA_TIVO = check_setting_str(CFG, 'General', 'metadata_tivo', '0|0|0|0|0|0|0|0|0|0')
        METADATA_MEDE8ER = check_setting_str(CFG, 'General', 'metadata_mede8er', '0|0|0|0|0|0|0|0|0|0')

        HOME_LAYOUT = check_setting_str(CFG, 'GUI', 'home_layout', 'poster')
        HISTORY_LAYOUT = check_setting_str(CFG, 'GUI', 'history_layout', 'detailed')
        HISTORY_LIMIT = check_setting_str(CFG, 'GUI', 'history_limit', '100')
        DISPLAY_SHOW_SPECIALS = bool(check_setting_int(CFG, 'GUI', 'display_show_specials', 1))
        COMING_EPS_LAYOUT = check_setting_str(CFG, 'GUI', 'coming_eps_layout', 'banner')
        COMING_EPS_DISPLAY_PAUSED = bool(check_setting_int(CFG, 'GUI', 'coming_eps_display_paused', 0))
        COMING_EPS_SORT = check_setting_str(CFG, 'GUI', 'coming_eps_sort', 'date')
        COMING_EPS_MISSED_RANGE = check_setting_int(CFG, 'GUI', 'coming_eps_missed_range', 7)
        FUZZY_DATING = bool(check_setting_int(CFG, 'GUI', 'fuzzy_dating', 0))
        TRIM_ZERO = bool(check_setting_int(CFG, 'GUI', 'trim_zero', 0))
        DATE_PRESET = check_setting_str(CFG, 'GUI', 'date_preset', '%x')
        TIME_PRESET_W_SECONDS = check_setting_str(CFG, 'GUI', 'time_preset', '%I:%M:%S %p')
        TIME_PRESET = TIME_PRESET_W_SECONDS.replace(u":%S", u"")
        TIMEZONE_DISPLAY = check_setting_str(CFG, 'GUI', 'timezone_display', 'local')
        POSTER_SORTBY = check_setting_str(CFG, 'GUI', 'poster_sortby', 'name')
        POSTER_SORTDIR = check_setting_int(CFG, 'GUI', 'poster_sortdir', 1)
        DISPLAY_ALL_SEASONS = bool(check_setting_int(CFG, 'General', 'display_all_seasons', 1))
        RECENTLY_DELETED = set()
        RELEASES_IN_PP = []
        GIT_REMOTE_BRANCHES = []
        KODI_LIBRARY_CLEAN_PENDING = False

        # reconfigure the logger
        logger.reconfigure()

        # initialize NZB and TORRENT providers
        providerList = providers.makeProviderList()

        NEWZNAB_DATA = check_setting_str(CFG, 'Newznab', 'newznab_data', '')
        newznabProviderList = NewznabProvider.get_providers_list(NEWZNAB_DATA)

        TORRENTRSS_DATA = check_setting_str(CFG, 'TorrentRss', 'torrentrss_data', '')
        torrentRssProviderList = TorrentRssProvider.get_providers_list(TORRENTRSS_DATA)

        all_providers = providers.sortedProviderList()

        # dynamically load provider settings
        for provider in all_providers:
            # use check_setting_bool to see if the provider is enabled instead of load_provider_settings
            # since the attr name does not match the default provider option style of '{provider}_{attribute}'
            provider.enabled = check_setting_bool(CFG, provider.get_id().upper(), provider.get_id(), 0)

            load_provider_setting(CFG, provider, 'string', 'username', '', censor_log='normal')
            load_provider_setting(CFG, provider, 'string', 'api_key', '', censor_log='low')
            load_provider_setting(CFG, provider, 'string', 'search_mode', 'eponly')
            load_provider_setting(CFG, provider, 'bool', 'search_fallback', 0)
            load_provider_setting(CFG, provider, 'bool', 'enable_daily', 1)
            load_provider_setting(CFG, provider, 'bool', 'enable_backlog', provider.supports_backlog)
            load_provider_setting(CFG, provider, 'bool', 'enable_manualsearch', 1)

            if provider.provider_type == GenericProvider.TORRENT:
                load_provider_setting(CFG, provider, 'string', 'custom_url', '', censor_log='low')
                load_provider_setting(CFG, provider, 'string', 'hash', '', censor_log='low')
                load_provider_setting(CFG, provider, 'string', 'digest', '', censor_log='low')
                load_provider_setting(CFG, provider, 'string', 'password', '', censor_log='low')
                load_provider_setting(CFG, provider, 'string', 'passkey', '', censor_log='low')
                load_provider_setting(CFG, provider, 'string', 'pin', '', censor_log='low')
                load_provider_setting(CFG, provider, 'string', 'sorting', 'seeders')
                load_provider_setting(CFG, provider, 'string', 'options', '')
                load_provider_setting(CFG, provider, 'string', 'ratio', '')
                load_provider_setting(CFG, provider, 'bool', 'confirmed', 1)
                load_provider_setting(CFG, provider, 'bool', 'ranked', 1)
                load_provider_setting(CFG, provider, 'bool', 'engrelease', 0)
                load_provider_setting(CFG, provider, 'bool', 'onlyspasearch', 0)
                load_provider_setting(CFG, provider, 'int', 'minseed', 1)
                load_provider_setting(CFG, provider, 'int', 'minleech', 0)
                load_provider_setting(CFG, provider, 'bool', 'freeleech', 0)
                load_provider_setting(CFG, provider, 'int', 'cat', 0)
                load_provider_setting(CFG, provider, 'bool', 'subtitle', 0)
                if provider.enable_cookies:
                    load_provider_setting(CFG, provider, 'string', 'cookies', '', censor_log='low')

        if not os.path.isfile(CONFIG_FILE):
            logger.log(u"Unable to find '" + CONFIG_FILE + "', all settings will be default!", logger.DEBUG)
            save_config()

        # initialize the main SB database
        main_db_con = db.DBConnection()
        db.upgradeDatabase(main_db_con, main_db.InitialSchema)

        # initialize the cache database
        cache_db_con = db.DBConnection('cache.db')
        db.upgradeDatabase(cache_db_con, cache_db.InitialSchema)

        # Performs a vacuum on cache.db
        logger.log(u"Performing a vacuum on the CACHE database", logger.DEBUG)
        cache_db_con.action("VACUUM")

        # initialize the failed downloads database
        failed_db_con = db.DBConnection('failed.db')
        db.upgradeDatabase(failed_db_con, failed_db.InitialSchema)

        # fix up any db problems
        main_db_con = db.DBConnection()
        db.sanityCheckDatabase(main_db_con, main_db.MainSanityCheck)

        # migrate the config if it needs it
        migrator = ConfigMigrator(CFG)
        migrator.migrate_config()

        # initialize metadata_providers
        metadata_provider_dict = metadata.get_metadata_generator_dict()
        for cur_metadata_tuple in [(METADATA_KODI, metadata.kodi),
                                   (METADATA_KODI_12PLUS, metadata.kodi_12plus),
                                   (METADATA_MEDIABROWSER, metadata.mediabrowser),
                                   (METADATA_PS3, metadata.ps3),
                                   (METADATA_WDTV, metadata.wdtv),
                                   (METADATA_TIVO, metadata.tivo),
                                   (METADATA_MEDE8ER, metadata.mede8er)]:

            (cur_metadata_config, cur_metadata_class) = cur_metadata_tuple
            tmp_provider = cur_metadata_class.metadata_class()
            tmp_provider.set_config(cur_metadata_config)
            metadata_provider_dict[tmp_provider.name] = tmp_provider

        # initialize schedulers
        # updaters
        versionCheckScheduler = scheduler.Scheduler(versionChecker.CheckVersion(),
                                                    cycleTime=datetime.timedelta(hours=UPDATE_FREQUENCY),
                                                    threadName="CHECKVERSION",
                                                    silent=False)

        showQueueScheduler = scheduler.Scheduler(show_queue.ShowQueue(),
                                                 cycleTime=datetime.timedelta(seconds=3),
                                                 threadName="SHOWQUEUE")

        showUpdateScheduler = scheduler.Scheduler(showUpdater.ShowUpdater(),
                                                  cycleTime=datetime.timedelta(hours=1),
                                                  threadName="SHOWUPDATER",
                                                  start_time=datetime.time(hour=SHOWUPDATE_HOUR, minute=random.randint(0, 59)))

        # snatcher used for manual search, manual picked results
        manualSnatchScheduler = scheduler.Scheduler(SnatchQueue(),
                                                    cycleTime=datetime.timedelta(seconds=3),
                                                    threadName="MANUALSNATCHQUEUE")
        # searchers
        searchQueueScheduler = scheduler.Scheduler(SearchQueue(),
                                                   cycleTime=datetime.timedelta(seconds=3),
                                                   threadName="SEARCHQUEUE")

        forcedSearchQueueScheduler = scheduler.Scheduler(ForcedSearchQueue(),
                                                         cycleTime=datetime.timedelta(seconds=3),
                                                         threadName="FORCEDSEARCHQUEUE")

        # TODO: update_interval should take last daily/backlog times into account!
        update_interval = datetime.timedelta(minutes=DAILYSEARCH_FREQUENCY)
        dailySearchScheduler = scheduler.Scheduler(DailySearcher(),
                                                   cycleTime=update_interval,
                                                   threadName="DAILYSEARCHER",
                                                   run_delay=update_interval)

        update_interval = datetime.timedelta(minutes=BACKLOG_FREQUENCY)
        backlogSearchScheduler = BacklogSearchScheduler(BacklogSearcher(),
                                                        cycleTime=update_interval,
                                                        threadName="BACKLOG",
                                                        run_delay=update_interval)

        search_intervals = {'15m': 15, '45m': 45, '90m': 90, '4h': 4 * 60, 'daily': 24 * 60}
        if CHECK_PROPERS_INTERVAL in search_intervals:
            update_interval = datetime.timedelta(minutes=search_intervals[CHECK_PROPERS_INTERVAL])
            run_at = None
        else:
            update_interval = datetime.timedelta(hours=1)
            run_at = datetime.time(hour=1)  # 1 AM

        properFinderScheduler = scheduler.Scheduler(ProperFinder(),
                                                    cycleTime=update_interval,
                                                    threadName="FINDPROPERS",
                                                    start_time=run_at,
                                                    run_delay=update_interval)

        # processors
        update_interval = datetime.timedelta(minutes=AUTOPOSTPROCESSOR_FREQUENCY)
        autoPostProcessorScheduler = scheduler.Scheduler(auto_postprocessor.PostProcessor(),
                                                         cycleTime=update_interval,
                                                         threadName="POSTPROCESSOR",
                                                         silent=not PROCESS_AUTOMATICALLY,
                                                         run_delay=update_interval)
        update_interval = datetime.timedelta(minutes=5)
        traktCheckerScheduler = scheduler.Scheduler(traktChecker.TraktChecker(),
                                                    cycleTime=datetime.timedelta(hours=1),
                                                    threadName="TRAKTCHECKER",
                                                    run_delay=update_interval,
                                                    silent=not USE_TRAKT)

        update_interval = datetime.timedelta(hours=SUBTITLES_FINDER_FREQUENCY)
        subtitlesFinderScheduler = scheduler.Scheduler(subtitles.SubtitlesFinder(),
                                                       cycleTime=update_interval,
                                                       threadName="FINDSUBTITLES",
                                                       run_delay=update_interval,
                                                       silent=not USE_SUBTITLES)

        __INITIALIZED__ = True
        return True


def restore_cache_folder(cache_folder):
    """Restore cache folder.

    :param cache_folder:
    :type cache_folder: string
    """
    restore_folder = os.path.join(DATA_DIR, 'restore')
    if not os.path.exists(restore_folder) or not os.path.exists(os.path.join(restore_folder, 'cache')):
        return

    try:
        def restore_cache(src_folder, dest_folder):
            def path_leaf(path):
                head, tail = os.path.split(path)
                return tail or os.path.basename(head)

            try:
                if os.path.isdir(dest_folder):
                    bak_filename = '{0}-{1}'.format(path_leaf(dest_folder), datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
                    shutil.move(dest_folder, os.path.join(os.path.dirname(dest_folder), bak_filename))

                shutil.move(src_folder, dest_folder)
                logger.log(u"Restore: restoring cache successful", logger.INFO)
            except OSError as e:
                logger.log(u"Restore: restoring cache failed: {0!r}".format(e), logger.ERROR)

        restore_cache(os.path.join(restore_folder, 'cache'), cache_folder)
    finally:
        helpers.remove_folder(restore_folder)
        for name in ('mako', 'sessions', 'indexers', 'rss'):
            folder_path = os.path.join(cache_folder, name)
            helpers.remove_folder(folder_path)


def start():
    global started  # pylint: disable=global-statement

    with INIT_LOCK:
        if __INITIALIZED__:
            # start sysetm events queue
            events.start()

            # start the daily search scheduler
            dailySearchScheduler.enable = True
            dailySearchScheduler.start()

            # start the backlog scheduler
            backlogSearchScheduler.enable = True
            backlogSearchScheduler.start()

            # start the show updater
            showUpdateScheduler.enable = True
            showUpdateScheduler.start()

            # start the version checker
            versionCheckScheduler.enable = True
            versionCheckScheduler.start()

            # start the queue checker
            showQueueScheduler.enable = True
            showQueueScheduler.start()

            # start the search queue checker
            searchQueueScheduler.enable = True
            searchQueueScheduler.start()

            # start the forced search queue checker
            forcedSearchQueueScheduler.enable = True
            forcedSearchQueueScheduler.start()

            # start the search queue checker
            manualSnatchScheduler.enable = True
            manualSnatchScheduler.start()

            # start the proper finder
            if DOWNLOAD_PROPERS:
                properFinderScheduler.silent = False
                properFinderScheduler.enable = True
            else:
                properFinderScheduler.enable = False
                properFinderScheduler.silent = True
            properFinderScheduler.start()

            # start the post processor
            if PROCESS_AUTOMATICALLY:
                autoPostProcessorScheduler.silent = False
                autoPostProcessorScheduler.enable = True
            else:
                autoPostProcessorScheduler.enable = False
                autoPostProcessorScheduler.silent = True
            autoPostProcessorScheduler.start()

            # start the subtitles finder
            if USE_SUBTITLES:
                subtitlesFinderScheduler.silent = False
                subtitlesFinderScheduler.enable = True
            else:
                subtitlesFinderScheduler.enable = False
                subtitlesFinderScheduler.silent = True
            subtitlesFinderScheduler.start()

            # start the trakt checker
            if USE_TRAKT:
                traktCheckerScheduler.silent = False
                traktCheckerScheduler.enable = True
            else:
                traktCheckerScheduler.enable = False
                traktCheckerScheduler.silent = True
            traktCheckerScheduler.start()

            started = True


def halt():
    global __INITIALIZED__, started  # pylint: disable=global-statement

    with INIT_LOCK:

        if __INITIALIZED__:

            logger.log(u"Aborting all threads")

            threads = [
                dailySearchScheduler,
                backlogSearchScheduler,
                showUpdateScheduler,
                versionCheckScheduler,
                showQueueScheduler,
                searchQueueScheduler,
                forcedSearchQueueScheduler,
                manualSnatchScheduler,
                autoPostProcessorScheduler,
                traktCheckerScheduler,
                properFinderScheduler,
                subtitlesFinderScheduler,
                events
            ]

            # set them all to stop at the same time
            for t in threads:
                t.stop.set()

            for t in threads:
                logger.log(u"Waiting for the %s thread to exit" % t.name)
                try:
                    t.join(10)
                except Exception:
                    pass

            if ADBA_CONNECTION:
                ADBA_CONNECTION.logout()
                logger.log(u"Waiting for the ANIDB CONNECTION thread to exit")
                try:
                    ADBA_CONNECTION.join(10)
                except Exception:
                    pass

            __INITIALIZED__ = False
        started = False


def sig_handler(signum=None, frame=None):
    _ = frame
    if not isinstance(signum, type(None)):
        logger.log(u"Signal %i caught, saving and exiting..." % int(signum))
        Shutdown.stop(PID)


def saveAll():
    # write all shows
    logger.log(u"Saving all shows to the database")
    for show in showList:
        show.save_to_db()

    # save config
    logger.log(u"Saving config file to disk")
    save_config()


def save_config():  # pylint: disable=too-many-statements, too-many-branches
    new_config = ConfigObj(encoding='UTF-8', default_encoding='UTF-8')
    new_config.filename = CONFIG_FILE

    # For passwords you must include the word `password` in the item_name
    # and add `helpers.encrypt(ITEM_NAME, ENCRYPTION_VERSION)` in save_config()
    new_config['General'] = {}
    new_config['General']['git_username'] = GIT_USERNAME
    new_config['General']['git_password'] = helpers.encrypt(GIT_PASSWORD, ENCRYPTION_VERSION)
    new_config['General']['git_reset'] = int(GIT_RESET)
    new_config['General']['git_reset_branches'] = ','.join(GIT_RESET_BRANCHES)
    new_config['General']['branch'] = BRANCH
    new_config['General']['git_remote'] = GIT_REMOTE
    new_config['General']['git_remote_url'] = GIT_REMOTE_URL
    new_config['General']['cur_commit_hash'] = CUR_COMMIT_HASH
    new_config['General']['cur_commit_branch'] = CUR_COMMIT_BRANCH
    new_config['General']['config_version'] = CONFIG_VERSION
    new_config['General']['encryption_version'] = int(ENCRYPTION_VERSION)
    new_config['General']['encryption_secret'] = ENCRYPTION_SECRET
    new_config['General']['log_dir'] = ACTUAL_LOG_DIR if ACTUAL_LOG_DIR else 'Logs'
    new_config['General']['log_nr'] = int(LOG_NR)
    new_config['General']['log_size'] = float(LOG_SIZE)
    new_config['General']['socket_timeout'] = SOCKET_TIMEOUT
    new_config['General']['web_port'] = WEB_PORT
    new_config['General']['web_host'] = WEB_HOST
    new_config['General']['web_ipv6'] = int(WEB_IPV6)
    new_config['General']['web_log'] = int(WEB_LOG)
    new_config['General']['web_root'] = WEB_ROOT
    new_config['General']['web_username'] = WEB_USERNAME
    new_config['General']['web_password'] = helpers.encrypt(WEB_PASSWORD, ENCRYPTION_VERSION)
    new_config['General']['web_cookie_secret'] = WEB_COOKIE_SECRET
    new_config['General']['web_use_gzip'] = int(WEB_USE_GZIP)
    new_config['General']['subliminal_log'] = int(SUBLIMINAL_LOG)
    new_config['General']['privacy_level'] = PRIVACY_LEVEL
    new_config['General']['ssl_verify'] = int(SSL_VERIFY)
    new_config['General']['download_url'] = DOWNLOAD_URL
    new_config['General']['localhost_ip'] = LOCALHOST_IP
    new_config['General']['cpu_preset'] = CPU_PRESET
    new_config['General']['anon_redirect'] = ANON_REDIRECT
    new_config['General']['api_key'] = API_KEY
    new_config['General']['debug'] = int(DEBUG)
    new_config['General']['dbdebug'] = int(DBDEBUG)
    new_config['General']['default_page'] = DEFAULT_PAGE
    new_config['General']['seeders_leechers_in_notify'] = int(SEEDERS_LEECHERS_IN_NOTIFY)
    new_config['General']['enable_https'] = int(ENABLE_HTTPS)
    new_config['General']['notify_on_login'] = int(NOTIFY_ON_LOGIN)
    new_config['General']['https_cert'] = HTTPS_CERT
    new_config['General']['https_key'] = HTTPS_KEY
    new_config['General']['handle_reverse_proxy'] = int(HANDLE_REVERSE_PROXY)
    new_config['General']['use_nzbs'] = int(USE_NZBS)
    new_config['General']['use_torrents'] = int(USE_TORRENTS)
    new_config['General']['nzb_method'] = NZB_METHOD
    new_config['General']['torrent_method'] = TORRENT_METHOD
    new_config['General']['usenet_retention'] = int(USENET_RETENTION)
    new_config['General']['cache_trimming'] = int(CACHE_TRIMMING)
    new_config['General']['max_cache_age'] = int(MAX_CACHE_AGE)
    new_config['General']['autopostprocessor_frequency'] = int(AUTOPOSTPROCESSOR_FREQUENCY)
    new_config['General']['dailysearch_frequency'] = int(DAILYSEARCH_FREQUENCY)
    new_config['General']['backlog_frequency'] = int(BACKLOG_FREQUENCY)
    new_config['General']['update_frequency'] = int(UPDATE_FREQUENCY)
    new_config['General']['showupdate_hour'] = int(SHOWUPDATE_HOUR)
    new_config['General']['download_propers'] = int(DOWNLOAD_PROPERS)
    new_config['General']['randomize_providers'] = int(RANDOMIZE_PROVIDERS)
    new_config['General']['check_propers_interval'] = CHECK_PROPERS_INTERVAL
    new_config['General']['allow_high_priority'] = int(ALLOW_HIGH_PRIORITY)
    new_config['General']['skip_removed_files'] = int(SKIP_REMOVED_FILES)
    new_config['General']['allowed_extensions'] = ALLOWED_EXTENSIONS
    new_config['General']['quality_default'] = int(QUALITY_DEFAULT)
    new_config['General']['status_default'] = int(STATUS_DEFAULT)
    new_config['General']['status_default_after'] = int(STATUS_DEFAULT_AFTER)
    new_config['General']['flatten_folders_default'] = int(FLATTEN_FOLDERS_DEFAULT)
    new_config['General']['indexer_default'] = int(INDEXER_DEFAULT)
    new_config['General']['indexer_timeout'] = int(INDEXER_TIMEOUT)
    new_config['General']['anime_default'] = int(ANIME_DEFAULT)
    new_config['General']['scene_default'] = int(SCENE_DEFAULT)
    new_config['General']['provider_order'] = ' '.join(PROVIDER_ORDER)
    new_config['General']['version_notify'] = int(VERSION_NOTIFY)
    new_config['General']['auto_update'] = int(AUTO_UPDATE)
    new_config['General']['notify_on_update'] = int(NOTIFY_ON_UPDATE)
    new_config['General']['naming_strip_year'] = int(NAMING_STRIP_YEAR)
    new_config['General']['naming_pattern'] = NAMING_PATTERN
    new_config['General']['naming_custom_abd'] = int(NAMING_CUSTOM_ABD)
    new_config['General']['naming_abd_pattern'] = NAMING_ABD_PATTERN
    new_config['General']['naming_custom_sports'] = int(NAMING_CUSTOM_SPORTS)
    new_config['General']['naming_sports_pattern'] = NAMING_SPORTS_PATTERN
    new_config['General']['naming_custom_anime'] = int(NAMING_CUSTOM_ANIME)
    new_config['General']['naming_anime_pattern'] = NAMING_ANIME_PATTERN
    new_config['General']['naming_multi_ep'] = int(NAMING_MULTI_EP)
    new_config['General']['naming_anime_multi_ep'] = int(NAMING_ANIME_MULTI_EP)
    new_config['General']['naming_anime'] = int(NAMING_ANIME)
    new_config['General']['indexerDefaultLang'] = INDEXER_DEFAULT_LANGUAGE
    new_config['General']['ep_default_deleted_status'] = int(EP_DEFAULT_DELETED_STATUS)
    new_config['General']['launch_browser'] = int(LAUNCH_BROWSER)
    new_config['General']['trash_remove_show'] = int(TRASH_REMOVE_SHOW)
    new_config['General']['trash_rotate_logs'] = int(TRASH_ROTATE_LOGS)
    new_config['General']['sort_article'] = int(SORT_ARTICLE)
    new_config['General']['proxy_setting'] = PROXY_SETTING
    new_config['General']['proxy_indexers'] = int(PROXY_INDEXERS)

    new_config['General']['use_listview'] = int(USE_LISTVIEW)
    new_config['General']['metadata_kodi'] = METADATA_KODI
    new_config['General']['metadata_kodi_12plus'] = METADATA_KODI_12PLUS
    new_config['General']['metadata_mediabrowser'] = METADATA_MEDIABROWSER
    new_config['General']['metadata_ps3'] = METADATA_PS3
    new_config['General']['metadata_wdtv'] = METADATA_WDTV
    new_config['General']['metadata_tivo'] = METADATA_TIVO
    new_config['General']['metadata_mede8er'] = METADATA_MEDE8ER

    new_config['General']['backlog_days'] = int(BACKLOG_DAYS)

    new_config['General']['cache_dir'] = ACTUAL_CACHE_DIR if ACTUAL_CACHE_DIR else 'cache'
    new_config['General']['root_dirs'] = ROOT_DIRS if ROOT_DIRS else ''
    new_config['General']['tv_download_dir'] = TV_DOWNLOAD_DIR
    new_config['General']['keep_processed_dir'] = int(KEEP_PROCESSED_DIR)
    new_config['General']['process_method'] = PROCESS_METHOD
    new_config['General']['del_rar_contents'] = int(DELRARCONTENTS)
    new_config['General']['move_associated_files'] = int(MOVE_ASSOCIATED_FILES)
    new_config['General']['sync_files'] = SYNC_FILES
    new_config['General']['postpone_if_sync_files'] = int(POSTPONE_IF_SYNC_FILES)
    new_config['General']['postpone_if_no_subs'] = int(POSTPONE_IF_NO_SUBS)
    new_config['General']['nfo_rename'] = int(NFO_RENAME)
    new_config['General']['process_automatically'] = int(PROCESS_AUTOMATICALLY)
    new_config['General']['no_delete'] = int(NO_DELETE)
    new_config['General']['unpack'] = int(UNPACK)
    new_config['General']['rename_episodes'] = int(RENAME_EPISODES)
    new_config['General']['airdate_episodes'] = int(AIRDATE_EPISODES)
    new_config['General']['file_timestamp_timezone'] = FILE_TIMESTAMP_TIMEZONE
    new_config['General']['create_missing_show_dirs'] = int(CREATE_MISSING_SHOW_DIRS)
    new_config['General']['add_shows_wo_dir'] = int(ADD_SHOWS_WO_DIR)

    new_config['General']['extra_scripts'] = '|'.join(EXTRA_SCRIPTS)
    new_config['General']['git_path'] = GIT_PATH
    new_config['General']['ignore_words'] = IGNORE_WORDS
    new_config['General']['preferred_words'] = PREFERRED_WORDS
    new_config['General']['undesired_words'] = UNDESIRED_WORDS
    new_config['General']['trackers_list'] = TRACKERS_LIST
    new_config['General']['require_words'] = REQUIRE_WORDS
    new_config['General']['ignored_subs_list'] = IGNORED_SUBS_LIST
    new_config['General']['ignore_und_subs'] = IGNORE_UND_SUBS
    new_config['General']['calendar_unprotected'] = int(CALENDAR_UNPROTECTED)
    new_config['General']['calendar_icons'] = int(CALENDAR_ICONS)
    new_config['General']['no_restart'] = int(NO_RESTART)
    new_config['General']['developer'] = int(DEVELOPER)
    new_config['General']['display_all_seasons'] = int(DISPLAY_ALL_SEASONS)
    new_config['General']['news_last_read'] = NEWS_LAST_READ
    new_config['General']['broken_providers'] = ','.join(helpers.get_broken_providers()) or BROKEN_PROVIDERS

    new_config['Blackhole'] = {}
    new_config['Blackhole']['nzb_dir'] = NZB_DIR
    new_config['Blackhole']['torrent_dir'] = TORRENT_DIR

    # dynamically save provider settings
    all_providers = providers.sortedProviderList()
    for provider in all_providers:
        name = provider.get_id()
        section = name.upper()

        new_config[section] = {}
        new_config[section][name] = int(provider.enabled)

        attributes = {
            'all': [
                'api_key', 'username',
                'search_mode', 'search_fallback',
                'enable_daily', 'enable_backlog', 'enable_manualsearch',
            ],
            'encrypted': [
                'password',
            ],
            GenericProvider.TORRENT: [
                'custom_url', 'digest', 'hash', 'passkey', 'pin', 'confirmed', 'ranked', 'engrelease', 'onlyspasearch',
                'sorting', 'ratio', 'minseed', 'minleech', 'options', 'freelech', 'cat', 'subtitle', 'cookies',
            ],
            GenericProvider.NZB: [
            ],
        }

        for attr in attributes['all']:
            save_provider_setting(new_config, provider, attr)

        for attr in attributes['encrypted']:
            # encrypt the attribute value first before storing
            encrypted_attribute = helpers.encrypt(getattr(provider, attr, ''), ENCRYPTION_VERSION)
            save_provider_setting(new_config, provider, attr, value=encrypted_attribute)

        for provider_type in [GenericProvider.NZB, GenericProvider.TORRENT]:
            if provider_type == provider.provider_type:
                for attr in attributes[provider_type]:
                    save_provider_setting(new_config, provider, attr)

    new_config['NZBs'] = {}
    new_config['NZBs']['nzbs'] = int(NZBS)
    new_config['NZBs']['nzbs_uid'] = NZBS_UID
    new_config['NZBs']['nzbs_hash'] = NZBS_HASH

    new_config['Newzbin'] = {}
    new_config['Newzbin']['newzbin'] = int(NEWZBIN)
    new_config['Newzbin']['newzbin_username'] = NEWZBIN_USERNAME
    new_config['Newzbin']['newzbin_password'] = helpers.encrypt(NEWZBIN_PASSWORD, ENCRYPTION_VERSION)

    new_config['SABnzbd'] = {}
    new_config['SABnzbd']['sab_username'] = SAB_USERNAME
    new_config['SABnzbd']['sab_password'] = helpers.encrypt(SAB_PASSWORD, ENCRYPTION_VERSION)
    new_config['SABnzbd']['sab_apikey'] = SAB_APIKEY
    new_config['SABnzbd']['sab_category'] = SAB_CATEGORY
    new_config['SABnzbd']['sab_category_backlog'] = SAB_CATEGORY_BACKLOG
    new_config['SABnzbd']['sab_category_anime'] = SAB_CATEGORY_ANIME
    new_config['SABnzbd']['sab_category_anime_backlog'] = SAB_CATEGORY_ANIME_BACKLOG
    new_config['SABnzbd']['sab_host'] = SAB_HOST
    new_config['SABnzbd']['sab_forced'] = int(SAB_FORCED)

    new_config['NZBget'] = {}

    new_config['NZBget']['nzbget_username'] = NZBGET_USERNAME
    new_config['NZBget']['nzbget_password'] = helpers.encrypt(NZBGET_PASSWORD, ENCRYPTION_VERSION)
    new_config['NZBget']['nzbget_category'] = NZBGET_CATEGORY
    new_config['NZBget']['nzbget_category_backlog'] = NZBGET_CATEGORY_BACKLOG
    new_config['NZBget']['nzbget_category_anime'] = NZBGET_CATEGORY_ANIME
    new_config['NZBget']['nzbget_category_anime_backlog'] = NZBGET_CATEGORY_ANIME_BACKLOG
    new_config['NZBget']['nzbget_host'] = NZBGET_HOST
    new_config['NZBget']['nzbget_use_https'] = int(NZBGET_USE_HTTPS)
    new_config['NZBget']['nzbget_priority'] = NZBGET_PRIORITY

    new_config['TORRENT'] = {}
    new_config['TORRENT']['torrent_username'] = TORRENT_USERNAME
    new_config['TORRENT']['torrent_password'] = helpers.encrypt(TORRENT_PASSWORD, ENCRYPTION_VERSION)
    new_config['TORRENT']['torrent_host'] = TORRENT_HOST
    new_config['TORRENT']['torrent_path'] = TORRENT_PATH
    new_config['TORRENT']['torrent_seed_time'] = int(TORRENT_SEED_TIME)
    new_config['TORRENT']['torrent_paused'] = int(TORRENT_PAUSED)
    new_config['TORRENT']['torrent_high_bandwidth'] = int(TORRENT_HIGH_BANDWIDTH)
    new_config['TORRENT']['torrent_label'] = TORRENT_LABEL
    new_config['TORRENT']['torrent_label_anime'] = TORRENT_LABEL_ANIME
    new_config['TORRENT']['torrent_verify_cert'] = int(TORRENT_VERIFY_CERT)
    new_config['TORRENT']['torrent_rpcurl'] = TORRENT_RPCURL
    new_config['TORRENT']['torrent_auth_type'] = TORRENT_AUTH_TYPE

    new_config['KODI'] = {}
    new_config['KODI']['use_kodi'] = int(USE_KODI)
    new_config['KODI']['kodi_always_on'] = int(KODI_ALWAYS_ON)
    new_config['KODI']['kodi_notify_onsnatch'] = int(KODI_NOTIFY_ONSNATCH)
    new_config['KODI']['kodi_notify_ondownload'] = int(KODI_NOTIFY_ONDOWNLOAD)
    new_config['KODI']['kodi_notify_onsubtitledownload'] = int(KODI_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['KODI']['kodi_update_library'] = int(KODI_UPDATE_LIBRARY)
    new_config['KODI']['kodi_update_full'] = int(KODI_UPDATE_FULL)
    new_config['KODI']['kodi_update_onlyfirst'] = int(KODI_UPDATE_ONLYFIRST)
    new_config['KODI']['kodi_host'] = KODI_HOST
    new_config['KODI']['kodi_username'] = KODI_USERNAME
    new_config['KODI']['kodi_password'] = helpers.encrypt(KODI_PASSWORD, ENCRYPTION_VERSION)
    new_config['KODI']['kodi_clean_library'] = int(KODI_CLEAN_LIBRARY)

    new_config['Plex'] = {}
    new_config['Plex']['use_plex_server'] = int(USE_PLEX_SERVER)
    new_config['Plex']['plex_notify_onsnatch'] = int(PLEX_NOTIFY_ONSNATCH)
    new_config['Plex']['plex_notify_ondownload'] = int(PLEX_NOTIFY_ONDOWNLOAD)
    new_config['Plex']['plex_notify_onsubtitledownload'] = int(PLEX_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['Plex']['plex_update_library'] = int(PLEX_UPDATE_LIBRARY)
    new_config['Plex']['plex_server_host'] = PLEX_SERVER_HOST
    new_config['Plex']['plex_server_token'] = PLEX_SERVER_TOKEN
    new_config['Plex']['plex_client_host'] = PLEX_CLIENT_HOST
    new_config['Plex']['plex_server_username'] = PLEX_SERVER_USERNAME
    new_config['Plex']['plex_server_password'] = helpers.encrypt(PLEX_SERVER_PASSWORD, ENCRYPTION_VERSION)

    new_config['Plex']['use_plex_client'] = int(USE_PLEX_CLIENT)
    new_config['Plex']['plex_client_username'] = PLEX_CLIENT_USERNAME
    new_config['Plex']['plex_client_password'] = helpers.encrypt(PLEX_CLIENT_PASSWORD, ENCRYPTION_VERSION)
    new_config['Plex']['plex_server_https'] = int(PLEX_SERVER_HTTPS)

    new_config['Emby'] = {}
    new_config['Emby']['use_emby'] = int(USE_EMBY)
    new_config['Emby']['emby_host'] = EMBY_HOST
    new_config['Emby']['emby_apikey'] = EMBY_APIKEY

    new_config['Growl'] = {}
    new_config['Growl']['use_growl'] = int(USE_GROWL)
    new_config['Growl']['growl_notify_onsnatch'] = int(GROWL_NOTIFY_ONSNATCH)
    new_config['Growl']['growl_notify_ondownload'] = int(GROWL_NOTIFY_ONDOWNLOAD)
    new_config['Growl']['growl_notify_onsubtitledownload'] = int(GROWL_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['Growl']['growl_host'] = GROWL_HOST
    new_config['Growl']['growl_password'] = helpers.encrypt(GROWL_PASSWORD, ENCRYPTION_VERSION)

    new_config['FreeMobile'] = {}
    new_config['FreeMobile']['use_freemobile'] = int(USE_FREEMOBILE)
    new_config['FreeMobile']['freemobile_notify_onsnatch'] = int(FREEMOBILE_NOTIFY_ONSNATCH)
    new_config['FreeMobile']['freemobile_notify_ondownload'] = int(FREEMOBILE_NOTIFY_ONDOWNLOAD)
    new_config['FreeMobile']['freemobile_notify_onsubtitledownload'] = int(FREEMOBILE_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['FreeMobile']['freemobile_id'] = FREEMOBILE_ID
    new_config['FreeMobile']['freemobile_apikey'] = FREEMOBILE_APIKEY

    new_config['Telegram'] = {}
    new_config['Telegram']['use_telegram'] = int(USE_TELEGRAM)
    new_config['Telegram']['telegram_notify_onsnatch'] = int(TELEGRAM_NOTIFY_ONSNATCH)
    new_config['Telegram']['telegram_notify_ondownload'] = int(TELEGRAM_NOTIFY_ONDOWNLOAD)
    new_config['Telegram']['telegram_notify_onsubtitledownload'] = int(TELEGRAM_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['Telegram']['telegram_id'] = TELEGRAM_ID
    new_config['Telegram']['telegram_apikey'] = TELEGRAM_APIKEY

    new_config['Prowl'] = {}
    new_config['Prowl']['use_prowl'] = int(USE_PROWL)
    new_config['Prowl']['prowl_notify_onsnatch'] = int(PROWL_NOTIFY_ONSNATCH)
    new_config['Prowl']['prowl_notify_ondownload'] = int(PROWL_NOTIFY_ONDOWNLOAD)
    new_config['Prowl']['prowl_notify_onsubtitledownload'] = int(PROWL_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['Prowl']['prowl_api'] = PROWL_API
    new_config['Prowl']['prowl_priority'] = PROWL_PRIORITY
    new_config['Prowl']['prowl_message_title'] = PROWL_MESSAGE_TITLE

    new_config['Twitter'] = {}
    new_config['Twitter']['use_twitter'] = int(USE_TWITTER)
    new_config['Twitter']['twitter_notify_onsnatch'] = int(TWITTER_NOTIFY_ONSNATCH)
    new_config['Twitter']['twitter_notify_ondownload'] = int(TWITTER_NOTIFY_ONDOWNLOAD)
    new_config['Twitter']['twitter_notify_onsubtitledownload'] = int(TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['Twitter']['twitter_username'] = TWITTER_USERNAME
    new_config['Twitter']['twitter_password'] = helpers.encrypt(TWITTER_PASSWORD, ENCRYPTION_VERSION)
    new_config['Twitter']['twitter_prefix'] = TWITTER_PREFIX
    new_config['Twitter']['twitter_dmto'] = TWITTER_DMTO
    new_config['Twitter']['twitter_usedm'] = int(TWITTER_USEDM)

    new_config['Boxcar2'] = {}
    new_config['Boxcar2']['use_boxcar2'] = int(USE_BOXCAR2)
    new_config['Boxcar2']['boxcar2_notify_onsnatch'] = int(BOXCAR2_NOTIFY_ONSNATCH)
    new_config['Boxcar2']['boxcar2_notify_ondownload'] = int(BOXCAR2_NOTIFY_ONDOWNLOAD)
    new_config['Boxcar2']['boxcar2_notify_onsubtitledownload'] = int(BOXCAR2_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['Boxcar2']['boxcar2_accesstoken'] = BOXCAR2_ACCESSTOKEN

    new_config['Pushover'] = {}
    new_config['Pushover']['use_pushover'] = int(USE_PUSHOVER)
    new_config['Pushover']['pushover_notify_onsnatch'] = int(PUSHOVER_NOTIFY_ONSNATCH)
    new_config['Pushover']['pushover_notify_ondownload'] = int(PUSHOVER_NOTIFY_ONDOWNLOAD)
    new_config['Pushover']['pushover_notify_onsubtitledownload'] = int(PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['Pushover']['pushover_userkey'] = PUSHOVER_USERKEY
    new_config['Pushover']['pushover_apikey'] = PUSHOVER_APIKEY
    new_config['Pushover']['pushover_device'] = PUSHOVER_DEVICE
    new_config['Pushover']['pushover_sound'] = PUSHOVER_SOUND

    new_config['Libnotify'] = {}
    new_config['Libnotify']['use_libnotify'] = int(USE_LIBNOTIFY)
    new_config['Libnotify']['libnotify_notify_onsnatch'] = int(LIBNOTIFY_NOTIFY_ONSNATCH)
    new_config['Libnotify']['libnotify_notify_ondownload'] = int(LIBNOTIFY_NOTIFY_ONDOWNLOAD)
    new_config['Libnotify']['libnotify_notify_onsubtitledownload'] = int(LIBNOTIFY_NOTIFY_ONSUBTITLEDOWNLOAD)

    new_config['NMJ'] = {}
    new_config['NMJ']['use_nmj'] = int(USE_NMJ)
    new_config['NMJ']['nmj_host'] = NMJ_HOST
    new_config['NMJ']['nmj_database'] = NMJ_DATABASE
    new_config['NMJ']['nmj_mount'] = NMJ_MOUNT

    new_config['NMJv2'] = {}
    new_config['NMJv2']['use_nmjv2'] = int(USE_NMJv2)
    new_config['NMJv2']['nmjv2_host'] = NMJv2_HOST
    new_config['NMJv2']['nmjv2_database'] = NMJv2_DATABASE
    new_config['NMJv2']['nmjv2_dbloc'] = NMJv2_DBLOC

    new_config['Synology'] = {}
    new_config['Synology']['use_synoindex'] = int(USE_SYNOINDEX)

    new_config['SynologyNotifier'] = {}
    new_config['SynologyNotifier']['use_synologynotifier'] = int(USE_SYNOLOGYNOTIFIER)
    new_config['SynologyNotifier']['synologynotifier_notify_onsnatch'] = int(SYNOLOGYNOTIFIER_NOTIFY_ONSNATCH)
    new_config['SynologyNotifier']['synologynotifier_notify_ondownload'] = int(SYNOLOGYNOTIFIER_NOTIFY_ONDOWNLOAD)
    new_config['SynologyNotifier']['synologynotifier_notify_onsubtitledownload'] = int(
        SYNOLOGYNOTIFIER_NOTIFY_ONSUBTITLEDOWNLOAD)

    new_config['Trakt'] = {}
    new_config['Trakt']['use_trakt'] = int(USE_TRAKT)
    new_config['Trakt']['trakt_username'] = TRAKT_USERNAME
    new_config['Trakt']['trakt_access_token'] = TRAKT_ACCESS_TOKEN
    new_config['Trakt']['trakt_refresh_token'] = TRAKT_REFRESH_TOKEN
    new_config['Trakt']['trakt_remove_watchlist'] = int(TRAKT_REMOVE_WATCHLIST)
    new_config['Trakt']['trakt_remove_serieslist'] = int(TRAKT_REMOVE_SERIESLIST)
    new_config['Trakt']['trakt_remove_show_from_application'] = int(TRAKT_REMOVE_SHOW_FROM_APPLICATION)
    new_config['Trakt']['trakt_sync_watchlist'] = int(TRAKT_SYNC_WATCHLIST)
    new_config['Trakt']['trakt_method_add'] = int(TRAKT_METHOD_ADD)
    new_config['Trakt']['trakt_start_paused'] = int(TRAKT_START_PAUSED)
    new_config['Trakt']['trakt_use_recommended'] = int(TRAKT_USE_RECOMMENDED)
    new_config['Trakt']['trakt_sync'] = int(TRAKT_SYNC)
    new_config['Trakt']['trakt_sync_remove'] = int(TRAKT_SYNC_REMOVE)
    new_config['Trakt']['trakt_default_indexer'] = int(TRAKT_DEFAULT_INDEXER)
    new_config['Trakt']['trakt_timeout'] = int(TRAKT_TIMEOUT)
    new_config['Trakt']['trakt_blacklist_name'] = TRAKT_BLACKLIST_NAME

    new_config['pyTivo'] = {}
    new_config['pyTivo']['use_pytivo'] = int(USE_PYTIVO)
    new_config['pyTivo']['pytivo_notify_onsnatch'] = int(PYTIVO_NOTIFY_ONSNATCH)
    new_config['pyTivo']['pytivo_notify_ondownload'] = int(PYTIVO_NOTIFY_ONDOWNLOAD)
    new_config['pyTivo']['pytivo_notify_onsubtitledownload'] = int(PYTIVO_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['pyTivo']['pyTivo_update_library'] = int(PYTIVO_UPDATE_LIBRARY)
    new_config['pyTivo']['pytivo_host'] = PYTIVO_HOST
    new_config['pyTivo']['pytivo_share_name'] = PYTIVO_SHARE_NAME
    new_config['pyTivo']['pytivo_tivo_name'] = PYTIVO_TIVO_NAME

    new_config['NMA'] = {}
    new_config['NMA']['use_nma'] = int(USE_NMA)
    new_config['NMA']['nma_notify_onsnatch'] = int(NMA_NOTIFY_ONSNATCH)
    new_config['NMA']['nma_notify_ondownload'] = int(NMA_NOTIFY_ONDOWNLOAD)
    new_config['NMA']['nma_notify_onsubtitledownload'] = int(NMA_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['NMA']['nma_api'] = NMA_API
    new_config['NMA']['nma_priority'] = NMA_PRIORITY

    new_config['Pushalot'] = {}
    new_config['Pushalot']['use_pushalot'] = int(USE_PUSHALOT)
    new_config['Pushalot']['pushalot_notify_onsnatch'] = int(PUSHALOT_NOTIFY_ONSNATCH)
    new_config['Pushalot']['pushalot_notify_ondownload'] = int(PUSHALOT_NOTIFY_ONDOWNLOAD)
    new_config['Pushalot']['pushalot_notify_onsubtitledownload'] = int(PUSHALOT_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['Pushalot']['pushalot_authorizationtoken'] = PUSHALOT_AUTHORIZATIONTOKEN

    new_config['Pushbullet'] = {}
    new_config['Pushbullet']['use_pushbullet'] = int(USE_PUSHBULLET)
    new_config['Pushbullet']['pushbullet_notify_onsnatch'] = int(PUSHBULLET_NOTIFY_ONSNATCH)
    new_config['Pushbullet']['pushbullet_notify_ondownload'] = int(PUSHBULLET_NOTIFY_ONDOWNLOAD)
    new_config['Pushbullet']['pushbullet_notify_onsubtitledownload'] = int(PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['Pushbullet']['pushbullet_api'] = PUSHBULLET_API
    new_config['Pushbullet']['pushbullet_device'] = PUSHBULLET_DEVICE

    new_config['Email'] = {}
    new_config['Email']['use_email'] = int(USE_EMAIL)
    new_config['Email']['email_notify_onsnatch'] = int(EMAIL_NOTIFY_ONSNATCH)
    new_config['Email']['email_notify_ondownload'] = int(EMAIL_NOTIFY_ONDOWNLOAD)
    new_config['Email']['email_notify_onsubtitledownload'] = int(EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD)
    new_config['Email']['email_host'] = EMAIL_HOST
    new_config['Email']['email_port'] = int(EMAIL_PORT)
    new_config['Email']['email_tls'] = int(EMAIL_TLS)
    new_config['Email']['email_user'] = EMAIL_USER
    new_config['Email']['email_password'] = helpers.encrypt(EMAIL_PASSWORD, ENCRYPTION_VERSION)
    new_config['Email']['email_from'] = EMAIL_FROM
    new_config['Email']['email_list'] = EMAIL_LIST
    new_config['Email']['email_subject'] = EMAIL_SUBJECT

    new_config['Newznab'] = {}
    new_config['Newznab']['newznab_data'] = NEWZNAB_DATA

    new_config['TorrentRss'] = {}
    new_config['TorrentRss']['torrentrss_data'] = '!!!'.join([x.config_string() for x in torrentRssProviderList])

    new_config['GUI'] = {}
    new_config['GUI']['theme_name'] = THEME_NAME
    new_config['GUI']['fanart_background'] = FANART_BACKGROUND
    new_config['GUI']['fanart_background_opacity'] = FANART_BACKGROUND_OPACITY
    new_config['GUI']['home_layout'] = HOME_LAYOUT
    new_config['GUI']['history_layout'] = HISTORY_LAYOUT
    new_config['GUI']['history_limit'] = HISTORY_LIMIT
    new_config['GUI']['display_show_specials'] = int(DISPLAY_SHOW_SPECIALS)
    new_config['GUI']['coming_eps_layout'] = COMING_EPS_LAYOUT
    new_config['GUI']['coming_eps_display_paused'] = int(COMING_EPS_DISPLAY_PAUSED)
    new_config['GUI']['coming_eps_sort'] = COMING_EPS_SORT
    new_config['GUI']['coming_eps_missed_range'] = int(COMING_EPS_MISSED_RANGE)
    new_config['GUI']['fuzzy_dating'] = int(FUZZY_DATING)
    new_config['GUI']['trim_zero'] = int(TRIM_ZERO)
    new_config['GUI']['date_preset'] = DATE_PRESET
    new_config['GUI']['time_preset'] = TIME_PRESET_W_SECONDS
    new_config['GUI']['timezone_display'] = TIMEZONE_DISPLAY
    new_config['GUI']['poster_sortby'] = POSTER_SORTBY
    new_config['GUI']['poster_sortdir'] = POSTER_SORTDIR

    new_config['Subtitles'] = {}
    new_config['Subtitles']['use_subtitles'] = int(USE_SUBTITLES)
    new_config['Subtitles']['subtitles_languages'] = ','.join(SUBTITLES_LANGUAGES)
    new_config['Subtitles']['SUBTITLES_SERVICES_LIST'] = ','.join(SUBTITLES_SERVICES_LIST)
    new_config['Subtitles']['SUBTITLES_SERVICES_ENABLED'] = '|'.join([str(x) for x in SUBTITLES_SERVICES_ENABLED])
    new_config['Subtitles']['subtitles_dir'] = SUBTITLES_DIR
    new_config['Subtitles']['subtitles_default'] = int(SUBTITLES_DEFAULT)
    new_config['Subtitles']['subtitles_history'] = int(SUBTITLES_HISTORY)
    new_config['Subtitles']['subtitles_perfect_match'] = int(SUBTITLES_PERFECT_MATCH)
    new_config['Subtitles']['embedded_subtitles_all'] = int(EMBEDDED_SUBTITLES_ALL)
    new_config['Subtitles']['subtitles_stop_at_first'] = int(SUBTITLES_STOP_AT_FIRST)
    new_config['Subtitles']['embedded_subtitles_unknown_lang'] = int(EMBEDDED_SUBTITLES_UNKNOWN_LANG)
    new_config['Subtitles']['subtitles_hearing_impaired'] = int(SUBTITLES_HEARING_IMPAIRED)
    new_config['Subtitles']['subtitles_finder_frequency'] = int(SUBTITLES_FINDER_FREQUENCY)
    new_config['Subtitles']['subtitles_multi'] = int(SUBTITLES_MULTI)
    new_config['Subtitles']['subtitles_extra_scripts'] = '|'.join(SUBTITLES_EXTRA_SCRIPTS)
    new_config['Subtitles']['subtitles_pre_scripts'] = '|'.join(SUBTITLES_PRE_SCRIPTS)
    new_config['Subtitles']['subtitles_keep_only_wanted'] = int(SUBTITLES_KEEP_ONLY_WANTED)
    new_config['Subtitles']['addic7ed_username'] = ADDIC7ED_USER
    new_config['Subtitles']['addic7ed_password'] = helpers.encrypt(ADDIC7ED_PASS, ENCRYPTION_VERSION)

    new_config['Subtitles']['itasa_username'] = ITASA_USER
    new_config['Subtitles']['itasa_password'] = helpers.encrypt(ITASA_PASS, ENCRYPTION_VERSION)

    new_config['Subtitles']['legendastv_username'] = LEGENDASTV_USER
    new_config['Subtitles']['legendastv_password'] = helpers.encrypt(LEGENDASTV_PASS, ENCRYPTION_VERSION)

    new_config['Subtitles']['opensubtitles_username'] = OPENSUBTITLES_USER
    new_config['Subtitles']['opensubtitles_password'] = helpers.encrypt(OPENSUBTITLES_PASS, ENCRYPTION_VERSION)

    new_config['FailedDownloads'] = {}
    new_config['FailedDownloads']['use_failed_downloads'] = int(USE_FAILED_DOWNLOADS)
    new_config['FailedDownloads']['delete_failed'] = int(DELETE_FAILED)

    new_config['ANIDB'] = {}
    new_config['ANIDB']['use_anidb'] = int(USE_ANIDB)
    new_config['ANIDB']['anidb_username'] = ANIDB_USERNAME
    new_config['ANIDB']['anidb_password'] = helpers.encrypt(ANIDB_PASSWORD, ENCRYPTION_VERSION)
    new_config['ANIDB']['anidb_use_mylist'] = int(ANIDB_USE_MYLIST)

    new_config['ANIME'] = {}
    new_config['ANIME']['anime_split_home'] = int(ANIME_SPLIT_HOME)

    new_config.write()


def launchBrowser(protocol='http', startPort=None, web_root='/'):

    try:
        import webbrowser
    except ImportError:
        logger.log(u"Unable to load the webbrowser module, cannot launch the browser.", logger.WARNING)
        return

    if not startPort:
        startPort = WEB_PORT

    browser_url = '%s://localhost:%d%s/home/' % (protocol, startPort, web_root)

    try:
        webbrowser.open(browser_url, 2, 1)
    except Exception:
        try:
            webbrowser.open(browser_url, 1, 1)
        except Exception:
            logger.log(u"Unable to launch a browser", logger.ERROR)
