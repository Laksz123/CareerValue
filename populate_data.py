import asyncio
from database.session import init_db
from utils.db_api import add_vacancy

async def populate():
    await init_db()
    
    sample_vacancies = [
        {
            "title": "Middle Python Developer",
            "company": "Tech Solutions",
            "city": "Москва",
            "sphere": "IT",
            "experience": "1–3 года",
            "description": "Разработка микросервисов на FastAPI, оптимизация запросов к БД.",
            "salary_min": 180000
        },
        {
            "title": "Менеджер по продажам",
            "company": "FastScale",
            "city": "Санкт-Петербург",
            "sphere": "Продажи",
            "experience": "Без опыта",
            "description": "Работа с входящими лидами, проведение презентаций продукта.",
            "salary_min": 70000
        },
        {
            "title": "Senior Go Developer",
            "company": "Fintech Prime",
            "city": "Удалённо",
            "sphere": "IT",
            "experience": "3+ года",
            "description": "Проектирование архитектуры высоконагруженных систем.",
            "salary_min": 300000
        }
    ]
    
    for vac in sample_vacancies:
        await add_vacancy(**vac)
    
    print("Success: Database populated with test vacancies!")

if __name__ == "__main__":
    asyncio.run(populate())
