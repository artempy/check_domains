import logging
import re
import pycurl
from user_agent import generate_user_agent


RE_XML_DECLARATION =\
    re.compile(br'^[^<]{,100}<\?xml[^>]+\?>', re.I)
RE_DECLARATION_ENCODING =\
    re.compile(br'encoding\s*=\s*["\']([^"\']+)["\']')
RE_META_CHARSET =\
    re.compile(br'<meta[^>]+content\s*=\s*[^>]+charset=([-\w]+)', re.I)
RE_META_CHARSET_HTML5 =\
    re.compile(br'<meta[^>]+charset\s*=\s*[\'"]?([-\w]+)', re.I)

logger = logging.getLogger('Curl')


class Net(object):
    """
    This class is designed for obtaining network data
    type_proxy - Type proxy using by default is socks5
    Can specify follow proxies: socks5, socks4, socks4a, http, https
    Auto referer using by default
    """
    def __init__(self, config, proxy=None, type_proxy=None,
                 not_use_proxy=False):
        self.response_body_chunks = []
        self.response_header_chunks = []
        self.config = config
        self.curl = pycurl.Curl()
        self.set_headers()
        self.settings()
        self.referer = None
        self.effective_url = ''
        if self.config['usecookies']:
            self.set_cookies()
        if not not_use_proxy and proxy:
            self.set_proxy(proxy, type_proxy=type_proxy)

    def body_processor(self, chunk):
        self.response_body_chunks.append(chunk)
        return None

    def header_processor(self, chunk):
        self.response_header_chunks.append(chunk)
        return None

    def set_headers(self, headers=None):
        self.useragent = generate_user_agent()
        self.set_user_agent()
        if headers:
            self.curl.setopt(pycurl.HTTPHEADER, headers)

    def prepare_response(self):
        """
        Preparing response. That's including find encodind inside
        a body page or inside the server response-header.
        After, method execution decode the page
        """
        charset = None
        self.response_body_chunks = b''.join(self.response_body_chunks)
        body_chunk = self.response_body_chunks
        headers = self.response_header_chunks
        if body_chunk:
            """Try to extract charset from http-equiv meta tag"""
            match_charset = RE_META_CHARSET.search(body_chunk)
            if match_charset:
                charset = match_charset.group(1)
            else:
                match_charset_html5 = RE_META_CHARSET_HTML5.search(body_chunk)
                if match_charset_html5:
                    charset = match_charset_html5.group(1)
            """Try to find encoding in xml"""
            if not charset:
                if body_chunk.startswith(b'<?xml'):
                    match = RE_XML_DECLARATION.search(body_chunk)
                    if match:
                        enc_match = RE_DECLARATION_ENCODING.search(
                            match.group(0))
                        if enc_match:
                            charset = enc_match.group(1)
            """Try to find encoding in headers' server inside Content-Type"""
            if not charset:
                if 'Content-Type' in headers:
                    pos = headers['Content-Type'].find('charset=')
                    if pos > -1:
                        charset = headers['Content-Type'][(pos + 8):]
                    else:
                        charset = "utf-8"
                else:
                    logger.debug('Not found charset\'s document at url: %s.', self.effective_url)
                    charset = "utf-8"

            if charset:
                charset = charset.lower()
                if not isinstance(charset, str):
                    charset = charset.decode('utf-8')

                try:
                    self.response_body_chunks = body_chunk.decode(charset)
                except UnicodeDecodeError:
                    logger.debug('UnicodeDecodeError: Not found charset\'s document at url: %s', self.effective_url)
                    self.response_body_chunks = ''

    def set_cookies(self, cookie=None, cookiefile='cookies.txt'):
        self.curl.setopt(pycurl.COOKIEFILE, cookiefile)
        self.curl.setopt(pycurl.COOKIEJAR, cookiefile)

    def set_user_agent(self, useragent=None):
        self.useragent = useragent if useragent else self.useragent
        self.curl.setopt(pycurl.USERAGENT, self.useragent)

    def settings(self, timeout=None, connect_timeout=None):
        if not connect_timeout:
            connect_timeout = self.config['connecttimeout']
        if not timeout:
            timeout = self.config['timeout']
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.MAXREDIRS, self.config['maxredirs'])
        self.curl.setopt(pycurl.ENCODING, '')
        self.curl.setopt(pycurl.CONNECTTIMEOUT, connect_timeout)
        self.curl.setopt(pycurl.TIMEOUT, timeout)
        self.curl.setopt(pycurl.SSL_VERIFYHOST, 0)
        self.curl.setopt(pycurl.SSL_VERIFYPEER, 0)
        self.curl.setopt(pycurl.VERBOSE, self.config['debug'])

    def set_referer(self, referer=None):
        myref = referer if referer else self.referer
        if myref is not None:
            self.curl.setopt(pycurl.REFERER, myref)

    def curl_type_proxy(self, type_proxy):
        if type_proxy == "socks5":
            return pycurl.PROXYTYPE_SOCKS5
        elif type_proxy == "socks4":
            return pycurl.PROXYTYPE_SOCKS4
        elif type_proxy == "socks4a":
            return pycurl.PROXYTYPE_SOCKS4A
        elif type_proxy == "https":
            return pycurl.PROXYTYPE_HTTPS
        else:
            return pycurl.PROXYTYPE_HTTP

    def set_proxy(self, proxy, type_proxy=None):
        """
        Proxy set by manual
        """
        if not type_proxy:
            type_proxy = self.config['typeproxy']
        if proxy:
            self.curl.setopt(pycurl.PROXYTYPE,
                             self.curl_type_proxy(type_proxy))
            self.proxy = proxy
            self.curl.setopt(pycurl.PROXY, self.proxy)
            logger.info('Used proxy %s of type: %s', self.proxy, type_proxy)

    def get_content(self, url, not_use_autoref=False, referer=None,
                    method="GET", postfields=None, proxy=None):
        """
        Getting data. You can specify referer
        """
        page = None
        self.response_body_chunks = []
        self.response_header_chunks = []
        logger.info('Connected to %s', url)
        if not not_use_autoref:
            self.set_referer(referer)
            logger.info('Used referer: %s', referer)
        if method == 'POST' and postfields:
            self.curl.setopt(pycurl.POST, 1)
            self.curl.setopt(pycurl.POSTFIELDS, postfields)
            logger.info('Used method: "POST"')
        else:
            self.curl.setopt(pycurl.HTTPGET, 1)
            logger.info('Used method: "GET"')
        logger.info('Used UserAgent: %s', self.useragent)
        self.curl.setopt(pycurl.URL, url)
        self.curl.setopt(pycurl.NOSIGNAL, 1)
        self.curl.setopt(pycurl.HEADERFUNCTION, self.header_processor)
        self.curl.setopt(pycurl.WRITEFUNCTION, self.body_processor)
        try:
            self.curl.perform()
            self.effective_url = effective_url = self.curl.getinfo(pycurl.EFFECTIVE_URL)
            self.prepare_response()
            page = self.response_body_chunks
            logger.info('Current url after execution request: %s',
                        effective_url)
            if self.config['autoreferer'] and not not_use_autoref:
                self.referer = effective_url
        except pycurl.error as error:
            errstr = error.args[1]
            useproxy = self.proxy if self.proxy else "not used"
            logger.error('Error get page from %s; Error: %s; Proxy: %s',
                         url, errstr, useproxy)
            return page
        return page
