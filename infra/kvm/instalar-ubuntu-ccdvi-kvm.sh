#!/usr/bin/env bash
# Ubuntu Server 24.04.5 LTS no Rocky Linux/KVM: instalação automatizada via Autoinstall/NoCloud.
# Execute como usuário com sudo: bash instalar-ubuntu-ccdvi-kvm.sh
set -Eeuo pipefail
umask 077

VM='ccdvi-ubuntu-lab'
BRIDGE='br-ex'
RAM_MIB=16384
VCPUS=4
DISK_GIB=80
ISO_NAME='ubuntu-24.04.5-live-server-amd64.iso'
BOOT_DIR='/var/lib/libvirt/boot'
IMAGE_DIR='/var/lib/libvirt/images'
ISO_PATH="${BOOT_DIR}/${ISO_NAME}"
DISK_PATH="${IMAGE_DIR}/${VM}.qcow2"
SEED_PATH="${IMAGE_DIR}/${VM}-seed.iso"
WORK="${HOME}/.ccdvi-autoinstall"
BASE_URL='https://releases.ubuntu.com/24.04'

fail() { printf 'ERRO: %s\n' "$*" >&2; exit 1; }
info() { printf '\n==> %s\n' "$*"; }
trap 'printf "\nInstalação interrompida na linha %s. Verifique a mensagem de erro acima.\n" "$LINENO" >&2' ERR

info 'Verificando pré-requisitos e protegendo recursos existentes'
for cmd in sudo virsh virt-install openssl curl sha256sum awk df; do
  command -v "$cmd" >/dev/null 2>&1 || fail "Comando ausente: $cmd"
done
if command -v genisoimage >/dev/null 2>&1; then
  MKISO='genisoimage'
elif command -v xorriso >/dev/null 2>&1; then
  MKISO='xorriso'
else
  fail 'É necessário genisoimage ou xorriso. Instale uma das ferramentas pelo dnf e execute novamente.'
fi
sudo -v
if sudo virsh dominfo "$VM" >/dev/null 2>&1; then
  fail "Já existe uma VM chamada ${VM}. Não será modificada."
fi
if sudo test -e "$DISK_PATH"; then
  fail "Já existe o disco ${DISK_PATH}. Não será sobrescrito."
fi
if sudo test -e "$SEED_PATH"; then
  fail "Já existe a ISO ${SEED_PATH}. Não será sobrescrita."
fi
ip link show "$BRIDGE" >/dev/null 2>&1 || fail "Bridge ${BRIDGE} inexistente."
ip link show "$BRIDGE" | grep -q 'state UP' || fail "Bridge ${BRIDGE} não está UP."
virt-install --osinfo list 2>/dev/null | grep -F 'ubuntu24.04' >/dev/null || fail 'A instalação atual do virt-install não reconhece ubuntu24.04.'
AVAILABLE_BYTES=$(df -B1 --output=avail "$IMAGE_DIR" | awk 'NR==2 {print $1}')
[ "${AVAILABLE_BYTES:-0}" -ge $((100*1024*1024*1024)) ] || fail 'Menos de 100 GiB disponíveis no pool default; revise o armazenamento antes de prosseguir.'

mkdir -p "$WORK"
chmod 700 "$WORK"

info 'Criando credenciais do Ubuntu (senha não aparece na tela)'
read -r -s -p "Defina uma senha forte (mínimo 12 caracteres) para o usuário 'suporte': " INITIAL_PASSWORD
echo
[ "${#INITIAL_PASSWORD}" -ge 12 ] || fail 'Senha muito curta. O mínimo é 12 caracteres.'
PASSWORD_HASH=$(printf '%s' "$INITIAL_PASSWORD" | openssl passwd -6 -stdin)
unset INITIAL_PASSWORD

cat > "$WORK/user-data" <<EOF
#cloud-config
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: br
    variant: ''
  identity:
    hostname: ${VM}
    username: suporte
    password: '${PASSWORD_HASH}'
  ssh:
    install-server: true
    allow-pw: true
  storage:
    layout:
      name: direct
  apt:
    fallback: offline-install
  refresh-installer:
    update: false
  timezone: America/Sao_Paulo
  shutdown: reboot
EOF
unset PASSWORD_HASH
cat > "$WORK/meta-data" <<EOF
instance-id: ${VM}-autoinstall
local-hostname: ${VM}
EOF
chmod 600 "$WORK/user-data" "$WORK/meta-data"

info 'Gerando ISO NoCloud local (sem depender de HTTP durante a instalação)'
if [ "$MKISO" = 'genisoimage' ]; then
  ( cd "$WORK" && genisoimage -quiet -r -J -V cidata -o "$WORK/seed.iso" user-data meta-data )
else
  ( cd "$WORK" && xorriso -as mkisofs -r -J -V cidata -o "$WORK/seed.iso" user-data meta-data >/dev/null )
fi
sudo install -m 0644 "$WORK/seed.iso" "$SEED_PATH"
sudo restorecon -v "$SEED_PATH" 2>/dev/null || true

info 'Verificando a ISO oficial do Ubuntu Server 24.04.5'
sudo mkdir -p "$BOOT_DIR"
if ! sudo test -s "$ISO_PATH"; then
  sudo curl -fL --retry 3 -o "${ISO_PATH}.part" "${BASE_URL}/${ISO_NAME}"
  sudo mv "${ISO_PATH}.part" "$ISO_PATH"
fi
curl -fLsS --retry 3 "${BASE_URL}/SHA256SUMS" -o "$WORK/SHA256SUMS"
EXPECTED=$(awk -v f="$ISO_NAME" '$2==f || $2=="*"f {print $1; exit}' "$WORK/SHA256SUMS")
[ -n "$EXPECTED" ] || fail 'ISO não encontrada no manifesto oficial SHA256SUMS.'
ACTUAL=$(sudo sha256sum "$ISO_PATH" | awk '{print $1}')
[ "$ACTUAL" = "$EXPECTED" ] || fail 'Falha de integridade SHA256 da ISO do Ubuntu; VM não será criada.'
printf '%s\n' 'ISO validada por SHA256.'

info 'Criando a VM e iniciando o instalador em modo completamente automático'
sudo virt-install \
  --name "$VM" \
  --virt-type kvm \
  --memory "$RAM_MIB" \
  --vcpus "$VCPUS" \
  --cpu host-passthrough \
  --disk "path=${DISK_PATH},size=${DISK_GIB},format=qcow2,bus=virtio" \
  --disk "path=${SEED_PATH},device=cdrom,readonly=on" \
  --location "${ISO_PATH},kernel=casper/vmlinuz,initrd=casper/initrd" \
  --os-variant ubuntu24.04 \
  --network "bridge=${BRIDGE},model=virtio" \
  --graphics none \
  --console pty,target_type=serial \
  --extra-args 'autoinstall console=ttyS0,115200n8' \
  --noautoconsole

printf '\nVM criada. O Ubuntu deverá instalar-se e reiniciar sem perguntas no instalador.\n'
printf 'Acompanhar: sudo virsh list --all\n'
printf 'Diagnóstico (se necessário): sudo virsh console %s\n' "$VM"
printf 'IP após a inicialização: sudo virsh domifaddr %s --source arp\n' "$VM"
printf 'ATENÇÃO: a bridge br-ex ainda não teve DHCP/conectividade IP comprovados.\n'
printf 'O usuário Ubuntu será suporte, com a senha definida no início.\n'
