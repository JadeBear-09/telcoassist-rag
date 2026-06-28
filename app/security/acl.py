from __future__ import annotations

from collections.abc import Iterable

from app.models import DocumentChunk, RequestIdentity


def parse_roles(raw_roles: str | None) -> list[str]:
    if not raw_roles:
        return []
    return [role.strip() for role in raw_roles.split(",") if role.strip()]


def normalize_identity(
    tenant_id: str | None = None,
    user_id: str | None = None,
    roles: Iterable[str] | None = None,
) -> RequestIdentity:
    return RequestIdentity(
        tenant_id=_clean(tenant_id),
        user_id=_clean(user_id),
        roles=[role for role in (_clean(role) for role in roles or []) if role],
    )


def chunk_allowed_for_identity(
    chunk: DocumentChunk,
    identity: RequestIdentity | None,
) -> bool:
    metadata = chunk.metadata
    tenant_id = _clean(metadata.tenant_id)
    allowed_roles = [_norm(role) for role in metadata.allowed_roles if _clean(role)]
    allowed_users = [_norm(user) for user in metadata.allowed_users if _clean(user)]

    if not tenant_id and not allowed_roles and not allowed_users:
        return True

    identity = identity or RequestIdentity()
    identity_tenant = _clean(identity.tenant_id)
    identity_user = _norm(identity.user_id) if identity.user_id else None
    identity_roles = {_norm(role) for role in identity.roles if _clean(role)}

    if tenant_id and _norm(tenant_id) != _norm(identity_tenant):
        return False

    if allowed_users or allowed_roles:
        user_allowed = bool(identity_user and identity_user in allowed_users)
        role_allowed = bool(identity_roles.intersection(allowed_roles))
        return user_allowed or role_allowed

    return bool(identity_tenant)


def filter_chunks_by_acl(
    chunks: Iterable[DocumentChunk],
    identity: RequestIdentity | None,
) -> list[DocumentChunk]:
    return [chunk for chunk in chunks if chunk_allowed_for_identity(chunk, identity)]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _norm(value: str | None) -> str:
    return (value or "").strip().casefold()
