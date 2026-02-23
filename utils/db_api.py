from database.session import async_session
from database.models import User, Vacancy, Setting
from sqlalchemy import select, update, func
from sqlalchemy.dialects.sqlite import insert

async def get_or_create_user(tg_id: int, username: str = None, full_name: str = None):
    async with async_session() as session:
        stmt = select(User).where(User.tg_id == tg_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(tg_id=tg_id, username=username, full_name=full_name)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user

async def update_user_survey(tg_id: int, **kwargs):
    async with async_session() as session:
        stmt = update(User).where(User.tg_id == tg_id).values(**kwargs)
        await session.execute(stmt)
        await session.commit()

async def get_vacancies(limit: int = 3):
    async with async_session() as session:
        stmt = select(Vacancy).order_by(func.random()).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

async def get_all_vacancies():
    async with async_session() as session:
        stmt = select(Vacancy).order_by(Vacancy.id.desc())
        result = await session.execute(stmt)
        return result.scalars().all()

async def delete_vacancy(vac_id: int):
    async with async_session() as session:
        v = await session.get(Vacancy, vac_id)
        if v:
            await session.delete(v)
            await session.commit()
            return True
        return False

async def update_vacancy(vac_id: int, **kwargs):
    async with async_session() as session:
        stmt = update(Vacancy).where(Vacancy.id == vac_id).values(**kwargs)
        await session.execute(stmt)
        await session.commit()

async def add_vacancy(**kwargs):
    async with async_session() as session:
        vacancy = Vacancy(**kwargs)
        session.add(vacancy)
        await session.commit()
        return vacancy

async def get_all_users():
    async with async_session() as session:
        stmt = select(User.tg_id)
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]

async def get_stats():
    async with async_session() as session:
        total_users = await session.execute(select(func.count(User.id)))
        completed_tests = await session.execute(select(func.count(User.id)).where(User.test_completed == True))
        return {
            "total": total_users.scalar(),
            "completed": completed_tests.scalar()
        }

async def set_user_admin(tg_id: int, status: bool):
    async with async_session() as session:
        # First ensure user exists
        stmt = select(User).where(User.tg_id == tg_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.is_admin = status
            await session.commit()
            return True
        return False

async def is_db_admin(tg_id: int) -> bool:
    async with async_session() as session:
        stmt = select(User.is_admin).where(User.tg_id == tg_id)
        result = await session.execute(stmt)
        return result.scalar() or False

async def get_all_admins():
    async with async_session() as session:
        stmt = select(User).where(User.is_admin == True)
        result = await session.execute(stmt)
        return result.scalars().all()

async def get_setting(key: str, default: str = None) -> str:
    async with async_session() as session:
        stmt = select(Setting).where(Setting.key == key)
        result = await session.execute(stmt)
        setting = result.scalar_one_or_none()
        return setting.value if setting else default

async def set_setting(key: str, value: str):
    async with async_session() as session:
        stmt = select(Setting).where(Setting.key == key)
        result = await session.execute(stmt)
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            session.add(setting)
        await session.commit()
