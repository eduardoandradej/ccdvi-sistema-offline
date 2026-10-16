# Runbook — Criação automatizada de VM Ubuntu Server no KVM/Rocky Linux

**Projeto:** CCDVI — Sistema DVI Offline  
**Cenário:** laboratório de desenvolvimento e demonstração  
**Hospedeiro:** Rocky Linux com libvirt/QEMU/KVM  
**Convidado:** Ubuntu Server 24.04.5 LTS  
**Método:** Autoinstall/NoCloud, sem interação com o instalador gráfico

> **Atenção:** este roteiro prepara uma **VM nova**. Não execute o script novamente sobre uma
> VM existente. A instalação formata o disco da VM nova e não deve afetar as VMs RHCSA
> `bastion`, `servera` e `serverb`.

## 1. Arquitetura utilizada

| Recurso | Configuração |
|---|---|
| Nome | `ccdvi-ubuntu-lab` |
| CPU | 4 vCPUs (`host-passthrough`) |
| RAM | 16 GiB |
| Disco | 80 GiB em qcow2 |
| Pool | `default` (`/var/lib/libvirt/images`) |
| Bridge | `br-ex` |
| IP | DHCP na LAN (pode mudar) |
| Usuário Ubuntu | `suporte` (senha informada na execução) |
| SSH | OpenSSH instalado |

A bridge `br-ex` é utilizada quando já está operacional no hospedeiro. No laboratório de
referência ela estava ligada à interface `enp2s0f0`. Confirme a configuração real
antes de reutilizar o procedimento em outro servidor.

## 2. Diagnóstico não destrutivo no Rocky Linux

```bash
sudo virsh list --all
sudo virsh pool-list --all
sudo virsh pool-dumpxml default
nmcli -f NAME,TYPE,DEVICE connection show --active
bridge link show master br-ex
ip -4 route
free -h
df -hT /var/lib/libvirt/images
command -v virt-install
command -v genisoimage || command -v xorriso
```

**Critérios:** `br-ex` ativa e com caminho de rede testado, espaço livre suficiente
(no script: mínimo de **100 GiB**), recursos disponíveis e `virt-install` reconhecendo
`ubuntu24.04`. Um ARP `REACHABLE` para o gateway comprova a camada 2,
**não** garante acesso IP ou DHCP. Não altere as conexões de rede do hospedeiro
às cegas.

## 3. Guardas de segurança antes do provisionamento

```bash
# Executar no Rocky Linux
sudo virsh dominfo ccdvi-ubuntu-lab
sudo ls -lh /var/lib/libvirt/images/ccdvi-ubuntu-lab.qcow2
sudo ls -lh /var/lib/libvirt/images/ccdvi-ubuntu-lab-seed.iso
```

Se a VM ou um desses arquivos existir, **não execute** o provisionamento.
O script também contém travas que recusam sobrescrevê-los.

## 4. Executar o script no hospedeiro

Copie `infra/kvm/instalar-ubuntu-ccdvi-kvm.sh` para o Rocky Linux, ou use o
repositório local de origem. Exemplo, no Rocky Linux após clonar o repositório:

```bash
cd ~/ccdvi-sistema-offline
bash infra/kvm/instalar-ubuntu-ccdvi-kvm.sh
```

O script:

1. Valida comandos, a bridge e o espaço livre.
2. Solicita a senha **inicial** de `suporte`, sem ecoá-la no terminal.
3. Gera dados `user-data`/`meta-data` do Autoinstall e ISO NoCloud.
4. Baixa, caso necessário, a ISO oficial do Ubuntu e compara SHA-256 com o
   manifesto publicado pelo Ubuntu.
5. Cria uma VM nova e inicia o instalador com o parâmetro `autoinstall`.
6. Deixa a instalação em andamento em segundo plano; **o retorno do script não
   prova que o Ubuntu terminou de instalar**.

A instalação do Ubuntu não exige respostas na tela, mas **a execução inicial
solicita a senha de administrador**. Não armazene essa senha em Git, script ou README.

## 5. Acompanhar e validar

```bash
# No Rocky Linux
sudo virsh list --all
sudo virsh console ccdvi-ubuntu-lab
```

Pressione `Enter` para atualizar o console, se necessário. Para sair do console
sem desligar a VM, utilize `Ctrl+]`.

Quando o Ubuntu mostrar o prompt de login, autentique-se com `suporte` e execute:

```bash
hostnamectl
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS
free -h
ip -br addr
ip -4 route
systemctl status ssh.socket --no-pager
sudo ss -lntp | grep ':22'
```

No Ubuntu 24.04, o SSH pode usar **ativação por socket**; nesse caso,
`ssh.service` aparecer como `inactive` isoladamente não indica falha.
Verifique se `ssh.socket` está em `active (listening)` e teste uma conexão real.

A bridge pode impedir que `virsh domifaddr --source arp` mostre o IP. Se o
resultado for vazio, identifique o endereço com `ip -br addr` **dentro do Ubuntu**.
O endereço DHCP observado no laboratório foi `192.168.10.92`, mas não é fixo.

No Rocky Linux ou estação administrativa:

```bash
ssh suporte@<IP_ATUAL_DA_VM>
```

## 6. Após a instalação — ajustes e recuperação

Antes dos runbooks dos aplicativos:

- Atualize o Ubuntu e verifique a necessidade de reinicialização.
- Confirme SSH, DNS, horário/NTP, espaço e firewall sem bloquear o acesso remoto.
- Prefira reserva DHCP para estabilizar o IP da VM.
- Faça um backup inicial consistente da VM **desligada** antes de instalar aplicações.
- Proteja e elimine, quando não forem mais necessários, os arquivos NoCloud
  gerados: eles incluem um **hash da senha inicial**. Verifique antes se a ISO
  ainda está anexada à VM, para não apagar um arquivo em uso.
- Nunca versione ISO, `.qcow2`, arquivos `.env`, `user-data` ou `seed.iso`.

O backup do disco qcow2 e o snapshot devem ser planejados considerando o espaço
livre no SSD e a existência de outros volumes da VM. Não copie um disco
ativo sem uma estratégia de consistência.

## 7. Ordem dos runbooks CCDVI

1. **Este runbook** — Rocky Linux/KVM e Ubuntu instalado.
2. **[Runbook do Sistema DVI Offline](../../Runbook_Instalacao_Ubuntu_CCDVI_Sistema.txt)** — PostgreSQL, API, interface e `ccdvi.service`.
3. **[CCDVI Drive Offline](https://github.com/eduardoandradej/ccdvi-drive-offline)** — seu próprio runbook e serviços Quadlet.

Ambos os projetos são demonstrativos e devem usar somente dados fictícios.

## 8. Referências

- [Autoinstall Ubuntu Server](https://canonical-subiquity.readthedocs-hosted.com/en/latest/intro-to-autoinstall.html)
- [Referência de configuração Autoinstall](https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html)
- [Projeto do Sistema DVI Offline](https://github.com/eduardoandradej/ccdvi-sistema-offline)
