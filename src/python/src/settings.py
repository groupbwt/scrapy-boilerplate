# -*- coding: utf-8 -*-
import logging
import os
from datetime import datetime, timedelta
from distutils.util import strtobool
from typing import Dict

from dotenv import load_dotenv
from scrapy.utils.log import configure_logging

load_dotenv()

BOT_NAME = "YOUR_PROJECT_NAME"

SPIDER_MODULES = ["spiders"]
NEWSPIDER_MODULE = "spiders"
COMMANDS_MODULE = "commands"

PROXY = os.getenv("PROXY", "")
PROXY_AUTH = os.getenv("PROXY_AUTH", "")
PROXY_ENABLED = strtobool(os.getenv("PROXY_ENABLED", "False"))

USER_AGENT_RELEASE_DATE = '2021-11-01'
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36"

CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", "16"))
CONCURRENT_REQUESTS_PER_DOMAIN = int(os.getenv("CONCURRENT_REQUESTS_PER_DOMAIN", "8"))
DOWNLOAD_DELAY = int(os.getenv("DOWNLOAD_DELAY", "0"))
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "180"))

TELNETCONSOLE_ENABLED = False
TELNETCONSOLE_PASSWORD = "password"

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "Accept-Language": "en-US,en;q=0.5",
    "Cache-Control": "max-age=0",
}

ROTATING_PROXIES_DOWNLOADER_HANDLER_AUTO_CLOSE_CACHED_CONNECTIONS_ENABLED: bool = True

DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware": None,
    "middlewares.HttpProxyMiddleware": 543,
}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE") if os.getenv("LOG_FILE", "") else None

ITEM_PIPELINES: Dict[str, int] = {}

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USERNAME = os.getenv("DB_USERNAME", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_DATABASE = os.getenv("DB_DATABASE", "db_name")

PIKA_LOG_LEVEL = os.getenv("PIKA_LOG_LEVEL", "WARN")
logging.getLogger("pika").setLevel(PIKA_LOG_LEVEL)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_VIRTUAL_HOST = os.getenv("RABBITMQ_VIRTUAL_HOST", "/")

try:
    HTTPCACHE_ENABLED = strtobool(os.getenv("HTTPCACHE_ENABLED", "False"))
except ValueError:
    HTTPCACHE_ENABLED = False

HTTPCACHE_IGNORE_HTTP_CODES = list(
    map(int, (s for s in os.getenv("HTTPCACHE_IGNORE_HTTP_CODES", "").split(",") if s))
)

EXTENSIONS = {}

# Send exceptions to Sentry
IS_SENTRY_ENABLED = os.getenv("IS_SENTRY_ENABLED", "false").lower() == "true"
if IS_SENTRY_ENABLED:
    SENTRY_DSN = os.getenv("SENTRY_DSN", None)
    # Optionally, additional configuration options can be provided
    SENTRY_CLIENT_OPTIONS = {
        # these correspond to the sentry_sdk.init kwargs
        "release": os.getenv("RELEASE", "0.0.0")
    }
    # Load SentryLogging extension before others
    EXTENSIONS["scrapy_sentry_sdk.extensions.SentryLogging"] = 1

configure_logging()
if datetime(*[int(number) for number in USER_AGENT_RELEASE_DATE.split('-')]) + timedelta(days=180) < datetime.now():
    logging.warning('USER_AGENT is outdated')
