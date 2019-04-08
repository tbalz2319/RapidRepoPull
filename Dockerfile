
FROM python:3.7-alpine

LABEL name rapid
LABEL src "https://github.com/tbalz2319/RapidRepoPull"
LABEL creator Tbalz
LABEL dockerfile_maintenance khast3x
LABEL desc "This program uses Python to clone multiple security related repos using threading and multiprocessing"

RUN apk add git && git clone https://github.com/tbalz2319/RapidRepoPull.git RapidRepoPull
WORKDIR /RapidRepoPull
RUN python3 -m venv venv
RUN pip install -r requirements.txt
RUN chmod +x boot.sh

VOLUME [ "/RapidRepoPull" ]
# ENTRYPOINT
ENTRYPOINT [ "/RapidRepoPull/boot.sh" ]