FROM python:3.10-slim

WORKDIR /app

COPY requirements-base.txt .
RUN pip install --no-cache-dir -r requirements-base.txt

COPY requirements-extra.txt .
RUN pip install --no-cache-dir -r requirements-extra.txt

COPY . /app

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]