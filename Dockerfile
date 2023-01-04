FROM python:3.8-slim-buster
ENV API_TOKEN ${API_TOKEN}
ADD . /app
WORKDIR /app
RUN pip3 install -r requirements.txt
RUN chmod +x /app/main.py
CMD python3 /app/main.py;
