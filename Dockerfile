FROM python:3.13-alpine

LABEL org.opencontainers.image.title="rapidrepopull"
LABEL org.opencontainers.image.source="https://github.com/tbalz2319/RapidRepoPull"
LABEL org.opencontainers.image.authors="Talal Balouch"
LABEL org.opencontainers.image.description="Clone and maintain a curated list of security repositories, in parallel."

RUN apk add --no-cache git openssh-client

WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY rapidrepopull ./rapidrepopull
RUN pip install --no-cache-dir .

WORKDIR /repos
VOLUME [ "/repos" ]
ENTRYPOINT [ "rapidrepopull", "-o", "/repos" ]
CMD [ "-v", "-t", "32" ]
