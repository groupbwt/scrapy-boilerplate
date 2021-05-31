# -*- coding: utf-8 -*-
import inspect

from scrapy import Request

from spiders.rucaptcha import RucaptchaSpider


class TestCaptchaSpider(RucaptchaSpider):
    """
    TestCaptchaSpider is an example spider using captcha solving.

    To solve captcha in your spider you should inherit RucaptchaSpider.
    If needed you can inherit other spiders using multiple inheritance.

    Captcha solving steps:
    1. Find captcha.
    2. Check for 'captcha_solved' parameter in response.meta.
    3. Send request to response.url with RucaptchaSpider.parse_captcha callback.
        Request parameters:
        start_url: response.url
        return_callback: the method name to return to
        old_meta: meta from current response
        sitekey: recaptcha sitekey

    4. Get 'captcha_key' from response.meta.
    5. Use captcha key to proceed scraping.
    """

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

        # Check is captcha solved
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
