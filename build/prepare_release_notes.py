#!/usr/bin/env python3
"""
NayBinho NAS — Prepare Release Notes and release.json
Extracts changelog for the current version (Novidades, Melhorias, Correções)
and prepares RELEASE_NOTES.md and release.json.
"""
import os
import re
import json
import sys
from pathlib import Path

def main():
    version = os.environ.get("VERSION", "1.0.0").lstrip("v")
    tag_name = f"v{version}"
    root_dir = Path(__file__).resolve().parent.parent
    dist_dir = root_dir / "dist-release"
    dist_dir.mkdir(parents=True, exist_ok=True)

    changelog_file = root_dir / "CHANGELOG.md"
    notes = ""

    if changelog_file.exists():
        content = changelog_file.read_text(encoding="utf-8")
        # Match from "## [v1.0.0]" or "## v1.0.0" until next "## [v" or EOF
        pattern = rf'##\s*\[?{re.escape(tag_name)}\]?.*?(?=\n##\s*\[?v|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            notes = match.group(0).strip()

    if not notes:
        notes = f"""## {tag_name} - NayBinho NAS

### 🚀 Novidades
- Lançamento oficial do sistema operacional NayBinho NAS v{version}.
- Imagem ISO bootável de instalação autônoma baseada no Ubuntu 26.04.1 LTS.
- Suporte nativo a Docker com 5 lojas de aplicativos pré-configuradas.
- Sistema completo de gerenciamento de RAID (0, 1, 5, 6, 10 e ZFS).
- Compartilhamentos de rede SMB/CIFS e NFS com painel web moderno.

### ⚡ Melhorias
- Otimização do backend FastAPI com consumo reduzido de memória RAM.
- Painel Dark Glass com monitoramento de telemetria em tempo real.
- Sistema de verificação e aplicação de auto-atualização em 1 clique.

### 🐛 Correções
- Ajustes de permissões e segurança para containers e serviços de rede.
- Otimização no pipeline de compilação da imagem ISO.
"""

    notes_file = dist_dir / "RELEASE_NOTES.md"
    full_notes = (
        f"{notes}\n\n"
        f"---\n"
        f"### 📦 Arquivos da Versão {tag_name}\n"
        f"- **`naybinho-nas-{tag_name}-amd64.iso`**: Imagem ISO bootável para instalação em bare metal ou máquina virtual.\n"
        f"- **`naybinho-update-{tag_name}.tar.gz`**: Pacote de auto-atualização para sistemas já instalados.\n"
        f"- **`release.json`**: Metadados de integridade e verificação para o auto-updater.\n"
    )
    notes_file.write_text(full_notes, encoding="utf-8")
    print(f"Generated {notes_file}")

    # Generate release.json
    iso_sha = ""
    iso_sha_file = dist_dir / f"naybinho-nas-{tag_name}-amd64.iso.sha256"
    if iso_sha_file.exists():
        iso_sha = iso_sha_file.read_text(encoding="utf-8").split()[0]

    up_sha = ""
    up_sha_file = dist_dir / f"naybinho-update-{tag_name}.tar.gz.sha256"
    if up_sha_file.exists():
        up_sha = up_sha_file.read_text(encoding="utf-8").split()[0]

    release_meta = {
        "version": version,
        "tag_name": tag_name,
        "release_title": f"NayBinho NAS {tag_name}",
        "iso_name": f"naybinho-nas-{tag_name}-amd64.iso",
        "iso_sha256": iso_sha,
        "update_package": f"naybinho-update-{tag_name}.tar.gz",
        "update_sha256": up_sha,
        "min_supported_version": "1.0.0",
        "requires_reboot": False,
        "changelog": notes
    }

    rel_file = dist_dir / "release.json"
    rel_file.write_text(json.dumps(release_meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {rel_file}")

if __name__ == "__main__":
    main()
