import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from sprintalis_api.core.exceptions import SlugConflictError
from sprintalis_api.workspaces.models import Workspace, WorkspaceRole
from sprintalis_api.workspaces.repository import WorkspaceRepository, WorkspaceMemberRepository
from sprintalis_api.workspaces.schemas import slugify


async def create_workspace(db: AsyncSession, name: str, created_by: uuid.UUID) -> Workspace:
    workspace_repo = WorkspaceRepository(db)
    member_repo = WorkspaceMemberRepository(db)

    base_slug = slugify(name)

    if not base_slug:
        raise ValueError("Workspace name must contain at least one letter or number.")
    
    slug = base_slug
    suffix = 1

    while await workspace_repo.get_by_slug(slug) is not None:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
        
        if suffix > 50:
            raise SlugConflictError("Could not generate a unique workspace slug.")

    workspace = await workspace_repo.create(name=name, slug=slug, created_by=created_by)

    await member_repo.add_member(
        workspace_id=workspace.id,
        user_id=created_by,
        role=WorkspaceRole.OWNER,
    )

    await db.commit()
    await db.refresh(workspace)
    return workspace


async def list_workspaces_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Workspace]:
    workspace_repo = WorkspaceRepository(db)
    return await workspace_repo.list_for_user(user_id)
