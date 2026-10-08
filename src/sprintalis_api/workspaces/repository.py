import uuid
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sprintalis_api.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole


class WorkspaceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, workspace_id: uuid.UUID) -> Workspace | None:
        return await self.db.scalar(
            select(Workspace).where(
                Workspace.id == workspace_id, Workspace.deleted_at.is_(None)
            )
        )

    async def get_by_slug(self, slug: str) -> Workspace | None:
        return await self.db.scalar(select(Workspace).where(Workspace.slug == slug))

    async def create(self, name: str, slug: str, created_by: uuid.UUID) -> Workspace:
        workspace = Workspace(name=name, slug=slug, created_by=created_by)
        self.db.add(workspace)
        await self.db.flush()
        return workspace

    async def list_for_user(self, user_id: uuid.UUID) -> list[Workspace]:
        result = await self.db.scalars(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id, Workspace.deleted_at.is_(None))
            .order_by(Workspace.created_at.desc())
        )
        return list(result.all())

    async def soft_delete(self, workspace_id: uuid.UUID, deleted_by: uuid.UUID) -> bool:
        deleted_id = await self.db.scalar(
            update(Workspace)
            .where(Workspace.id == workspace_id, Workspace.deleted_at.is_(None))
            .values(deleted_at=func.now(), deleted_by=deleted_by)
            .returning(Workspace.id)
        )
        return deleted_id

    async def update_name(self, workspace_id: uuid.UUID, name: str) -> Workspace | None:
        workspace = await self.db.scalar(
            update(Workspace)
            .where(Workspace.id == workspace_id, Workspace.deleted_at.is_(None))
            .values(name=name)
            .returning(Workspace)
        )
        return workspace

    async def count_owned_by_user(self, user_id: uuid.UUID) -> int:
        count = await self.db.scalar(
            select(func.count())
            .select_from(WorkspaceMember)
            .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.role == WorkspaceRole.OWNER,
                Workspace.deleted_at.is_(None),
            )
        )
        return count or 0


class WorkspaceMemberRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_membership(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        return await self.db.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )

    async def add_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, role: WorkspaceRole
    ) -> WorkspaceMember:
        member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
        self.db.add(member)
        await self.db.flush()
        return member
