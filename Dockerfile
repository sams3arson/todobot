FROM python

ENV API_ID=
ENV API_HASH=
ENV BOT_TOKEN=

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY . .

RUN pip3 install -r requirements.txt

CMD ["python3", "main.py"]

