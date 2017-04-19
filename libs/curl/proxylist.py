import logging
import queue
from random import shuffle
from threading import RLock
from time import time, sleep
from libs.curl.net import Net


logger = logging.getLogger('ProxyList')


class ProxyList(object):
    def __init__(self, config):
        self.lock = RLock()
        self.config = config
        self.proxies = queue.Queue()
        self.url = self.config['listproxiesurl']
        self.filename = self.config['listproxiesfile']
        self.proxylist = []
        self.thistime = 0

    def get_proxies_from_file(self):
        try:
            with open(self.filename, 'r') as f:
                proxies = f.readlines()
        except IOError:
            logger.error('Failed to open file that name is %s', self.filename)
            return False
        if len(proxies) > 0:
            proxies = [x.strip() for x in proxies if x]
            self.proxylist = proxies
            return True
        else:
            return False

    def get_proxies_from_url(self):
        try:
            page = Net(self.config)
            proxies = page.get_content(self.url).replace("\r", "").split("\n")
            proxies = [x for x in proxies if x]
            self.proxylist = proxies
            return True
        except Exception:
            logger.error('Failed to get proxy from %s', self.url)
            return False

    def check_proxy(self, proxy):
        request = Net(self.config, proxy=proxy)
        page = request.get_content(self.config['urlforcheckproxy'])
        if page and \
                self.config['searchwordcheckproxy'].lower() in page.lower():
            return True
        else:
            return False

    def get_proxies(self):
        n_attempt = 0
        while not self.proxylist and \
                n_attempt < self.config['numattemptloadproxies']:
            if self.url:
                self.get_proxies_from_url()
            elif self.filename:
                self.get_proxies_from_file()
            if len(self.proxylist) > 0:
                break
            sleep(self.config['sleepattemptloadproxies'])
            n_attempt += 1
            logger.info('Attempt get a proxies: %s', n_attempt)
        if self.proxylist:
            return self.proxylist
        else:
            logger.info('Don\'t fetch list of proxy!')
            raise ValueError("Don't fetch list of proxy!")

    def update_proxylist(self, url=None, filename=None):
        self.proxies = queue.Queue()
        proxies = self.get_proxies()
        shuffle(proxies)
        if len(proxies) < 1:
            logger.error('Can\'t get a list of proxy')
            return False
        else:
            for proxy in proxies:
                self.proxies.put(proxy)
            self.thistime = int(round(time()))
            return True

    def choice_proxy(self):
        if not int(self.config['useproxy']):
            return None
        self.lock.acquire()
        try:
            mtime = int(round(time())) - self.thistime
            if mtime > self.config['periodproxyupdate']:
                logger.info('Period\'s been expired for list proxy. Update...')
                self.update_proxylist()
            return self.proxies.get_nowait()
        except queue.Empty:
            logger.info('Proxy list is empty. Run update proxy list now')
            self.update_proxylist()
            return self.proxies.get_nowait()
        finally:
            self.lock.release()

    def get_proxy(self):
        result = False
        n_attempt = 0
        while n_attempt < self.config['numattemptcheckproxy']:
            proxy = self.choice_proxy()
            if self.config['checkproxy'] and proxy:
                result = self.check_proxy(proxy)
                if result:
                    break
            else:
                break
            n_attempt += 1
        return proxy
