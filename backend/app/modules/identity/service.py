"""Identity-owned account and role queries shared by API adapters."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from app.models.academic import Account, AccountRole, Role


class IdentityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_account(self, account_id: str) -> Account | None:
        return await self.session.scalar(select(Account).where(Account.id == account_id))

    async def get_account_by_email(self, email: str) -> Account | None:
        return await self.session.scalar(select(Account).where(Account.email == email))

    async def roles_for(self, account_id: str) -> list[str]:
        result = await self.session.scalars(
            select(Role.name)
            .join(AccountRole, AccountRole.role_id == Role.id)
            .where(AccountRole.account_id == account_id)
            .order_by(Role.name)
        )
        return list(result.all())

    async def has_role(self, account_id: str, role_name: str) -> bool:
        return role_name in await self.roles_for(account_id)

    async def ensure_role(self, name: str) -> Role:
        role = await self.session.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(id=str(uuid4()), name=name, description=f"Kairos {name.lower()} role")
            self.session.add(role)
            await self.session.flush()
        return role
