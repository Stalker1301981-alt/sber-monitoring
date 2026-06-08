FROM python:3.9-slim
WORKDIR /app
# Копируем все файлы проекта
COPY . .
# Если у вас появится файл зависимостей, раскомментируйте строку ниже:
# RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8080
# Запуск вашего основного скрипта (замените calc.py на test_app.py при необходимости)
CMD ["python", "calc.py"]
