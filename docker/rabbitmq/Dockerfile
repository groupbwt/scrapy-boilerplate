FROM rabbitmq:3.8.7-management
RUN apt-get update && apt-get install -y curl wget gnupg2 systemd gettext-base
COPY setup.sh /usr/local/bin/
RUN set -eu && chmod +x /usr/local/bin/setup.sh

ENTRYPOINT ["setup.sh"]
