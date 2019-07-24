ARG SCRAPY_VERSION=1.6
FROM scrapinghub/scrapinghub-stack-scrapy:${SCRAPY_VERSION}-py3-latest

# Set Timezone
ARG TZ=UTC

ENV TZ=${TZ}

ADD https://github.com/Yelp/dumb-init/releases/download/v1.2.2/dumb-init_1.2.2_amd64 /usr/local/bin/dumb-init
RUN chmod +x /usr/local/bin/dumb-init
ENTRYPOINT ["dumb-init", "--"]

RUN pip install --no-cache-dir pipenv

COPY src/Pipfile .
RUN pipenv lock && pipenv install --dev --pre --system

WORKDIR /var/app

# change this to actual scraper command if necessary
CMD ["sh", "-c", "scrapy shell"]
