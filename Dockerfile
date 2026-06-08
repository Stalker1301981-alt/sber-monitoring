FROM python:3-slim
WORKDIR /app
COPY calc.py .
EXPOSE 8080
CMD ["python3", "calc.py"]
