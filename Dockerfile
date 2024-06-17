FROM alpine:3.20

ENV APP_ENV=/opt/venv
ENV PATH="${APP_ENV}/bin:$PATH"

RUN apk add --no-cache py3-pip uwsgi-python3 && \
  python3 -m venv $APP_ENV && \
  $APP_ENV/bin/pip install --no-cache-dir pip structables && \
  adduser -S -D -H structables

COPY entrypoint.sh /entrypoint.sh

EXPOSE 8002

USER structables

ENTRYPOINT ["/entrypoint.sh"]
