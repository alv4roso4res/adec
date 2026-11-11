"""Resposta do card 4 (integrantes do time).

Os exemplos vêm das fixtures reais em tests/fixtures/github/
(pulls_all.json e contributors.json).
"""

from pydantic import ConfigDict, Field

from api.schemas.common import ApiModel

_MEMBER_EXAMPLE = {
    "login": "GustaReis-bit",
    "avatarUrl": "https://avatars.githubusercontent.com/u/200959764?v=4",
    "prsOpen": 0,
    "prsMerged": 1,
    "commits": 8,
    "meetsRequirement": True,
}
_IDLE_EXAMPLE = {
    "login": "DrawnGZN",
    "avatarUrl": "https://github.com/DrawnGZN.png",
    "prsOpen": 0,
    "prsMerged": 0,
    "commits": 0,
    "meetsRequirement": False,
}


class TeamMember(ApiModel):
    """Um integrante de TEAM_LOGINS com a atividade dele no repositório.

    Todos os integrantes configurados aparecem, mesmo sem nenhuma atividade
    (com zeros).
    """

    model_config = ConfigDict(json_schema_extra={"examples": [_MEMBER_EXAMPLE, _IDLE_EXAMPLE]})

    login: str = Field(
        description=(
            "Login no GitHub, com as maiúsculas que o GitHub devolve (ou como "
            "está em TEAM_LOGINS, se não houver atividade)."
        ),
        examples=["GustaReis-bit"],
    )
    avatar_url: str = Field(
        description=(
            "Avatar do GitHub; sem atividade no repositório, "
            "https://github.com/<login>.png."
        ),
        examples=[_MEMBER_EXAMPLE["avatarUrl"], _IDLE_EXAMPLE["avatarUrl"]],
    )
    prs_open: int = Field(description="PRs abertos de autoria do integrante.", examples=[0])
    prs_merged: int = Field(
        description="PRs de autoria do integrante que foram mergeados.",
        examples=[1],
    )
    commits: int = Field(
        description=(
            "Commits na branch padrão (campo contributions de /contributors; só "
            "conta commits com e-mail ligado à conta). 0 se não aparece."
        ),
        examples=[8],
    )
    meets_requirement: bool = Field(
        description=(
            "Regra do trabalho: true se o integrante tem pelo menos 1 PR de "
            "autoria (aberto, mergeado ou fechado sem merge)."
        ),
        examples=[True],
    )
