FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY calc.py test_app.py ./
EXPOSE 8080
EXPOSE 8000
CMD ["python", "calc.py"]
