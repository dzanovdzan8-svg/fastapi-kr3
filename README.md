# Контрольная работа №3 - FastAPI

## Установка и запуск

1. Установите зависимости:
   pip install -r requirements.txt

2. Переименуйте файл app (1).py в app.py (чтобы убрать пробел в названии).

3. Запустите сервер:
   uvicorn app:app --reload

## Тестирование (curl)

### 3.1 Создание пользователя
curl -X POST http://localhost:8000/create_user -H "Content-Type: application/json" -d '{"name":"User","email":"user@test.com","age":20}'

### 3.2 Поиск товаров
curl "http://localhost:8000/products/search?keyword=code"

### 5.1 Логин (Cookie)
# 1. Логинимся и сохраняем куку в файл cookies.txt
curl -c cookies.txt -X POST http://localhost:8000/login -H "Content-Type: application/json" -d '{"username":"mihail","password":"secure1234"}'

# 2. Проверяем доступ к профилю с помощью куки
curl -b cookies.txt http://localhost:8000/user

### 5.2 Логин с HMAC
curl -c cookies.txt -X POST http://localhost:8000/login_signed -H "Content-Type: application/json" -d '{"username":"admin","password":"adminpass"}'
curl -b cookies.txt http://localhost:8000/profile

### 5.4 Заголовки
curl -H "User-Agent: TestBot" -H "Accept-Language: ru-RU" http://localhost:8000/headers
