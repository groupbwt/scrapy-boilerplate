ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}
SHELL ["/bin/bash", "-l", "-c"]

#####################################
# Set Timezone
#####################################

ARG TZ=UTC
ENV TZ ${TZ}

COPY setup.sh /usr/local/bin/
RUN set -eu && chmod +x /usr/local/bin/setup.sh

RUN apt-get update && apt-get install -y curl wget gnupg2 systemd gettext-base
RUN set -eu && \
    wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.3/install.sh | bash && \
    export NVM_DIR="$HOME/.nvm" && \
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" && \
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" && \
    nvm install 13.6.0 && \
    npm install -g pm2

RUN /usr/local/bin/python -m pip install --upgrade pip && /usr/local/bin/python -m pip install poetry

ENTRYPOINT ["/bin/bash", "-l", "-c", "setup.sh"]
