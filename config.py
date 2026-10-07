from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_GEO = PROJECT_ROOT / "data" / "geo"

UF = "RJ"
MUNICIPIO = "NITERÓI"

# --- Candidates ---

HUGO_LEAL = {
    "name": "HUGO LEAL",
    "elections": {
        2022: {"cargo": "DEPUTADO FEDERAL", "partido": "PSD", "nr": 5555},
        2018: {"cargo": "DEPUTADO FEDERAL", "partido": "PSD", "nr": 5555},
        2014: {"cargo": "DEPUTADO FEDERAL", "partido": "PROS", "nr": 2055},
        2010: {"cargo": "DEPUTADO FEDERAL", "partido": "PSC", "nr": 2055},
    },
}

FELIPE_PEIXOTO = {
    "name": "FELIPE DOS SANTOS PEIXOTO",
    "elections": {
        2022: {"cargo": "DEPUTADO FEDERAL", "partido": "PSD", "nr": "5512"},
        2020: {"cargo": "PREFEITO", "partido": "PSD", "nr": "55"},
        2018: {"cargo": "DEPUTADO ESTADUAL", "partido": "PSD", "nr": "55055"},
        2016: {"cargo": "PREFEITO", "partido": "PSB", "nr": "40"},
        2012: {"cargo": "PREFEITO", "partido": "PDT", "nr": "12"},
        2010: {"cargo": "DEPUTADO ESTADUAL", "partido": "PDT", "nr": "12369"},
    },
}

PARTY = "PSD"
PARTY_NUMBERS = {
    "PSD": "55",
    "PSC": "20",
    "PROS": "90",
    "PSB": "40",
}

# PSD (as a legal entity under this name) didn't exist before this year —
# used to distinguish "party didn't exist yet" from "chose not to run".
PSD_FOUNDING_YEAR = 2011

# --- TSE download URLs ---

TSE_CDN = "https://cdn.tse.jus.br/estatistica/sead/odsele"

FEDERAL_YEARS = [2022, 2018, 2014, 2010]
MUNICIPAL_YEARS = [2024, 2020, 2016, 2012]
ALL_YEARS = sorted(set(FEDERAL_YEARS + MUNICIPAL_YEARS))

def url_votacao_secao(year: int, uf: str = UF) -> str:
    return f"{TSE_CDN}/votacao_secao/votacao_secao_{year}_{uf}.zip"

def url_candidato_munzona(year: int) -> str:
    return f"{TSE_CDN}/votacao_candidato_munzona/votacao_candidato_munzona_{year}.zip"

def url_consulta_cand(year: int) -> str:
    return f"{TSE_CDN}/consulta_cand/consulta_cand_{year}.zip"

def url_perfil_eleitor_secao(year: int, uf: str = UF) -> str:
    return f"{TSE_CDN}/perfil_eleitor_secao/perfil_eleitor_secao_{year}_{uf}.zip"

def url_locais_votacao(year: int) -> str:
    return f"{TSE_CDN}/eleitorado_locais_votacao/eleitorado_local_votacao_{year}.zip"
