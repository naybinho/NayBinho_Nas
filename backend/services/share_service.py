"""
NayBinho NAS — File Sharing Service (SMB / CIFS & NFS)
Manages Samba configuration (/etc/samba/smb.conf), Samba users (pdbedit/smbpasswd),
NFS export rules (/etc/exports), daemon reloads/restarts, and service status tracking.
"""

from __future__ import annotations

import configparser
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from backend.models.storage_models import (
    NfsExport,
    OperationResult,
    SambaUser,
    Share,
    ShareProtocol,
    ShareServiceStatus,
    ShareState,
    SmbShare,
)

logger = logging.getLogger(__name__)

SMB_CONF_PATH = "/etc/samba/smb.conf"
NFS_EXPORTS_PATH = "/etc/exports"


def _run_cmd(cmd: List[str], check: bool = False) -> subprocess.CompletedProcess:
    logger.debug("Executing share command: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


class ShareService:
    """Provides high-level management for SMB (Samba) and NFS file shares."""

    def __init__(
        self,
        smb_conf_path: str = SMB_CONF_PATH,
        nfs_exports_path: str = NFS_EXPORTS_PATH,
    ):
        self.smb_conf_path = Path(smb_conf_path)
        self.nfs_exports_path = Path(nfs_exports_path)

    # -----------------------------------------------------------------------
    # Service Status & Daemons
    # -----------------------------------------------------------------------

    def get_service_status(self) -> ShareServiceStatus:
        """Checks whether smbd and nfs-server are running."""
        smb_check = _run_cmd(["systemctl", "is-active", "smbd"])
        smb_running = smb_check.stdout.strip() == "active"

        nfs_check = _run_cmd(["systemctl", "is-active", "nfs-server"])
        nfs_running = nfs_check.stdout.strip() == "active"

        # Fetch versions if possible
        smb_ver_res = _run_cmd(["smbd", "--version"])
        smb_version = smb_ver_res.stdout.strip() if smb_ver_res.returncode == 0 else None

        return ShareServiceStatus(
            smb_running=smb_running,
            nfs_running=nfs_running,
            smb_version=smb_version,
            nfs_version="NFSv4/NFSv3",
        )

    def reload_smb(self) -> OperationResult:
        """Reloads Samba daemon configuration."""
        res = _run_cmd(["systemctl", "reload-or-restart", "smbd"])
        if res.returncode == 0:
            return OperationResult(success=True, message="Serviço Samba atualizado com sucesso.")
        return OperationResult(
            success=False,
            message="Falha ao recarregar Samba.",
            error=res.stderr or res.stdout,
        )

    def reload_nfs(self) -> OperationResult:
        """Applies export changes using exportfs -ra."""
        res = _run_cmd(["exportfs", "-ra"])
        if res.returncode == 0:
            return OperationResult(success=True, message="NFS exportfs atualizado com sucesso.")
        return OperationResult(
            success=False,
            message="Falha ao recarregar NFS exports.",
            error=res.stderr or res.stdout,
        )

    # -----------------------------------------------------------------------
    # Samba (SMB/CIFS) Shares
    # -----------------------------------------------------------------------

    def list_smb_shares(self) -> List[SmbShare]:
        """Parses /etc/samba/smb.conf and lists all non-global shares."""
        shares: List[SmbShare] = []
        if not self.smb_conf_path.exists():
            return shares

        cp = configparser.ConfigParser(interpolation=None)
        try:
            cp.read(str(self.smb_conf_path))
        except Exception as e:
            logger.error("Could not parse %s: %s", self.smb_conf_path, e)
            return shares

        for sec in cp.sections():
            if sec.lower() in ("global", "printers", "print$"):
                continue

            sec_data = cp[sec]
            path = sec_data.get("path", "")
            if not path:
                continue

            share = SmbShare(
                name=sec,
                path=path,
                comment=sec_data.get("comment"),
                browseable=sec_data.getboolean("browseable", fallback=True),
                writable=sec_data.getboolean("writable", fallback=True)
                or (sec_data.get("read only", "no").lower() == "no"),
                guest_ok=sec_data.getboolean("guest ok", fallback=False),
                create_mask=sec_data.get("create mask", "0664"),
                directory_mask=sec_data.get("directory mask", "0775"),
                force_user=sec_data.get("force user"),
                force_group=sec_data.get("force group"),
            )
            val_users = sec_data.get("valid users")
            if val_users:
                share.valid_users = [u.strip() for u in val_users.split(",") if u.strip()]

            shares.append(share)

        return shares

    def save_smb_share(self, share: SmbShare) -> OperationResult:
        """Creates or updates a Samba share in smb.conf and reloads the service."""
        Path(share.path).mkdir(parents=True, exist_ok=True)

        cp = configparser.ConfigParser(interpolation=None)
        if self.smb_conf_path.exists():
            try:
                cp.read(str(self.smb_conf_path))
            except Exception:
                pass

        if "global" not in cp:
            cp["global"] = {
                "workgroup": "WORKGROUP",
                "server string": "NayBinho NAS",
                "security": "user",
                "map to guest": "Bad User",
                "dns proxy": "no",
                "log file": "/var/log/samba/log.%m",
                "max log size": "1000",
            }

        share_dict = {
            "path": share.path,
            "browseable": "yes" if share.browseable else "no",
            "writable": "yes" if share.writable else "no",
            "read only": "no" if share.writable else "yes",
            "guest ok": "yes" if share.guest_ok else "no",
            "create mask": share.create_mask,
            "directory mask": share.directory_mask,
        }
        if share.comment:
            share_dict["comment"] = share.comment
        if share.valid_users:
            share_dict["valid users"] = ", ".join(share.valid_users)
        if share.force_user:
            share_dict["force user"] = share.force_user
        if share.force_group:
            share_dict["force group"] = share.force_group

        cp[share.name] = share_dict

        try:
            self.smb_conf_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.smb_conf_path, "w", encoding="utf-8") as f:
                cp.write(f)
            self.reload_smb()
            return OperationResult(
                success=True,
                message=f"Compartilhamento SMB '{share.name}' configurado com sucesso.",
                details={"name": share.name, "path": share.path},
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Erro ao salvar smb.conf: {e}",
                error=str(e),
            )

    def remove_smb_share(self, share_name: str) -> OperationResult:
        """Removes a share section from smb.conf."""
        if not self.smb_conf_path.exists():
            return OperationResult(success=False, message="smb.conf não encontrado")

        cp = configparser.ConfigParser(interpolation=None)
        cp.read(str(self.smb_conf_path))

        if share_name not in cp:
            return OperationResult(
                success=False, message=f"Compartilhamento '{share_name}' não encontrado."
            )

        cp.remove_section(share_name)

        try:
            with open(self.smb_conf_path, "w", encoding="utf-8") as f:
                cp.write(f)
            self.reload_smb()
            return OperationResult(
                success=True,
                message=f"Compartilhamento SMB '{share_name}' removido com sucesso.",
            )
        except Exception as e:
            return OperationResult(success=False, message=str(e), error=repr(e))

    # -----------------------------------------------------------------------
    # Samba User Management
    # -----------------------------------------------------------------------

    def list_samba_users(self) -> List[SambaUser]:
        """Lists users registered in Samba using pdbedit -L."""
        users: List[SambaUser] = []
        res = _run_cmd(["pdbedit", "-L"])
        if res.returncode == 0:
            for line in res.stdout.strip().splitlines():
                if ":" in line:
                    username = line.split(":")[0]
                    users.append(SambaUser(username=username, enabled=True))
        return users

    def set_samba_user_password(self, username: str, password: str) -> OperationResult:
        """Sets Samba password for an existing system user using smbpasswd."""
        proc = subprocess.Popen(
            ["smbpasswd", "-a", username],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(input=f"{password}\n{password}\n")

        if proc.returncode == 0:
            return OperationResult(
                success=True,
                message=f"Usuário Samba '{username}' atualizado com sucesso.",
            )
        return OperationResult(
            success=False,
            message=f"Falha ao cadastrar senha Samba para '{username}'. Certifique-se de que o usuário Linux existe.",
            error=stderr or stdout,
        )

    # -----------------------------------------------------------------------
    # NFS Exports Management (/etc/exports)
    # -----------------------------------------------------------------------

    def list_nfs_exports(self) -> List[NfsExport]:
        """Parses /etc/exports and returns defined exports."""
        exports: List[NfsExport] = []
        if not self.nfs_exports_path.exists():
            return exports

        lines = self.nfs_exports_path.read_text().splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            match = re.match(r"^(\S+)\s+(.+)$", line)
            if match:
                path, clients_str = match.groups()
                client_specs = clients_str.split()
                clients = []
                first_opt = "rw,sync,no_subtree_check"
                for c in client_specs:
                    c_m = re.match(r"^([^\(]+)(?:\((.*)\))?$", c)
                    if c_m:
                        c_host, c_opts = c_m.groups()
                        clients.append(c_host)
                        if c_opts:
                            first_opt = c_opts

                exports.append(
                    NfsExport(
                        path=path,
                        clients=clients,
                        options=first_opt,
                        no_root_squash="no_root_squash" in first_opt,
                        all_squash="all_squash" in first_opt,
                    )
                )

        return exports

    def save_nfs_export(self, export: NfsExport) -> OperationResult:
        """Adds or updates an export in /etc/exports and reloads exportfs."""
        Path(export.path).mkdir(parents=True, exist_ok=True)

        existing = self.list_nfs_exports()
        # Keep exports for different paths
        updated = [e for e in existing if e.path != export.path]
        updated.append(export)

        out_lines = ["# /etc/exports configured by NayBinho NAS"]
        for exp in updated:
            client_rule = ""
            opts = exp.options
            if exp.no_root_squash and "no_root_squash" not in opts:
                opts += ",no_root_squash"
            if exp.all_squash and "all_squash" not in opts:
                opts += ",all_squash"

            targets = exp.clients if exp.clients else ["*"]
            client_rule = " ".join([f"{tgt}({opts})" for tgt in targets])
            out_lines.append(f"{exp.path}    {client_rule}")

        try:
            self.nfs_exports_path.parent.mkdir(parents=True, exist_ok=True)
            self.nfs_exports_path.write_text("\n".join(out_lines) + "\n")
            self.reload_nfs()
            return OperationResult(
                success=True,
                message=f"Exportação NFS para '{export.path}' salva com sucesso.",
                details={"path": export.path, "clients": export.clients},
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Erro ao salvar /etc/exports: {e}",
                error=str(e),
            )

    def remove_nfs_export(self, path: str) -> OperationResult:
        """Removes a path from /etc/exports."""
        if not self.nfs_exports_path.exists():
            return OperationResult(success=False, message="/etc/exports não encontrado.")

        existing = self.list_nfs_exports()
        updated = [e for e in existing if e.path != path]

        out_lines = ["# /etc/exports configured by NayBinho NAS"]
        for exp in updated:
            targets = exp.clients if exp.clients else ["*"]
            client_rule = " ".join([f"{tgt}({exp.options})" for tgt in targets])
            out_lines.append(f"{exp.path}    {client_rule}")

        try:
            self.nfs_exports_path.write_text("\n".join(out_lines) + "\n")
            self.reload_nfs()
            return OperationResult(
                success=True,
                message=f"Export NFS para '{path}' removido com sucesso.",
            )
        except Exception as e:
            return OperationResult(success=False, message=str(e), error=repr(e))

    # -----------------------------------------------------------------------
    # Unified Share Listing
    # -----------------------------------------------------------------------

    def list_all_shares(self) -> List[Share]:
        """Returns unified list of both SMB and NFS shares."""
        unified: List[Share] = []
        for s in self.list_smb_shares():
            unified.append(
                Share(
                    id=f"smb_{s.name}",
                    protocol=ShareProtocol.SMB,
                    name=s.name,
                    path=s.path,
                    state=ShareState.ACTIVE,
                    smb_config=s,
                )
            )

        for n in self.list_nfs_exports():
            unified.append(
                Share(
                    id=f"nfs_{re.sub(r'[^a-zA-Z0-9]', '_', n.path)}",
                    protocol=ShareProtocol.NFS,
                    name=Path(n.path).name or "nfs_root",
                    path=n.path,
                    state=ShareState.ACTIVE,
                    nfs_config=n,
                )
            )

        return unified


share_service = ShareService()
