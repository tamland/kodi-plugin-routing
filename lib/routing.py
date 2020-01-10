# -*- coding: utf-8 -*-

# Copyright: (c) 2014-2015, Thomas Amland
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function, unicode_literals

import re
import sys
try:  # Python 3
    from urllib.parse import parse_qs, urlencode, urlsplit
except ImportError:  # Python 2
    from urllib import urlencode
    from urlparse import parse_qs, urlsplit

try:
    from xbmc import LOGDEBUG, xlog
    from xbmcaddon import Addon
    ADDON_ID = Addon().getAddonInfo('id')

    def log(msg):
        msg = '[%s][routing] %s' % (ADDON_ID, msg)
        xlog(msg, level=LOGDEBUG)
except ImportError:
    ADDON_ID = 'plugin.foo.bar'
    def log(msg):
        print('[routing] %s' % msg)


class RoutingError(Exception):
    pass


class Plugin:
    """
    :ivar handle: The plugin handle from kodi
    :type handle: int

    :ivar path: The current path
    :type path: byte string

    :ivar args: The parsed query string.
    :type args: dict of byte strings
    """

    def __init__(self, base_url=None):
        self._rules = {}  # function to list of rules
        if sys.argv:
            self.path = urlsplit(sys.argv[0]).path or '/'
        else:
            self.path = '/'
        if len(sys.argv) > 1 and sys.argv[1].isdigit():
            self.handle = int(sys.argv[1])
        else:
            self.handle = -1
        self.args = {}
        self.base_url = base_url
        self.addon_id = ADDON_ID
        if self.base_url is None:
            self.base_url = 'plugin://{0}'.format(ADDON_ID)

    def route_for(self, path):
        """
        Returns the view function for path.

        :type path: byte string.
        """
        if path.startswith(self.base_url):
            path = path.split(self.base_url, 1)[1]

        for view_fun, rules in iter(list(self._rules.items())):
            for rule in rules:
                if rule.match(path) is not None:
                    return view_fun
        return None

    def url_for(self, func, *args, **kwargs):
        """
        Construct and returns an URL for view function with give arguments.
        """
        if func in self._rules:
            for rule in self._rules[func]:
                path = rule.make_path(*args, **kwargs)
                if path is not None:
                    return self.url_for_path(path)
        raise RoutingError("No known paths to '{0}' with args {1} and "
                           "kwargs {2}".format(func.__name__, args, kwargs))

    def url_for_path(self, path):
        """
        Returns the complete URL for a path.
        """
        path = path if path.startswith('/') else '/' + path
        return self.base_url + path

    def route(self, pattern):
        """ Register a route. """
        def decorator(func):
            self.add_route(func, pattern)
            return func
        return decorator

    def add_route(self, func, pattern):
        """ Register a route. """
        rule = UrlRule(pattern)
        if func not in self._rules:
            self._rules[func] = []
        self._rules[func].append(rule)

    def run(self, argv=None):
        if argv is None:
            argv = sys.argv
        self.path = urlsplit(argv[0]).path
        self.path = self.path.rstrip('/')
        if len(argv) > 2:
            self.args = parse_qs(argv[2].lstrip('?'))
        self._dispatch(self.path)

    def redirect(self, path):
        self._dispatch(path)

    def _dispatch(self, path):
        for view_func, rules in iter(list(self._rules.items())):
            for rule in rules:
                kwargs = rule.match(path)
                if kwargs is not None:
                    log("Dispatching to '%s', args: %s" % (view_func.__name__, kwargs))
                    view_func(**kwargs)
                    return
        raise RoutingError('No route to path "%s"' % path)


class UrlRule:

    def __init__(self, pattern):
        pattern = pattern.rstrip('/')
        kw_pattern = r'<(?:[^:]+:)?([A-z]+)>'
        self._pattern = re.sub(kw_pattern, '{\\1}', pattern)
        self._keywords = re.findall(kw_pattern, pattern)

        p = re.sub('<([A-z]+)>', '<string:\\1>', pattern)
        p = re.sub('<string:([A-z]+)>', '(?P<\\1>[^/]+?)', p)
        p = re.sub('<path:([A-z]+)>', '(?P<\\1>.*)', p)
        self._compiled_pattern = p
        self._regex = re.compile('^' + p + '$')

    def match(self, path):
        """
        Check if path matches this rule. Returns a dictionary of the extracted
        arguments if match, otherwise None.
        """
        # match = self._regex.search(urlsplit(path).path)
        match = self._regex.search(path)
        return match.groupdict() if match else None

    def make_path(self, *args, **kwargs):
        """Construct a path from arguments."""
        if args and kwargs:
            return None  # can't use both args and kwargs
        if args:
            # Replace the named groups %s and format
            try:
                return re.sub(r'{[A-z]+}', r'%s', self._pattern) % args
            except TypeError:
                return None

        # We need to find the keys from kwargs that occur in our pattern.
        # Unknown keys are pushed to the query string.
        url_kwargs = dict(((k, v) for k, v in list(kwargs.items()) if k in self._keywords))
        qs_kwargs = dict(((k, v) for k, v in list(kwargs.items()) if k not in self._keywords))

        query = '?' + urlencode(qs_kwargs) if qs_kwargs else ''
        try:
            return self._pattern.format(**url_kwargs) + query
        except KeyError:
            return None

    def __str__(self):
        return b"Rule(pattern=%s, keywords=%s)" % (self._pattern, self._keywords)
