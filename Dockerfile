FROM python:3.7-alpine3.15

WORKDIR /usr/src/app

COPY . .


RUN apk add --update --no-cache g++ gcc libxml2-dev libxslt-dev
RUN python3 setup.py install

VOLUME ["/usr/src/app/dumps"]

RUN crontab crontab

CMD ["crond", "-f"]
