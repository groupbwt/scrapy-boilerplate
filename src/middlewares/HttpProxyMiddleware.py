from w3lib.http import basic_auth_header


class HttpProxyMiddleware(object):
    def process_request(self, request, spider):
        proxy = spider.settings.get('PROXY')
        proxy_auth = spider.settings.get('PROXY_AUTH')
        if proxy is not None and len(proxy):
            if proxy_auth is not None:
                request.headers['Proxy-Authorization'] = basic_auth_header(*proxy_auth.split(':'))
            request.meta['proxy'] = "http://{}".format(proxy)
