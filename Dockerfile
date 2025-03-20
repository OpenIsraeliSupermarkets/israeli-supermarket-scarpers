#syntax=docker/dockerfile:1

FROM node:20.19.0-alpine3.21 as base
ARG PY_VERSION="3.11.0"

# setting the environment 
RUN apk update && \
    apk add --no-cache cron libxml2-dev libxslt-dev

# setting python and more 
RUN apk add --no-cache python3 py3-pip dieharder wget

# setup python
ENV HOME="/root"
WORKDIR ${HOME}
RUN apk add --no-cache git libbz2-dev ncurses-dev readline-dev libffi-dev openssl-dev
RUN git clone --depth=1 https://github.com/pyenv/pyenv.git .pyenv
ENV PYENV_ROOT="${HOME}/.pyenv"
ENV PATH="${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${PATH}"

RUN pyenv install $PY_VERSION
RUN pyenv global $PY_VERSION

# setup code
WORKDIR /usr/src/app
COPY . .
RUN python -m pip install .

VOLUME ["/usr/src/app/dumps"]

# development container
FROM base as dev
RUN apk add --no-cache git
RUN pip install black pylint

# production image
FROM base as prod

# ADD crontab /etc/cron.d
# RUN chmod 0644 /etc/cron.d/crontab
# RUN crontab /etc/cron.d/crontab
# RUN touch /var/log/cron.log
# && cron & tail -f /var/log/cron.log
CMD python main.py 

# run test
FROM base as test

# playwrite
RUN npx -y playwright@1.43.0 install --with-deps
RUN python -m playwright install  

RUN python -m pip install . ".[test]"
CMD python -m pytest -n 2