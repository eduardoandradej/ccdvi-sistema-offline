"""Matriz de permissões por função operacional.

A permissão efetiva de uma requisição = função ativa da sessão, desde que exista uma
Authorization ativa (usuário + operação + base + função). A base é contexto de trabalho
e origem dos registros; ela não concede permissão por si só.
"""

ROLES: dict[str, str] = {
    "ADMIN_TIC": "Administrador TIC",
    "OPERADOR_AM": "Operador Ante Mortem",
    "OPERADOR_PM": "Operador/Perito Post Mortem",
    "REVISOR_RECONCILIACAO": "Revisor de Reconciliação",
    "COORDENADOR": "Coordenador",
    "AUDITOR": "Auditor",
}

# am:* / pm:*           registros AM / PM
# att_am:* / att_pm:*   anexos vinculados a registros AM / PM (conteúdo sensível)
PERMISSIONS: dict[str, frozenset[str]] = {
    "OPERADOR_AM": frozenset({"am:read", "am:write", "att_am:read", "att_am:write"}),
    "OPERADOR_PM": frozenset({"pm:read", "pm:write", "att_pm:read", "att_pm:write"}),
    "REVISOR_RECONCILIACAO": frozenset(
        {"am:read", "pm:read", "att_am:read", "att_pm:read", "match:read", "match:review"}
    ),
    # Coordenação e TIC não acessam automaticamente fotos/documentos sensíveis.
    "COORDENADOR": frozenset({"dashboard:read"}),
    "ADMIN_TIC": frozenset({"admin:users", "admin:health"}),
    "AUDITOR": frozenset({"audit:read"}),
}


def permissions_for(role: str | None) -> frozenset[str]:
    if role is None:
        return frozenset()
    return PERMISSIONS.get(role, frozenset())
