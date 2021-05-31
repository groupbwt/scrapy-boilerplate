# -*- coding: utf-8 -*-
import logging
from urllib.parse import urlencode

from scrapy import Request, Spider
from scrapy.utils.project import get_project_settings


class RucaptchaSpider(Spider):
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            "middlewares.DelayedRequestsMiddleware": 600,
        }
    }

    MAX_CAPTCHA_RETRIES = 5
    CAPTCHA_REQUEST_DELAY = 30

    logger = logging.getLogger(name=__name__)

    def parse(self, response, **kwargs):
        pass

    def parse_captcha(self, response):
        if response.meta.get("solve_captcha", False):
            project_settings = get_project_settings()
            rucaptcha_key = project_settings.get("RUCAPTCHA_KEY")
            rucaptcha_action = project_settings.get("RUCAPTCHA_ACTION")
            rucaptcha_score = project_settings.get("RUCAPTCHA_SCORE")

            if not rucaptcha_key:
                raise Exception("RUCAPTCHA_KEY is not provided")

            pageurl = response.url
            sitekey = response.meta.get("sitekey")

            params = urlencode(
                {
                    "method": "userrecaptcha",
                    "pageurl": pageurl,
                    "invisible": 1,
                    "json": 1,
                    "key": rucaptcha_key,
                    "action": rucaptcha_action,
                    "min_score": rucaptcha_score,
                    "googlekey": sitekey,
                }
            )
            rucaptcha_url = f"http://rucaptcha.com/in.php?{params}"

            yield Request(
                url=rucaptcha_url,
                method="POST",
                callback=self.__captcha_request,
                meta={
                    "start_url": response.meta.get("start_url"),
                    "return_callback": response.meta.get("return_callback"),
                    "old_meta": response.meta.get("old_meta"),
                    "rucaptcha_key": rucaptcha_key,
                },
                dont_filter=True,
            )

    def __captcha_request(self, response):
        data = response.json()

        if data["status"] == 1:
            captcha_id = data["request"]

            params = urlencode(
                {
                    "action": "get",
                    "json": 1,
                    "id": captcha_id,
                    "key": response.meta.get("rucaptcha_key"),
                }
            )
            url = f"https://rucaptcha.com/res.php?{params}"

            yield Request(
                url=url,
                method="POST",
                callback=self.__captcha_solving,
                meta={
                    "start_url": response.meta.get("start_url"),
                    "return_callback": response.meta.get("return_callback"),
                    "old_meta": response.meta.get("old_meta"),
                    "rucaptcha_key": response.meta.get("rucaptcha_key"),
                    "captcha_id": captcha_id,
                },
                dont_filter=True,
            )

    def __captcha_solving(self, response):
        data = response.json()
        if data["status"] == 1:
            captcha_result = data["request"]
            yield Request(
                response.meta.get("start_url"),
                callback=getattr(self, response.meta.get("return_callback")),
                meta={
                    "old_meta": response.meta.get("old_meta"),
                    "captcha_key": captcha_result,
                    "captcha_solved": bool(captcha_result),
                },
                dont_filter=True,
            )
        else:
            if data["request"] == "CAPCHA_NOT_READY":
                params = urlencode(
                    {
                        "action": "get",
                        "json": 1,
                        "id": response.meta.get("captcha_id"),
                        "key": response.meta.get("rucaptcha_key"),
                    }
                )
                url = f"https://rucaptcha.com/res.php?{params}"

                captcha_retries = (
                    response.meta.get("captcha_retries") + 1
                    if response.meta.get("captcha_retries")
                    else 1
                )

                if captcha_retries > self.MAX_CAPTCHA_RETRIES:
                    self.logger.error("Failed parsing with captcha")
                    return

                yield Request(
                    url=url,
                    method="POST",
                    callback=self.__captcha_solving,
                    meta={
                        "delay_request": self.CAPTCHA_REQUEST_DELAY,
                        "start_url": response.meta.get("start_url"),
                        "return_callback": response.meta.get(
                            "return_callback"
                        ),
                        "old_meta": response.meta.get("old_meta"),
                        "rucaptcha_key": response.meta.get("rucaptcha_key"),
                        "captcha_id": response.meta.get("captcha_id"),
                        "captcha_retries": captcha_retries,
                    },
                    dont_filter=True,
                )
            else:
                if data["request"] == "CAPCHA_UNSOLVABLE":
                    self.logger.error("Captcha unsolvable")
                else:
                    self.logger.error("Captcha response: %s", data["request"])
