# Используем официальный образ Apify для Python
FROM apify/actor-python-playwright:3.11

# Копируем файлы проекта
COPY . ./

# Устанавливаем зависимости из requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Команда для запуска нашего скрипта
CMD ["python3", "main.py"]
