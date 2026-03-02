#!/bin/bash
# Gera /opt/lavalink/application.yml com LavaSrc + yt-dlp
# Uso: bash lavalink/setup_config.sh

# Instalar yt-dlp se não existir
if ! command -v yt-dlp &> /dev/null; then
  echo "📦 Instalando yt-dlp..."
  pip3 install -U yt-dlp
fi

cat > /opt/lavalink/application.yml << 'EOF'
server:
  port: 2333
  address: 0.0.0.0

lavalink:
  plugins:
    - dependency: "com.github.topi314.lavasrc:lavasrc-plugin:4.8.1"
      repository: "https://maven.lavalink.dev/releases"

  server:
    password: "youshallnotpass"
    sources:
      youtube: false
      bandcamp: true
      soundcloud: false
      twitch: true
      vimeo: true
      http: true
      local: false
    bufferDurationMs: 400
    frameBufferDurationMs: 5000
    opusEncodingQuality: 10
    resamplingQuality: LOW
    trackStuckThresholdMs: 10000
    useSeekGhosting: true
    playerUpdateInterval: 5
    gc-warnings: true

plugins:
  lavasrc:
    providers:
      - "ytsearch:%QUERY%"
    sources:
      deezer: false
      spotify: false
      applemusic: false
      yandexmusic: false
      flowerytts: false
      youtube: false
      vkmusic: false
      tidal: false
      qobuz: false
      ytdlp: true
    ytdlp:
      path: "yt-dlp"
      searchLimit: 10

logging:
  level:
    root: INFO
    lavalink: INFO
  request:
    enabled: true
    includeClientInfo: true
    includeHeaders: false
    includeQueryString: true
    includePayload: true
    maxPayloadLength: 10000
EOF

echo "✅ application.yml criado com LavaSrc + yt-dlp"
echo "Reinicie: sudo systemctl restart lavalink"
