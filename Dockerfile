FROM python:3.8.2

WORKDIR /usr/src/app

COPY requirements/base.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY reckerbot.py reckerbot.py

CMD [ "python", "./reckerbot.py", "serve" ]
