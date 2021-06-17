FROM python:3.8-alpine3.12

RUN apk add --update alpine-sdk glib-dev rust curl cargo openssl-dev libffi-dev

RUN mkdir /airpurifier2mqtt

WORKDIR /airpurifier2mqtt

RUN curl -o airpurifier2mqtt.py 'https://raw.githubusercontent.com/kneip68/airpurifier2mqtt/main/airpurifier2mqtt.py'

RUN curl -o requirements.txt 'https://raw.githubusercontent.com/kneip68/airpurifier2mqtt/main/requirements.txt'

VOLUME /data

RUN pip install --upgrade pip -r requirements.txt

CMD ["python", "airpurifier2mqtt.py", "--config", "/data/airpurifier2mqtt.yaml" ]
