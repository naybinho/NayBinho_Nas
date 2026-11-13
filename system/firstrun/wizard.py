#!/usr/bin/env python3
"""
NayBinho NAS — Assistente de Primeira Inicialização (First Run Wizard)
Executado no primeiro acesso ou via CLI para configurar:
- Hostname do sistema
- Senha do administrador (admin)
- Configuração de rede (DHCP ou IP Estático)
- Fuso horário (Timezone) e NTP
"""

import sys
import os
import subprocess
import shutil
import json
import re

FIRST_RUN_FLAG = "/etc/naybinho/.initialized"
CONFIG_FILE = "/etc/naybinho/system.json"

def run_command(cmd, check=True):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[-] Erro ao executar comando: {cmd}\nDetalhes: {e.stderr}", file=sys.stderr)
        return None

def is_already_initialized():
    return os.path.exists(FIRST_RUN_FLAG)

def set_hostname(hostname):
    hostname = hostname.strip().lower()
    if not re.match(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$", hostname):
        raise ValueError("Hostname inválido. Use letras minúsculas, números e hífens.")
    print(f"[+] Definindo hostname para: {hostname}")
    run_command(f"hostnamectl set-hostname {hostname}")
    # Atualiza /etc/hosts
    hosts_path = "/etc/hosts"
    if os.path.exists(hosts_path):
        try:
            with open(hosts_path, "r") as f:
                content = f.read()
            # Substitui linha 127.0.1.1
            if "127.0.1.1" in content:
                content = re.sub(r"127\.0\.1\.1\s+.*", f"127.0.1.1\t{hostname}", content)
            else:
                content += f"\n127.0.1.1\t{hostname}\n"
            with open(hosts_path, "w") as f:
                f.write(content)
        except Exception as e:
            print(f"[!] Aviso ao atualizar /etc/hosts: {e}")
    return True

def set_admin_password(password):
    if len(password) < 8:
        raise ValueError("A senha do administrador deve conter no mínimo 8 caracteres.")
    print("[+] Atualizando senha da conta 'admin' no sistema operacional e Samba...")
    # Atualiza senha Linux
    proc = subprocess.Popen(["chpasswd"], stdin=subprocess.PIPE, text=True)
    proc.communicate(input=f"admin:{password}\n")
    # Atualiza senha Samba se o smbpasswd estiver instalado
    if shutil.which("smbpasswd"):
        smb_proc = subprocess.Popen(["smbpasswd", "-a", "admin", "-s"], stdin=subprocess.PIPE, text=True)
        smb_proc.communicate(input=f"{password}\n{password}\n")
    return True

def set_timezone(tz):
    print(f"[+] Configurando fuso horário para: {tz}")
    run_command(f"timedatectl set-timezone {tz}")
    # Ativa sincronização NTP
    run_command("timedatectl set-ntp true")
    return True

def configure_network(interface, mode="dhcp", ip=None, netmask="24", gateway=None, dns=None):
    print(f"[+] Configurando interface de rede {interface} em modo {mode.upper()}...")
    netplan_dir = "/etc/netplan"
    os.makedirs(netplan_dir, exist_ok=True)
    cfg_file = os.path.join(netplan_dir, "01-naybinho-network.yaml")

    if mode.lower() == "dhcp":
        netplan_yaml = f"""# Gerado pelo Assistente NayBinho NAS
network:
  version: 2
  renderer: networkd
  ethernets:
    {interface}:
      dhcp4: true
      dhcp6: false
"""
    else:
        dns_servers = [d.strip() for d in dns.split(",")] if dns else ["1.1.1.1", "8.8.8.8"]
        dns_formatted = "\n          - ".join(dns_servers)
        netplan_yaml = f"""# Gerado pelo Assistente NayBinho NAS
network:
  version: 2
  renderer: networkd
  ethernets:
    {interface}:
      dhcp4: false
      dhcp6: false
      addresses:
        - {ip}/{netmask}
      routes:
        - to: default
          via: {gateway}
      nameservers:
        addresses:
          - {dns_formatted}
"""

    with open(cfg_file, "w") as f:
        f.write(netplan_yaml)

    run_command("netplan apply")
    return True

def finish_wizard(config_data):
    os.makedirs("/etc/naybinho", exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        # Não armazena senha em texto claro no JSON de configuração
        safe_data = {k: v for k, v in config_data.items() if k != "admin_password"}
        json.dump(safe_data, f, indent=2)

    with open(FIRST_RUN_FLAG, "w") as f:
        f.write("NayBinho NAS Initialized Successfully\n")
    print("\n[🎉] Assistente de configuração inicial concluído com sucesso!")

def interactive_cli():
    print("=" * 60)
    print("   🏠 BEM-VINDO AO ASSISTENTE INICIAL DO NAYBINHO NAS")
    print("=" * 60)

    if is_already_initialized():
        print("[!] Este sistema já foi inicializado anteriormente.")
        ans = input("Deseja reexecutar a configuração? (s/N): ").strip().lower()
        if ans != 's':
            sys.exit(0)

    # 1. Hostname
    hostname = input("\n1. Digite o Hostname desejado [naybinho-nas]: ").strip() or "naybinho-nas"
    set_hostname(hostname)

    # 2. Senha Admin
    while True:
        pwd1 = input("\n2. Digite a nova senha do administrador (mín. 8 caracteres): ").strip()
        pwd2 = input("   Confirme a senha: ").strip()
        if pwd1 != pwd2:
            print("[-] As senhas não conferem. Tente novamente.")
            continue
        try:
            set_admin_password(pwd1)
            break
        except ValueError as e:
            print(f"[-] {e}")

    # 3. Timezone
    tz = input("\n3. Fuso Horário [America/Sao_Paulo]: ").strip() or "America/Sao_Paulo"
    set_timezone(tz)

    # 4. Rede
    interfaces = [i for i in os.listdir("/sys/class/net/") if i != "lo"]
    default_iface = interfaces[0] if interfaces else "eth0"
    iface = input(f"\n4. Selecione a interface de rede [{default_iface}]: ").strip() or default_iface
    net_mode = input("   Modo de endereçamento (dhcp / estatico) [dhcp]: ").strip().lower() or "dhcp"

    if net_mode == "estatico":
        ip = input("   Endereço IPv4 (ex: 192.168.1.100): ").strip()
        netmask = input("   Prefixo CIDR [24]: ").strip() or "24"
        gateway = input("   Gateway padrão (ex: 192.168.1.1): ").strip()
        dns = input("   Servidores DNS [1.1.1.1, 8.8.8.8]: ").strip() or "1.1.1.1, 8.8.8.8"
        configure_network(iface, mode="estatico", ip=ip, netmask=netmask, gateway=gateway, dns=dns)
    else:
        configure_network(iface, mode="dhcp")

    finish_wizard({
        "hostname": hostname,
        "timezone": tz,
        "interface": iface,
        "mode": net_mode
    })

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--api-apply":
        # Recebe configuração via stdin em formato JSON
        raw_json = sys.stdin.read()
        data = json.loads(raw_json)
        if "hostname" in data:
            set_hostname(data["hostname"])
        if "admin_password" in data:
            set_admin_password(data["admin_password"])
        if "timezone" in data:
            set_timezone(data["timezone"])
        if "network" in data:
            n = data["network"]
            configure_network(
                n.get("interface", "eth0"),
                n.get("mode", "dhcp"),
                n.get("ip"),
                n.get("netmask", "24"),
                n.get("gateway"),
                n.get("dns")
            )
        finish_wizard(data)
    else:
        interactive_cli()
