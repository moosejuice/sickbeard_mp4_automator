#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

"""Simple-to-use Python interface to The TVDB's API (www.thetvdb.com)

Example usage:

>>> from tvdb_api import Tvdb
>>> db = Tvdb()
>>> db['Lost'][4][11]['episodename']
u'Cabin Fever'
"""
__author__ = "dbr/Ben"
__version__ = "0.6dev"

from elementtree import ElementTree

from tvdb_ui import BaseUI, ConsoleUI
from tvdb_exceptions import (tvdb_error, tvdb_userabort, tvdb_shownotfound,
    tvdb_seasonnotfound, tvdb_episodenotfound, tvdb_attributenotfound)

class Cache:
    """Simple caching URL opener. Acts like:
    import urllib
    return urllib.urlopen("http://example.com").read()

    Caches complete files to temp directory,

    >>> ca = Cache()
    >>> ca.loadUrl("http://example.com") #doctest: +ELLIPSIS
    '<HTML>...'
    """
    import os
    import sys
    import time
    import tempfile
    import urllib
    try:
        from hashlib import sha1 as hasher
    except ImportError:
        from sha import sha as hasher

    def __init__(self, max_age=21600, prefix="tvdb_api"):
        self.prefix = prefix
        self.max_age = max_age

        tmp = self.tempfile.gettempdir()
        tmppath = self.os.path.join(tmp, prefix)
        if not self.os.path.isdir(tmppath):
            self.os.mkdir(tmppath)
        self.tmp = tmppath
    #end __init__

    def getCachePath(self, url):
        """Calculates the cache path (/temp_directory/hash_of_URL)
        """
        cache_name = self.hasher(url).hexdigest()
        cache_path = self.os.path.join(self.tmp, cache_name)
        return cache_path
    #end getUrl

    def checkCache(self, url):
        """Takes a URL, checks if a cache exists for it.
        If so, returns path, if not, returns False
        """
        path = self.getCachePath(url)
        if self.os.path.isfile(path):
            cache_modified_time = self.os.stat(path).st_mtime
            time_now = self.time.time()
            if cache_modified_time < time_now - self.max_age:
                # Cache is old
                return False
            else:
                return path
        else:
            return False
    #end checkCache

    def loadUrl(self, url):
        """Takes a URL, returns the contents of the URL, and does the caching.
        """
        cacheExists = self.checkCache(url)
        if cacheExists:
            cache_file = open(cacheExists)
            dat = cache_file.read()
            cache_file.close()
            return dat
        else:
            path = self.getCachePath(url)
            dat = self.urllib.urlopen(url).read()
            try:
                target_socket = open(path, "w+")
                target_socket.write(dat)
                target_socket.close()
            except IOError, errormsg:
                sys.stderr.write(
                    "WARNING: Cannot write to cache file (%s): %s\n" % (path, errormsg)
                )
            return dat
        #end if cacheExists
    #end loadUrl
#end Cache

def can_int(x):
    """Takes a string, checks if it is numeric.
    >>> can_int("2")
    True
    >>> can_int("A test")
    False
    """
    try:
        int(x)
    except ValueError:
        return False
    else:
        return True


# Custom exceptions

class ShowContainer(dict):
    """Simple dict that holds a series of Show instancies
    """
    pass

class Show(dict):
    """Holds a dict of seasons, and show data.
    """
    def __init__(self):
        self.data = {}
    
    def __repr__(self):
        return "<Show %s (containing %s seasons)>" % (
            self.data.get(u'seriesname', 'instance'),
            len(self)
        )
    def __getitem__(self, key):
        if key in self:
            # Key is an episode, return it
            return dict.__getitem__(self, key)
        
        if key in self.data:
            # Non-numeric request is for show-data
            return dict.__getitem__(self.data, key)

        # Data wasn't found, raise appropriate error
        if can_int(key):
            # Episode number x was not found
            raise tvdb_seasonnotfound("Could not find season %s" % (key))
        else:
            # If it's not numeric, it must be an attribute name, which
            # doesn't exist, so attribute error.
            raise tvdb_attributenotfound("Cannot find attribute %s" % (key))

    def search(self, term = None, key = None):
        """
        Search all episodes in show. Can search all data, or a specific key (for
        example, episodename)
        
        Always returns an array (can be empty). First index is first
        found episode, and so on.
        
        Each array index is an Episode() instance, so doing
        search_results[0]['episodename'] will retrive the episode name of the
        first match.
        
        Search terms are convered to lower case unicode strings.

        Examples
        These examples assume t is an instance of Tvdb():
        >>> t = Tvdb()
        >>>

        Search for all episodes of Scrubs episodes
        with a bit of data containg "my first day":

        >>> t['Scrubs'].search("my first day") #doctest: +ELLIPSIS
        [<Episode 01x01 - My First Day>]
        >>>

        Search for "My Name Is Earl" named "Faked His Own Death":

        >>> t['My Name Is Earl'].search('Faked His Own Death', key = 'episodename') #doctest: +ELLIPSIS
        [<Episode 01x04 - Faked His Own Death>]
        >>>
        
        To search Scrubs for all episodes with "mentor" in the episode name:
        
        >>> t['scrubs'].search('mentor', key = 'episodename')
        [<Episode 01x02 - My Mentor>, <Episode 03x15 - My Tormented Mentor>]
        >>>

        Using search results

        >>> results = t['Scrubs'].search("my first")
        >>> print results[0]['episodename']
        My First Day
        >>> for x in results: print x['episodename']
        My First Day
        My First Step
        My First Kill
        >>>
        """
        results = []
        for cur_season in self.values():
            searchresult = cur_season.search(term = term, key = key)
            if len(searchresult) != 0:
                results.extend(searchresult)
        #end for cur_season
        return results

class Season(dict):
    def __repr__(self):
        return "<Season instance (containing %s episodes)>" % (
            len(self.keys())
        )
    def __getitem__(self, episode_number):
        if episode_number not in self:
            raise tvdb_episodenotfound
        else:
            return dict.__getitem__(self, episode_number)
    
    def search(self, term = None, key = None):
        """Search a all episodes in season, returns a list of matching Episode 
        instances.
        
        >>> t = Tvdb()
        >>> t['scrubs'][1].search('first day')
        [<Episode 01x01 - My First Day>]
        >>>
        
        See Episode.search documentation for further information on search
        """
        results = []
        for ep in self.values():
            searchresult = ep.search(term = term, key = key)
            if searchresult is not None:
                results.append(
                    searchresult
                )
        return results

class Episode(dict):
    def __repr__(self):
        seasno = int(self.get(u'seasonnumber', 0))
        epno = int(self.get(u'episodenumber', 0))
        epname = self.get(u'episodename')
        if epname is not None:
            return "<Episode %02dx%02d - %s>" % (seasno, epno, epname)
        else:
            return "<Episode %02dx%02d>" % (seasno, epno)
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            raise tvdb_attributenotfound("Cannot find attribute %s" % (key))
    def search(self, term = None, key = None):
        """Search episodes data for term, if it matches, return the Episode.
        The key parameter can be used to limit the search to a specific element.
        for example, episodename
        
        Simple example:
        
        >>> e = Episode()
        >>> e['episodename'] = "An Example"
        >>> e.search("examp")
        <Episode 00x00 - An Example>
        >>>
        
        Limiting by key:
        
        >>> e.search("examp", key = "episodename")
        <Episode 00x00 - An Example>
        >>>
        """
        if term == None:
            raise TypeError("must supply string to search for (contents)")
        
        term = unicode(term).lower()
        for cur_key, cur_value in self.items():
            cur_key, cur_value = unicode(cur_key).lower(), unicode(cur_value).lower()
            if key is not None and cur_key != key:
                # Do not search this key
                continue
            if cur_value.find( unicode(term).lower() ) > -1:
                return self
            #end if cur_value.find()
        #end for cur_key, cur_value
        

class Tvdb:
    """Create easy-to-use interface to name of season/episode name
    >>> t = Tvdb()
    >>> t['Scrubs'][1][24]['episodename']
    u'My Last Day'
    """
    import urllib
    from BeautifulSoup import BeautifulStoneSoup

    def __init__(self, interactive = False,
                select_first = True,
                debug = False,
                cache = True,
                banners = False,
                custom_ui = None):
        """interactive:
        When True, uses built-in console UI is used to select
        the correct show.
        When False, the first search result is used.
        
        select_first (True/False):
        Automatically selects the first series search result (rather
        than showing the user a list of more than one series).
        Is overridden by interactive = False, or specifying a custom_ui
        
        debug (True/False):
         shows verbose debugging information
        
        cache (True/False):
        Retrived XML are persisted to to disc (under the TEMP_DIR/tvdb_api)
        
        banners (True/False):
        Retrives the banners for a show. These are accessed 
        via the _banners key of a Show(), for example:
        
        >>> Tvdb(banners=True)['scrubs']['_banners'].keys()
        [u'fanart', u'poster', u'series', u'season']
        
        custom_ui (tvdb_ui.BaseUI subclass):
        A callable subclass of tvdb_ui.BaseUI (overrides interactive)
        """
        self.shows = ShowContainer() # Holds all Show classes
        self.corrections = {} # Holds show-name to show_id mapping

        self.config = {}

        self.config['apikey'] = "0629B785CE550C8D" # thetvdb.com API key

        self.config['debug_enabled'] = debug # show debugging messages

        self.config['custom_ui'] = custom_ui

        self.config['interactive'] = interactive # prompt for correct series?
        
        self.config['select_first'] = select_first
        
        self.config['cache_enabled'] = cache
        
        self.config['banners_enabled'] = banners

        if self.config['cache_enabled']:
            self.cache = Cache(prefix="tvdb_api") # Caches retreived URLs in tmp dir
        
        self.log = self._initLogger() # Setups the logger (self.log.debug() etc)

        # The following url_ configs are based of the
        # http://thetvdb.com/wiki/index.php/Programmers_API
        self.config['base_url'] = "http://www.thetvdb.com"

        self.config['url_getSeries'] = "%(base_url)s/api/GetSeries.php?seriesname=%%s" % self.config
        self.config['url_epInfo'] = "%(base_url)s/api/%(apikey)s/series/%%s/all/" % self.config

        self.config['url_seriesInfo'] = "%(base_url)s/api/%(apikey)s/series/%%s/" % self.config
        self.config['url_seriesBanner'] = "%(base_url)s/api/%(apikey)s/series/%%s/banners.xml" % self.config
        self.config['url_bannerPath'] = "%(base_url)s/banners/%%s" % self.config

    #end __init__

    def _initLogger(self):
        """Setups a logger using the logging module, returns a log object
        """
        import logging, sys
        logger = logging.getLogger("tvdb")
        formatter = logging.Formatter('%(asctime)s) %(levelname)s %(message)s')

        hdlr = logging.StreamHandler(sys.stdout)

        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)

        if self.config['debug_enabled']:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.WARNING)
        return logger
    #end initLogger

    def _getsoupsrc(self, url):
        """Helper to get a URL, turn it into
        a BeautifulStoneSoup instance (for XML parsing)
        """
        url = url.replace(" ", "+")
        try:
            if self.config['cache_enabled']:
                self.log.debug("Getting %s using Cache (cache location %s)" % (url, self.cache.tmp))
                src = self.cache.loadUrl(url)
            else:
                self.log.debug("Getting %s with no caching" % (url))
                src = self.urllib.urlopen(url).read()
        except IOError, errormsg:
            raise tvdb_error("Could not connect to server: %s" % (errormsg))
        #end try
        soup = self.BeautifulStoneSoup(src)
        return soup
    #end _getsoupsrc

    def _getetsrc(self, url):
        url = url.replace(" ", "+")
        try:
            if self.config['cache_enabled']:
                self.log.debug("Getting %s using Cache (cache location %s)" % (url, self.cache.tmp))
                src = self.cache.loadUrl(url)
            else:
                self.log.debug("Getting %s with no caching" % (url))
                src = self.urllib.urlopen(url).read()
        except IOError, errormsg:
            raise tvdb_error("Could not connect to server: %s" % (errormsg))
        #end try
        et = ElementTree.fromstring(src)
        return et
#end _getetsrc


    def _setItem(self, sid, seas, ep, attrib, value):
        """Creates a new episode, creating Show(), Season() and
        Episode()s as required. Called by _getShowData to populute

        Since the nice-to-use tvdb[1][24]['name] interface
        makes it impossible to do tvdb[1][24]['name] = "name"
        and still be capable of checking if an episode exists
        so we can raise tvdb_shownotfound, we have a slightly
        less pretty method of setting items.. but since the API
        is supposed to be read-only, this is the best way to
        do it!
        The problem is that calling tvdb[1][24]['episodename'] = "name"
        calls __getitem__ on tvdb[1], there is no way to check if
        tvdb.__dict__ should have a key "1" before we auto-create it
        """
        if sid not in self.shows:
            self.shows[sid] = Show()
        if seas not in self.shows[sid]: 
            self.shows[sid][seas] = Season()
        if ep not in self.shows[sid][seas]:
            self.shows[sid][seas][ep] = Episode()
        self.shows[sid][seas][ep][attrib] = value
    #end _set_item

    def _setShowData(self, sid, key, value):
        if sid not in self.shows:
            self.shows[sid] = Show()
        self.shows[sid].data.__setitem__(key, value)

    def _cleanData(self, data):
        """Cleans up strings returned by TheTVDB.com

        Issues corrected:
        - Returns &amp; instead of &, since &s in filenames
        are bad, replace &amp; with "and"
        """
        data = data.replace(u"&amp;", u"and")
        data = data.strip()
        return data
    #end _cleanData

    def _getSeries(self, series):
        """This searches TheTVDB.com for the series name,
        and either interactivly selects the correct show,
        or returns the first result.
        """
        seriesEt = self._getetsrc(self.config['url_getSeries'] % (series))
        allSeries = []
        for series in seriesEt:
            sn = series.find('SeriesName')
            tag = sn.tag.lower()
            value = self._cleanData(sn.text)
            cur_sid = series.find('id').text
            self.log.debug('Found series %s (id: %s)' % (value, cur_sid))
            allSeries.append( {'sid':cur_sid, 'name':tag} )
        #end for series

        if len(allSeries) == 0:
            self.log.debug('Series result returned zero')
            raise tvdb_shownotfound("Show-name search returned zero results (cannot find show on TVDB)")
        
        if self.config['custom_ui'] is not None:
            self.log.debug("Using custom UI %s" % (repr(self.config['custom_ui'])))
            ui = self.config['custom_ui'](config = self.config, log = self.log)
        else:
            if not self.config['interactive']:
                self.log.debug('Auto-selecting first search result using BaseUI')
                ui = BaseUI(config = self.config, log = self.log)
            else:
                self.log.debug('Interactivily selecting show using ConsoleUI')
                ui = ConsoleUI(config = self.config, log = self.log)
            #end if config['interactive]
        #end if custom_ui != None
        
        return ui.selectSeries(allSeries)
            
    #end _getSeries

    def _getShowData(self, sid):
        """Takes a series ID, gets the epInfo URL and parses the TVDB
        XML file into the shows dict in layout:
        shows[series_id][season_number][episode_number]
        """
        
        # Parse show information
        self.log.debug('Getting all series data for %s' % (sid))
        seriesInfoEt = self._getetsrc(self.config['url_seriesInfo'] % (sid))
        for curInfo in seriesInfoEt.findall("Series")[0]:
            tag = curInfo.tag.lower()
            value = curInfo.text
            self._setShowData(sid, tag, value)
            self.log.debug(
                "Got info: %s = %s" % (tag, value)
            )
        #end for series
        
        # Parse banners
        if self.config['banners_enabled']:
            self.log.debug('Getting season banners for %s' % (sid))
            bannersSoup = self._getsoupsrc( self.config['url_seriesBanner'] % (sid) )    
            banners = {}
            for cur_banner in bannersSoup.findAll('banner'):
                bid = cur_banner.id.string
                btype = cur_banner.bannertype.string
                btype2 = cur_banner.bannertype2.string
                if not btype in banners:
                    banners[btype] = {}
                if not btype2 in banners[btype]:
                    banners[btype][btype2] = {}
                if not bid in banners[btype][btype2]:
                    banners[btype][btype2][bid] = {}
            
                self.log.debug("Banner: %s", bid)
                for cur_element in cur_banner.findChildren():
                    self.log.debug("Banner info: %s = %s" % (cur_element.name, cur_element.string))
                    banners[btype][btype2][bid][cur_element.name] = cur_element.string
            
                for k, v in banners[btype][btype2][bid].items():
                    if k.endswith("path"):
                        new_key = "_%s" % (k)
                        new_url = self.config['url_bannerPath'] % (v)
                        banners[btype][btype2][bid][new_key] = new_url

            self._setShowData(sid, "_banners", banners)

        # Parse episode data
        self.log.debug('Getting all episodes of %s' % (sid))
        epsSoup = self._getsoupsrc( self.config['url_epInfo'] % (sid) )

        for cur_ep in epsSoup.findAll('episode'):
            # We need the season and episode numbers to store the other data
            ep_no = int( cur_ep.find('episodenumber').contents[0] )
            seas_no = int( cur_ep.find('seasonnumber').contents[0] )

            # Iterate over the data within each episode
            for cur_attr in cur_ep.findChildren():
                if len(cur_attr.contents) > 0:
                    clean_attr = self._cleanData(cur_attr.contents[0])
                    self._setItem(sid, seas_no, ep_no, cur_attr.name, clean_attr)
        #end for cur_ep
    #end _geEps

    def _nameToSid(self, name):
        """Takes show name, returns the correct series ID (if the show has
        already been grabbed), or grabs all episodes and returns
        the correct SID.
        """
        if name in self.corrections:
            self.log.debug('Correcting %s to %s' % (name, self.corrections[name]) )
            sid = self.corrections[name]
        else:
            self.log.debug('Getting show %s' % (name))
            selected_series = self._getSeries( name )
            sname, sid = selected_series['name'], selected_series['sid']
            self.log.debug('Got %s, sid %s' % (sname, sid) )

            self.corrections[name] = sid
            self._getShowData( sid )
        #end if name in self.corrections
        return sid
    #end _nameToSid

    def __getitem__(self, key):
        """Handles tvdb_instance['seriesname'] calls.
        The dict index should be the show id
        """
        key = key.lower() # make key lower case
        sid = self._nameToSid(key)
        self.log.debug('Got series id %s' % (sid))
        return self.shows[sid]
    #end __getitem__

    def __str__(self):
        return str(self.shows)
    #end __str__
#end Tvdb

def simple_example():
    """Simple example of using tvdb_api - it just
    grabs an episode name interactivly.
    """
    tvdb_instance = Tvdb(interactive=True, debug=True, cache=False)
    print tvdb_instance['Lost']['seriesname']
    print tvdb_instance['Lost'][1][4]['episodename']

def main():
    """Runs simple example of tvdb_api functionailty
    """
    simple_example()


if __name__ == '__main__':
    main()
