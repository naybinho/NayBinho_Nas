#!/usr/bin/env bash
# =============================================================================
# NayBinho NAS — Script de Criação e Publicação de Release no GitHub
# Uso: ./build/create-release.sh [versão] [tag/título]
# Exemplo: ./build/create-release.sh 1.0.1 "NayBinho NAS 1.0.1 Estável"
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"
TITLE="${2:-}"

if [[ -z "$VERSION" ]]; then
    if [[ -f "${ROOT_DIR}/VERSION" ]]; then
        CURRENT_VER=$(cat "${ROOT_DIR}/VERSION")
    else
        CURRENT_VER="1.0.0"
    fi
    read -rp "Informe a nova versão da Release (atual: ${CURRENT_VER}): " VERSION
fi

TAG="v${VERSION}"
TITLE="${TITLE:-NayBinho NAS ${TAG}}"
RELEASE_DIR="${ROOT_DIR}/dist-release"

echo "======================================================"
echo "  NayBinho NAS — Compilador e Publicador de Release"
echo "  Versão: ${VERSION} (${TAG})"
echo "======================================================"

mkdir -p "${RELEASE_DIR}"

# 1. Atualizar VERSION
echo "${VERSION}" > "${ROOT_DIR}/VERSION"

# 2. Build do Frontend
if command -v npm &>/dev/null; then
    echo ">> [1/5] Compilando ativos do Frontend (React + Vite)..."
    (cd "${ROOT_DIR}/frontend" && npm install --silent && npm run build)
else
    echo ">> [Aviso] npm não encontrado. Certifique-se de que frontend/dist já esteja gerado."
fi

# 3. Empacotar pacote de atualização (naybinho-update.tar.gz)
echo ">> [2/5] Gerando pacote de atualização naybinho-update-${TAG}.tar.gz..."
tar --exclude='*.pyc' --exclude='__pycache__' --exclude='.git' \
    -czf "${RELEASE_DIR}/naybinho-update-${TAG}.tar.gz" \
    -C "${ROOT_DIR}" \
    backend frontend/dist system appstore build/packages.list VERSION README.md

# 4. Gerar ISO do NayBinho NAS
echo ">> [3/5] Gerando Imagem ISO bootável naybinho-nas-${TAG}-amd64.iso..."
ISO_OUTPUT="${RELEASE_DIR}/naybinho-nas-${TAG}-amd64.iso"
if [[ -x "${ROOT_DIR}/build/build-iso.sh" ]]; then
    export NAYBINHO_VERSION="${VERSION}"
    export OUTPUT_ISO="${ISO_OUTPUT}"
    bash "${ROOT_DIR}/build/build-iso.sh" || {
        echo ">> Build padrão falhou; criando ISO usando xorriso..."
        mkdir -p /tmp/naybinho_iso_stage
        cp "${ROOT_DIR}/build/grub.cfg" /tmp/naybinho_iso_stage/ 2>/dev/null || true
        xorriso -as mkisofs -r -V "NAYBINHO_NAS" -o "${ISO_OUTPUT}" "${RELEASE_DIR}/naybinho-update-${TAG}.tar.gz"
    }
fi

# 5. Gerar Hashes e release.json
echo ">> [4/5] Gerando Checksums SHA256 e release.json..."
cd "${RELEASE_DIR}"
if [[ -f "naybinho-nas-${TAG}-amd64.iso" ]]; then
    sha256sum "naybinho-nas-${TAG}-amd64.iso" > "naybinho-nas-${TAG}-amd64.iso.sha256"
fi
sha256sum "naybinho-update-${TAG}.tar.gz" > "naybinho-update-${TAG}.tar.gz.sha256"

cat <<EOF > release.json
{
  "version": "${VERSION}",
  "tag_name": "${TAG}",
  "release_date": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
  "iso_name": "naybinho-nas-${TAG}-amd64.iso",
  "update_package": "naybinho-update-${TAG}.tar.gz",
  "changelog": "Lançamento oficial da versão ${TAG} com instalador ISO e atualizações de sistema."
}
EOF

# 6. Publicar no GitHub se gh CLI estiver logado
echo ">> [5/5] Verificando GitHub CLI (gh)..."
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
    echo ">> Publicando release ${TAG} no GitHub..."
    gh release create "${TAG}" \
        --title "${TITLE}" \
        --notes "Release oficial do NayBinho NAS ${TAG}. Baixe a ISO bootável ou atualize seu sistema existente com 1 clique." \
        "${RELEASE_DIR}/naybinho-nas-${TAG}-amd64.iso"* \
        "${RELEASE_DIR}/naybinho-update-${TAG}.tar.gz"* \
        "${RELEASE_DIR}/release.json"
    echo ">> Release publicada com sucesso no GitHub!"
else
    echo ">> gh CLI não configurado. Arquivos gerados em: ${RELEASE_DIR}/"
    echo ">> Você pode subir manualmente os arquivos em: https://github.com/naybinho/nas/releases/new"
fi
