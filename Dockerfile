FROM python:3.8.3-slim

WORKDIR /usr/src/app

RUN python3 -m pip install -U git+https://github.com/erlichsefi/il_supermarket_scarper.git

VOLUME ["/usr/src/app/dumps"]

RUN crontab crontab

CMD ["crond", "-f"]
