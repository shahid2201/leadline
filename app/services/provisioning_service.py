from app.core.security import build_api_key, hash_secret
from app.models.api_key import APIKey
from app.models.user import User
from app.repositories.tenant_repository import TenantRepository


class ProvisioningService:
    def __init__(self, repository: TenantRepository) -> None:
        self.repository = repository

    async def provision_tenant(
        self,
        *,
        name: str,
        slug: str,
        owner_email: str,
        plan: str,
    ) -> tuple[str, str, str, str]:
        existing = await self.repository.get_by_slug(slug)
        if existing is not None:
            raise ValueError("tenant slug already exists")

        tenant = await self.repository.create(
            name=name,
            slug=slug,
            plan=plan,
            settings={
                "plan_limits": {},
                "design_partner": False,
                "rollout_percentage": 0,
            },
        )

        user = User(
            tenant_id=tenant.id,
            email=owner_email,
            role="owner",
            status="active",
            preferences={},
        )
        self.repository.session.add(user)
        await self.repository.session.flush()
        await self.repository.session.refresh(user)

        raw_key = build_api_key(prefix="ll_live")
        api_key = APIKey(
            tenant_id=tenant.id,
            name="default-live-key",
            scopes=["*"],
            status="active",
            key_prefix=raw_key.prefix,
            key_hash=hash_secret(raw_key.display),
        )
        self.repository.session.add(api_key)
        await self.repository.session.flush()
        await self.repository.session.refresh(api_key)

        await self.repository.session.commit()
        return tenant.id, user.id, raw_key.display, tenant.plan

    async def enroll_design_partner(
        self,
        *,
        tenant_id: str,
        cohort: str,
        launch_notes: str | None,
    ) -> tuple[bool, str]:
        tenant = await self.repository.get(tenant_id)
        if tenant is None:
            raise ValueError("tenant not found")

        settings = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
        settings["design_partner"] = True
        settings["design_partner_cohort"] = cohort
        settings["design_partner_notes"] = launch_notes or ""
        await self.repository.update(tenant, {"settings": settings})
        await self.repository.session.commit()
        return True, cohort

    async def promote_rollout(self, *, tenant_id: str, rollout_percentage: int) -> int:
        tenant = await self.repository.get(tenant_id)
        if tenant is None:
            raise ValueError("tenant not found")

        settings = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
        settings["rollout_percentage"] = rollout_percentage
        await self.repository.update(tenant, {"settings": settings})
        await self.repository.session.commit()
        return rollout_percentage
