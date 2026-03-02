#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
#  install_lavalink.sh — Instalação do Lavalink no VPS
#  Execute como: bash install_lavalink.sh
# ──────────────────────────────────────────────────────────────────────────────
set -e

LAVALINK_VERSION="4.2.1"
LAVALINK_DIR="/opt/lavalink"
LAVALINK_JAR="$LAVALINK_DIR/Lavalink.jar"
BOT_DIR="/root/gatocomics-bot"

echo "=== [1/5] Verificando Java 17+ ==="
if ! java -version 2>&1 | grep -qE 'version "(17|18|19|20|21)'; then
    echo "Java 17+ não encontrado. Instalando OpenJDK 17..."
    apt-get update -qq && apt-get install -y openjdk-17-jdk
fi
java -version

echo "=== [2/5] Criando diretório do Lavalink ==="
mkdir -p "$LAVALINK_DIR/plugins"
mkdir -p "$LAVALINK_DIR/logs"

echo "=== [3/5] Baixando Lavalink $LAVALINK_VERSION ==="
curl -L \
  "https://github.com/lavalink-devs/Lavalink/releases/download/$LAVALINK_VERSION/Lavalink.jar" \
  -o "$LAVALINK_JAR"
echo "JAR baixado: $(du -sh $LAVALINK_JAR | cut -f1)"

echo "=== [4/5] Copiando configuração ==="
cp "$BOT_DIR/lavalink/application.yml" "$LAVALINK_DIR/application.yml"
echo "application.yml copiado."

echo "=== [5/5] Criando serviço systemd ==="
cat > /etc/systemd/system/lavalink.service << 'EOF'
[Unit]
Description=Lavalink Audio Server
After=network.target
Before=gatocomics.service

[Service]
User=root
WorkingDirectory=/opt/lavalink
ExecStart=/usr/bin/java -Xmx512m -jar /opt/lavalink/Lavalink.jar
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable lavalink
systemctl start lavalink

echo ""
echo "═══════════════════════════════════════"
echo " ✅ Lavalink instalado com sucesso!"
echo " Verificando status..."
echo "═══════════════════════════════════════"
sleep 5
systemctl status lavalink --no-pager | head -20
echo ""
echo "Aguarde ~15s para o Lavalink inicializar completamente."
echo "Depois reinicie o bot: sudo systemctl restart gatocomics"
