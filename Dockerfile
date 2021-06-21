FROM python:3.8-alpine3.12

RUN apk add --update alpine-sdk glib-dev rust curl cargo openssl-dev libffi-dev

RUN mkdir /airpurifier2mqtt

WORKDIR /airpurifier2mqtt

ADD airpurifier2mqtt.py ./

ADD requirements.txt ./

VOLUME /data

RUN pip install --upgrade pip -r requirements.txt

CMD ["python", "airpurifier2mqtt.py", "--config", "/data/airpurifier2mqtt.yaml" ]
