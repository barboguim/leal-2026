"""Download raw TSE data for all election years (RJ only)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    DATA_RAW, ALL_YEARS, FEDERAL_YEARS, MUNICIPAL_YEARS, UF,
    url_votacao_secao, url_perfil_eleitor_secao, url_locais_votacao,
)
from _pipeline_utils import download_and_extract


def main():
    print("=" * 60)
    print("TSE Data Downloader — LEAL project")
    print("=" * 60)

    for year in ALL_YEARS:
        print(f"\n--- {year} ---")

        # Votes by section (RJ only)
        download_and_extract(
            url_votacao_secao(year),
            DATA_RAW / f"votacao_secao_{year}",
            f"votacao_secao {year} {UF}",
        )

        # Voter profile by section (RJ only)
        download_and_extract(
            url_perfil_eleitor_secao(year),
            DATA_RAW / f"perfil_eleitor_secao_{year}",
            f"perfil_eleitor {year} {UF}",
        )

        # Polling places (national file, only need most recent)
        if year in (2024, 2022):
            download_and_extract(
                url_locais_votacao(year),
                DATA_RAW / f"locais_votacao_{year}",
                f"locais_votacao {year}",
            )

    print("\nDone.")


if __name__ == "__main__":
    main()
