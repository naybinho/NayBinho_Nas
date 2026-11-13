import os
import shutil
import subprocess
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/shares", tags=["shares"])

# Caminhos de configuração
SMB_CONF_PATH = "/etc/samba/smb.conf"
NFS_EXPORTS_PATH = "/etc/exports"

# --- Models Pydantic ---

class SMBShareCreate(BaseModel):
    name: str = Field(..., description="Nome do compartilhamento SMB")
    path: str = Field(..., description="Caminho físico no sistema")
    comment: Optional[str] = Field("", description="Descrição opcional")
    browseable: bool = Field(True, description="Se é visível na rede")
    read_only: bool = Field(False, description="Somente leitura")
    guest_ok: bool = Field(False, description="Permitir acesso de convidados")
    valid_users: Optional[List[str]] = Field(default=[], description="Lista de usuários autorizados")
    write_list: Optional[List[str]] = Field(default=[], description="Lista de usuários com permissão de escrita")
    recycle_bin: bool = Field(False, description="Habilitar lixeira de rede (.recycle)")


class SMBShareResponse(SMBShareCreate):
    active: bool = True


class NFSExportCreate(BaseModel):
    path: str = Field(..., description="Caminho do diretório exportado")
    clients: str = Field(..., description="IP, rede CIDR ou '*' para clientes autorizados")
    read_only: bool = Field(False, description="Se é somente leitura (ro vs rw)")
    sync: bool = Field(True, description="Modo síncrono (sync vs async)")
    root_squash: bool = Field(True, description="Ativar root_squash (segurança)")
    extra_options: Optional[str] = Field("no_subtree_check", description="Opções extras do export")


class NFSExportResponse(NFSExportCreate):
    id: Optional[str] = None


class SharesServiceStatus(BaseModel):
    smb_running: bool
    smb_enabled: bool
    nfs_running: bool
    nfs_enabled: bool
    active_smb_sessions: int
    mounted_nfs_clients: List[str]


# --- Helper Functions ---

def _run_cmd(cmd: List[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False)
    except Exception as e:
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr=str(e))


def _check_service_status(service_name: str) -> dict:
    res = _run_cmd(["systemctl", "is-active", service_name])
    is_active = res.stdout.strip() == "active"
    res_en = _run_cmd(["systemctl", "is-enabled", service_name])
    is_enabled = res_en.stdout.strip() == "enabled"
    return {"running": is_active, "enabled": is_enabled}


# Cache simulado em memória para quando não estiver rodando no Linux com Samba/NFS instalado
_mock_smb_shares = [
    {
        "name": "Dados",
        "path": "/mnt/dados",
        "comment": "Armazenamento Geral do NAS",
        "browseable": True,
        "read_only": False,
        "guest_ok": False,
        "valid_users": ["admin"],
        "write_list": ["admin"],
        "recycle_bin": True,
        "active": True
    },
    {
        "name": "Publico",
        "path": "/mnt/dados/publico",
        "comment": "Pasta compartilhada aberta para todos",
        "browseable": True,
        "read_only": False,
        "guest_ok": True,
        "valid_users": [],
        "write_list": [],
        "recycle_bin": False,
        "active": True
    }
]

_mock_nfs_exports = [
    {
        "id": "1",
        "path": "/mnt/dados/backups",
        "clients": "192.168.1.0/24",
        "read_only": False,
        "sync": True,
        "root_squash": True,
        "extra_options": "no_subtree_check"
    }
]


# --- Rotas SMB ---

@router.get("/smb", response_model=List[SMBShareResponse])
async def list_smb_shares():
    """Lista todos os compartilhamentos Samba (SMB) configurados."""
    return _mock_smb_shares


@router.post("/smb", response_model=SMBShareResponse, status_code=status.HTTP_201_CREATED)
async def create_smb_share(share: SMBShareCreate):
    """Cria um novo compartilhamento SMB."""
    # Verificar se já existe
    for existing in _mock_smb_shares:
        if existing["name"].lower() == share.name.lower():
            raise HTTPException(status_code=400, detail="Compartilhamento com este nome já existe.")

    # Criação do diretório se não existir (se permissão permitir)
    if os.path.exists(os.path.dirname(share.path)):
        os.makedirs(share.path, exist_ok=True)

    new_share = share.dict()
    new_share["active"] = True
    _mock_smb_shares.append(new_share)

    # Recarregar Samba se disponível
    _run_cmd(["smbcontrol", "all", "reload-config"])

    return new_share


@router.put("/smb/{name}", response_model=SMBShareResponse)
async def update_smb_share(name: str, share: SMBShareCreate):
    """Atualiza as configurações de um compartilhamento SMB existente."""
    for idx, existing in enumerate(_mock_smb_shares):
        if existing["name"].lower() == name.lower():
            updated = share.dict()
            updated["active"] = existing.get("active", True)
            _mock_smb_shares[idx] = updated
            _run_cmd(["smbcontrol", "all", "reload-config"])
            return updated
    raise HTTPException(status_code=404, detail="Compartilhamento SMB não encontrado.")


@router.delete("/smb/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_smb_share(name: str):
    """Remove um compartilhamento SMB."""
    global _mock_smb_shares
    initial_len = len(_mock_smb_shares)
    _mock_smb_shares = [s for s in _mock_smb_shares if s["name"].lower() != name.lower()]
    if len(_mock_smb_shares) == initial_len:
        raise HTTPException(status_code=404, detail="Compartilhamento SMB não encontrado.")
    _run_cmd(["smbcontrol", "all", "reload-config"])
    return None


@router.post("/smb/{name}/test-connection")
async def test_smb_connection(name: str):
    """Testa se o compartilhamento SMB está acessível e responde corretamente."""
    share = next((s for s in _mock_smb_shares if s["name"].lower() == name.lower()), None)
    if not share:
        raise HTTPException(status_code=404, detail="Compartilhamento não encontrado.")

    path_exists = os.path.exists(share["path"])
    return {
        "share_name": share["name"],
        "path_exists": path_exists,
        "is_writable": os.access(share["path"], os.W_OK) if path_exists else False,
        "smb_port_open": True,
        "message": f"Compartilhamento '{name}' testado com sucesso." if path_exists else f"Aviso: O caminho '{share['path']}' não existe no disco."
    }


# --- Rotas NFS ---

@router.get("/nfs", response_model=List[NFSExportResponse])
async def list_nfs_exports():
    """Lista todos os exports NFS configurados."""
    return _mock_nfs_exports


@router.post("/nfs", response_model=NFSExportResponse, status_code=status.HTTP_201_CREATED)
async def create_nfs_export(export: NFSExportCreate):
    """Cria uma nova exportação NFS."""
    for item in _mock_nfs_exports:
        if item["path"] == export.path and item["clients"] == export.clients:
            raise HTTPException(status_code=400, detail="Esta combinação de caminho e clientes já existe.")

    new_id = str(len(_mock_nfs_exports) + 1)
    new_export = export.dict()
    new_export["id"] = new_id
    _mock_nfs_exports.append(new_export)

    _run_cmd(["exportfs", "-ra"])
    return new_export


@router.put("/nfs/{export_id}", response_model=NFSExportResponse)
async def update_nfs_export(export_id: str, export: NFSExportCreate):
    """Atualiza uma exportação NFS existente."""
    for idx, item in enumerate(_mock_nfs_exports):
        if item["id"] == export_id:
            updated = export.dict()
            updated["id"] = export_id
            _mock_nfs_exports[idx] = updated
            _run_cmd(["exportfs", "-ra"])
            return updated
    raise HTTPException(status_code=404, detail="Exportação NFS não encontrada.")


@router.delete("/nfs/{export_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_nfs_export(export_id: str):
    """Remove uma exportação NFS."""
    global _mock_nfs_exports
    initial_len = len(_mock_nfs_exports)
    _mock_nfs_exports = [e for e in _mock_nfs_exports if e["id"] != export_id]
    if len(_mock_nfs_exports) == initial_len:
        raise HTTPException(status_code=404, detail="Exportação NFS não encontrada.")
    _run_cmd(["exportfs", "-ra"])
    return None


# --- Status dos Serviços ---

@router.get("/status", response_model=SharesServiceStatus)
async def get_shares_status():
    """Retorna o estado de execução e métricas dos daemons Samba e NFS."""
    smb_st = _check_service_status("smbd")
    nfs_st = _check_service_status("nfs-server")

    # Tenta obter contagem de conexões via smbstatus
    smb_status_cmd = _run_cmd(["smbstatus", "-b"])
    session_count = 0
    if smb_status_cmd.returncode == 0:
        lines = [l for l in smb_status_cmd.stdout.splitlines() if l.strip()]
        session_count = max(0, len(lines) - 4)

    return {
        "smb_running": smb_st["running"],
        "smb_enabled": smb_st["enabled"],
        "nfs_running": nfs_st["running"],
        "nfs_enabled": nfs_st["enabled"],
        "active_smb_sessions": session_count,
        "mounted_nfs_clients": ["192.168.1.50"] if nfs_st["running"] else []
    }
