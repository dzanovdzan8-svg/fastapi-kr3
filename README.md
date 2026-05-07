# Контрольная работа 3 - FastAPI

## Установка и запуск

1. Установить зависимости:
pip install -r requirements.txt

2. Создать файл .env на основе .env.example:
cp .env.example .env

3. Запустить приложение:
python app.py

или

uvicorn app:app --reload

## Тестирование

Регистрация пользователя:
curl -X POST http://localhost:8000/register -H "Content-Type: application/json" -d '{"username":"test","password":"12345678"}'

Логин (JWT):
curl -X POST http://localhost:8000/login -H "Content-Type: application/json" -d '{"username":"test","password":"12345678"}'

Логин (Basic Auth):
curl -u admin:secret http://localhost:8000/login_basic

Создание Todo:
curl -X POST http://localhost:8000/todos -H "Content-Type: application/json" -H "Authorization: Bearer <token>" -d '{"title":"Test","description":"Desc"}'

Получение Todo:
curl http://localhost:8000/todos/1 -H "Authorization: Bearer <token>"

Обновление Todo:
curl -X PUT http://localhost:8000/todos/1 -H "Content-Type: application/json" -H "Authorization: Bearer <token>" -d '{"completed":true}'

Удаление Todo:
curl -X DELETE http://localhost:8000/todos/1 -H "Authorization: Bearer <token>"

Приватный ресурс:
curl http://localhost:8000/protected_resource -H "Authorization: Bearer <token>"

## Режимы работы

DEV (по умолчанию):
- Документация доступна на /docs (защищена Basic Auth)
- /redoc скрыт

PROD:
- Установить MODE=PROD в .env
- Вся документация отключена (404)
