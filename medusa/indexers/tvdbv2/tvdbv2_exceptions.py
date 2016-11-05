# coding=utf-8
# Author: p0psicles
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

"""Custom exceptions used or raised by tvdbv2_api."""

__author__ = "p0psicles"
__version__ = "1.0"

__all__ = ["Tvdb2Error", "Tvdb2UserAbort", "Tvdb2ShowNotFound", "Tvdb2ShowIncomplete",
           "Tvdb2SeasonNotFound", "Tvdb2EpisodeNotFound", "Tvdb2AttributeNotFound"]


class Tvdb2Exception(Exception):
    """Any exception generated by Tvdb2Api."""


class Tvdb2Error(Tvdb2Exception):
    """An error with thetvdb.com (Cannot connect, for example)."""


class Tvdb2UserAbort(Tvdb2Exception):
    """User aborted the interactive selection (via the q command, ^c etc)."""


class Tvdb2ShowNotFound(Tvdb2Exception):
    """Show cannot be found on thetvdb.com (non-existant show)."""


class Tvdb2ShowNotFound(Tvdb2Exception):
    """Show cannot be found on thetvdb.com (non-existant show)."""


class Tvdb2ShowIncomplete(Tvdb2Exception):
    """Show found but incomplete on thetvdb.com (incomplete show)."""


class Tvdb2SeasonNotFound(Tvdb2Exception):
    """Season cannot be found on thetvdb.com."""


class Tvdb2EpisodeNotFound(Tvdb2Exception):
    """Episode cannot be found on thetvdb.com."""


class Tvdb2AttributeNotFound(Tvdb2Exception):
    """Raised if an episode does not have the requested attribute (such as a episode name)."""
