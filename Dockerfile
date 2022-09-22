FROM debian:latest

RUN apt-get update -y && apt-get install cron -y && apt-get install libxml2-dev -y && apt-get install libxslt-dev -y && apt-get install gcc-10 -y && apt-get install g++-10 -y && apt-get install -y python3-pip && apt-get install -y dieharder


WORKDIR /usr/src/app

COPY . .

RUN python3 setup.py install

VOLUME ["/usr/src/app/dumps"]

RUN crontab crontab

CMD ["cron", "-f"]
