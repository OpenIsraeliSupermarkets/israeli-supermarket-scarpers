FROM debian:latest

WORKDIR /usr/src/app

# setting the enviroment 
RUN apt-get update -y && apt-get install cron -y && apt-get install libxml2-dev -y && apt-get install libxslt-dev -y && apt-get install gcc-10 -y && apt-get install g++-10 -y && apt-get install -y python3-pip && apt-get install -y dieharder
COPY . .
RUN python3 setup.py install

VOLUME ["/usr/src/app/dumps"]

ADD crontab /etc/cron.d
RUN chmod 0644 /etc/cron.d/crontab
RUN crontab /etc/cron.d/crontab
RUN touch /var/log/cron.log

CMD python3 example.py && cron & tail -f /var/log/cron.log
