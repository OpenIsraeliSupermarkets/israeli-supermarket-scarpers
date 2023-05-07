#syntax=docker/dockerfile:1

FROM debian:latest as base
WORKDIR /usr/src/app
ARG PY_VERSION

# setting the enviroment 
RUN apt-get update -y && \
    apt-get install cron -y && \
    apt-get install libxml2-dev -y && \
    apt-get install libxslt-dev -y && \
    apt-get install gcc-10 -y && \
    apt-get install g++-10 -y && \
    apt-get install python3-pip -y && \
    apt-get install dieharder -y && \
    apt-get install wget -y && \
    apt-get clean && \
    apt-get autoremove

# setup python
RUN wget https://www.python.org/ftp/python/$PY_VERSION/Python-$PY_VERSION.tgz && \
    tar -xf Python-$PY_VERSION.tgz  && \
    ./configure --enable-optimizations && \
    make -j $(nproc) && \
    make altinstall

COPY . .
RUN python$PY_VERSION -m pip install .

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
CMD python$PY_VERSION example.py && cron & tail -f /var/log/cron.log

# run test
FROM base as test
# docker build -t erlichsefi/israeli-supermarket-scarpers --target prod .
# docker push erlichsefi/israeli-supermarket-scarpers
RUN python$PY_VERSION -m pip install . ".[test]"
CMD python$PY_VERSION -m pytest .

# docker build -t erlichsefi/israeli-supermarket-scarpers:test --target test .
# docker push erlichsefi/israeli-supermarket-scarpers:test
# docker run -it --rm --name test-run erlichsefi/israeli-supermarket-scarpers:test