FROM docker.io/library/python:3.9-slim-buster

COPY . /usr/src/thot/

RUN if ! command -v git; then \
    sed -i \
      -e '/git+/s#\([^ ]\)@\([^; ]*\)#\1/archive/\2.zip#' \
      -e "s@git+@@g" \
      /usr/src/thot/setup.py; \
    fi

RUN pip --disable-pip-version-check install \
      --cache-dir /var/cache/pip \
      "/usr/src/thot[jinja,code]" \
 && rm -rf /var/cache/pip/* /tmp/*pip* /usr/src/thot

ENTRYPOINT ["/usr/local/bin/thot"]
VOLUME /srv
WORKDIR /srv
