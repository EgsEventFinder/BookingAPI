FROM python:3.10-alpine

WORKDIR /app

RUN apk add --no-cache gcc musl-dev && \
    python3 -m pip install --upgrade pip && \
    apk del gcc musl-dev

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

ENV TZ Europe/Lisbon

EXPOSE 5010

COPY . .

CMD [ "python3", "app.py" ]
