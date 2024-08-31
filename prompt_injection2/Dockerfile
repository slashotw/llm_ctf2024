FROM tiangolo/uwsgi-nginx-flask:python3.10

COPY src /app

RUN pip3 install -r requirements.txt

CMD python3 main.py