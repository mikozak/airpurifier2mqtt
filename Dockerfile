FROM python:3-alpine3.12

RUN apk add --update alpine-sdk glib-dev rust curl cargo openssl-dev libffi-dev

RUN mkdir /airpurifier2mqtt

WORKDIR /airpurifier2mqtt
