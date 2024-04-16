#syntax=docker/dockerfile:1

FROM debian:latest as base
WORKDIR /usr/src/app
ARG PY_VERSION="3.11.0"

# setting the enviroment 
RUN apt-get update -y && \
    apt-get install cron -y && \
    apt-get install libxml2-dev -y && \
    apt-get install libxslt-dev -y 

# setting the C++
# RUN apt-get install gcc-10 -y && \
#     apt-get install g++-10 -y 

# setting python and more 
RUN apt-get install python3-pip -y && \
    apt-get install dieharder -y && \
    apt-get install wget -y && \
    apt-get clean && \
    apt-get autoremove

# setup python
ENV HOME="/root"
WORKDIR ${HOME}
RUN apt-get install -y git libbz2-dev libncurses-dev  libreadline-dev libffi-dev libssl-dev
RUN git clone --depth=1 https://github.com/pyenv/pyenv.git .pyenv
ENV PYENV_ROOT="${HOME}/.pyenv"
ENV PATH="${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${PATH}"

RUN pyenv install $PY_VERSION
RUN pyenv global $PY_VERSION

# setup code
COPY . .
RUN python -m pip install .

VOLUME ["/usr/src/app/dumps"]

# development container
FROM base as dev
RUN apt-get -y install git
RUN pip install black
RUN pip install pylint

# install google chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get -y update
RUN apt-get install -y google-chrome-stable

# install chromedriver
RUN apt-get install -yqq unzip
RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip
RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/

# set display port to avoid crash
ENV DISPLAY=:99

# production image
FROM base as prod

ADD crontab /etc/cron.d
RUN chmod 0644 /etc/cron.d/crontab
RUN crontab /etc/cron.d/crontab
RUN touch /var/log/cron.log
CMD python example.py && cron & tail -f /var/log/cron.log

# run test
FROM base as test
# docker build -t erlichsefi/israeli-supermarket-scarpers --target prod .
# docker push erlichsefi/israeli-supermarket-scarpers
RUN python -m pip install . ".[test]"
CMD python -m pytest .

# docker build -t erlichsefi/israeli-supermarket-scarpers:test --target test .
# docker push erlichsefi/israeli-supermarket-scarpers:test
# docker run -it --rm --name test-run erlichsefi/israeli-supermarket-scarpers:test