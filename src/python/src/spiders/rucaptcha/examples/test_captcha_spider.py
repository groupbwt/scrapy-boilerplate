# -*- coding: utf-8 -*-
import inspect

from scrapy import Request

from spiders.rucaptcha import RucaptchaSpider


class TestCaptchaSpider(RucaptchaSpider):
    name = "test_captcha"

    start_urls = ["https://www.mininghamster.com/login/"]

    def parse(self, response):
        # Find recaptcha
        recaptcha_js = response.xpath(
            '//script[@src="https://www.google.com/recaptcha/api.js"]'
        ).get()
        recaptcha_sitekey = response.xpath(
            '//div[@class="g-recaptcha"]/@data-sitekey'
        ).get()

        captcha_solved = response.meta.get("captcha_solved", False)
        solve_captcha = not captcha_solved

        if recaptcha_js and recaptcha_sitekey and solve_captcha:
            yield Request(
                response.url,
                callback=self.parse_captcha,
                meta={
                    "start_url": response.url,
                    "return_callback": inspect.currentframe().f_code.co_name,
                    "old_meta": response.meta,
                    "solve_captcha": solve_captcha,
                    "sitekey": recaptcha_sitekey,
                },
                dont_filter=True,
            )
        else:
            self.logger.debug("Captcha solved!")
            self.logger.debug(
                "Captcha key: %s", response.meta.get("captcha_key")
            )
            # do stuff with captcha key from response.meta.get("captcha_key")
