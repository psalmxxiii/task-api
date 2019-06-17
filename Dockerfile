FROM python:3.7.3-alpine3.9
RUN adduser -D api
WORKDIR /home/api
COPY requirements.txt requirements.txt
RUN python3 -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn==19.9.0
COPY api/app.py api/utils.py boot.sh ./
RUN chown -R api:api ./
RUN chmod +x boot.sh
USER api
ENV TZ America/Sao_Paulo
ENV COUNTER 5
EXPOSE 5000
ENTRYPOINT ["./boot.sh"]