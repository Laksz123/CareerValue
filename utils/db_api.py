from typing import Optional
from database.session import async_session
from database.models import User, Vacancy, VacancyPost, Setting, ReferralLink
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


async def get_user(tg_id: int):
    async with async_session() as session:
        stmt = select(User).where(User.tg_id == tg_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def update_user_survey(tg_id: int, **kwargs):
    async with async_session() as session:
        stmt = update(User).where(User.tg_id == tg_id).values(**kwargs)
        await session.execute(stmt)
        await session.commit()

def _sphere_to_db(sphere: str) -> str:
    """Map user-facing sphere labels to DB values."""
    mapping = {
        "💻 IT": "IT",
        "💬 Продажи": "Продажи",
        "📦 Склад / производство": "Склад",
        "🚚 Логистика": "Логистика",
        "🔎 Другое": None,
    }
    return mapping.get(sphere, sphere) if sphere else None


async def get_vacancies(limit: int = 3, sphere: str = None):
    async with async_session() as session:
        db_sphere = _sphere_to_db(sphere) if sphere else None
        stmt = select(Vacancy)
        if db_sphere:
            stmt = stmt.where(Vacancy.sphere == db_sphere)
        stmt = stmt.order_by(func.random()).limit(limit)
        result = await session.execute(stmt)
        vacs = result.scalars().all()
        if not vacs and db_sphere:
            stmt = select(Vacancy).order_by(func.random()).limit(limit)
            result = await session.execute(stmt)
            vacs = result.scalars().all()
        return vacs

async def get_vacancy(vac_id: int):
    async with async_session() as session:
        result = await session.execute(select(Vacancy).where(Vacancy.id == vac_id))
        return result.scalar_one_or_none()

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


# --- VacancyPost (post-based vacancies) ---

async def add_vacancy_post(content_type: str, text: str, entities_json: str = None, photo_file_id: str = None):
    async with async_session() as session:
        post = VacancyPost(
            content_type=content_type,
            text=text,
            entities_json=entities_json,
            photo_file_id=photo_file_id,
        )
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post


async def get_vacancy_posts(limit: int = 50):
    """Возвращает вакансии в порядке добавления (по id), с лимитом."""
    async with async_session() as session:
        stmt = select(VacancyPost).order_by(VacancyPost.id.asc()).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()


async def get_all_vacancy_posts():
    async with async_session() as session:
        stmt = select(VacancyPost).order_by(VacancyPost.id.desc())
        result = await session.execute(stmt)
        return result.scalars().all()


async def get_vacancy_post(post_id: int):
    async with async_session() as session:
        result = await session.execute(select(VacancyPost).where(VacancyPost.id == post_id))
        return result.scalar_one_or_none()


async def delete_vacancy_post(post_id: int):
    async with async_session() as session:
        post = await session.get(VacancyPost, post_id)
        if post:
            await session.delete(post)
            await session.commit()
            return True
        return False


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


# --- Referral Links ---

async def create_referral_link(name: str, slug: str) -> Optional[ReferralLink]:
    async with async_session() as session:
        existing = await session.execute(select(ReferralLink).where(ReferralLink.slug == slug))
        if existing.scalar_one_or_none():
            return None
        link = ReferralLink(name=name, slug=slug)
        session.add(link)
        await session.commit()
        await session.refresh(link)
        return link


async def get_all_referral_links():
    async with async_session() as session:
        stmt = select(ReferralLink).order_by(ReferralLink.created_at.desc())
        result = await session.execute(stmt)
        return result.scalars().all()


async def get_referral_link_by_slug(slug: str) -> Optional[ReferralLink]:
    async with async_session() as session:
        result = await session.execute(select(ReferralLink).where(ReferralLink.slug == slug))
        return result.scalar_one_or_none()


async def increment_referral_clicks(slug: str) -> bool:
    async with async_session() as session:
        link = await session.execute(select(ReferralLink).where(ReferralLink.slug == slug))
        link = link.scalar_one_or_none()
        if not link:
            return False
        link.clicks += 1
        await session.commit()
        return True


async def delete_referral_link(link_id: int) -> bool:
    async with async_session() as session:
        link = await session.get(ReferralLink, link_id)
        if link:
            await session.delete(link)
            await session.commit()
            return True
        return False
