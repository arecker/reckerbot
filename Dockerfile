FROM python:3.8.2-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/* \
    && pip install cryptography \
    && apt-get purge -y --auto-remove gcc

WORKDIR /usr/src/app

COPY requirements/base.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY reckerbot.py reckerbot.py

CMD [ "python", "./reckerbot.py", "serve" ]
