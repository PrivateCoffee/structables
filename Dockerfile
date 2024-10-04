FROM alpine:3.20

ENV APP_ENV=/opt/venv
ENV PATH="${APP_ENV}/bin:$PATH"

RUN apk add --no-cache py3-pip uwsgi-python3 && \
  python3 -m venv $APP_ENV

COPY . /app

RUN $APP_ENV/bin/pip install --no-cache-dir pip && \
  $APP_ENV/bin/pip install /app && \
  adduser -S -D -H structables

COPY entrypoint.sh /entrypoint.sh

EXPOSE 8002

USER structables

ENTRYPOINT ["/entrypoint.sh"]
