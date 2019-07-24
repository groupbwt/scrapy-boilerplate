# -*- coding: utf-8 -*-
import os

from dotenv import load_dotenv


load_dotenv()

BOT_NAME = "YOUR_PROJECT_NAME"

SPIDER_MODULES = ["spiders"]
NEWSPIDER_MODULE = "spiders"
COMMANDS_MODULE = "commands"

PROXY = os.getenv("PROXY")
PROXY_AUTH = os.getenv("PROXY_AUTH")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"

ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = os.getenv("CONCURRENT_REQUESTS")
CONCURRENT_REQUESTS_PER_DOMAIN = os.getenv("CONCURRENT_REQUESTS_PER_DOMAIN")
DOWNLOAD_DELAY = os.getenv("DOWNLOAD_DELAY")
DOWNLOAD_TIMEOUT = os.getenv("DOWNLOAD_TIMEOUT")

# HTTPERROR_ALLOWED_CODES = [404, 405, 407, 429, 456, 503]
HTTPERROR_ALLOW_ALL = True

# COOKIES_ENABLED = False

TELNETCONSOLE_ENABLED = False
TELNETCONSOLE_PASSWORD = "password"

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    # Upgrade-Insecure-Requests: 1
    "Cache-Control": "max-age=0",
}

# SPIDER_MIDDLEWARES = {}

DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware": None,
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "middlewares.HttpProxyMiddleware": 543,
    "middlewares.LogErrorsMiddleware": 550,
}

LOG_LEVEL = os.getenv("LOG_LEVEL")

# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

ITEM_PIPELINES = {}

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASS = os.getenv("MYSQL_PASS")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_DB = os.getenv("MYSQL_DB")

PIKA_LOG_LEVEL = os.getenv("PIKA_LOG_LEVEL")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT")
RABBITMQ_VIRTUAL_HOST = os.getenv("RABBITMQ_VIRTUAL_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS")
