FROM python:3.8

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

ENV MYSQL_HOST=nef_db
ENV MYSQL_PORT=3306
ENV MYSQL_USER=nef_user
ENV MYSQL_PASSWORD=nef_pass
ENV MYSQL_DB=nef_db

CMD [ "python", "app.py" ]
