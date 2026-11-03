FROM python:3.12-slim

WORKDIR /app

# 先拷依赖清单，单独装依赖 —— 代码改动时能复用这一层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷代码
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
