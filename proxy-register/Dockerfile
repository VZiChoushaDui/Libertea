ARG DOCKER_REGISTRY=
FROM ${DOCKER_REGISTRY}python:3.8-alpine
ARG ALPINE_MIRROR=
RUN if [ -n "$ALPINE_MIRROR" ]; then ver=$(cut -d. -f1,2 /etc/alpine-release); printf '%s\n' "${ALPINE_MIRROR}/v${ver}/main" "${ALPINE_MIRROR}/v${ver}/community" > /etc/apk/repositories; fi

WORKDIR /app
COPY . .

RUN apk add --no-cache gcc python3-dev musl-dev linux-headers

ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN if [ -n "$PIP_INDEX_URL" ]; then \
      pip install -i "$PIP_INDEX_URL" --trusted-host "${PIP_TRUSTED_HOST:-package-mirror.liara.ir}" -r requirements.txt; \
    else \
      pip install -r requirements.txt; \
    fi

ENV PYTHONUNBUFFERED=0

CMD ["python", "-u", "main.py"]
