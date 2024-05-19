#syntax=docker/dockerfile:1

FROM node:20-bookworm as base
WORKDIR /usr/src/app
ARG PY_VERSION="3.11.0"

# setting the enviroment 
RUN apt-get update -y && \
    apt-get install cron -y && \
    apt-get install libxml2-dev -y && \
    apt-get install libxslt-dev -y 

# playwrite
RUN npx -y playwright@1.43.0 install --with-deps
    

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
RUN python -m  playwright install  

VOLUME ["/usr/src/app/dumps"]

# development container
FROM base as dev
RUN apt-get -y install git
RUN pip install black
RUN pip install pylint


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