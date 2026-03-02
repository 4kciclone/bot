#!/bin/bash
# Gera /opt/lavalink/application.yml com o refresh token
# Uso: bash lavalink/setup_config.sh "SEU_REFRESH_TOKEN"

TOKEN="${1:-}"

if [ -z "$TOKEN" ]; then
  echo "Uso: bash lavalink/setup_config.sh \"SEU_REFRESH_TOKEN\""
  exit 1
fi

cat > /opt/lavalink/application.yml << EOF
server:
  port: 2333
  address: 0.0.0.0
  http2:
    enabled: false

lavalink:
  plugins:
    - dependency: "dev.lavalink.youtube:youtube-plugin:1.18.0"
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
    filters:
      volume: true
      equalizer: true
      karaoke: true
      timescale: true
      tremolo: true
      vibrato: true
      distortion: true
      rotation: true
      channelMix: true
      lowPass: true
    bufferDurationMs: 400
    frameBufferDurationMs: 5000
    opusEncodingQuality: 10
    resamplingQuality: LOW
    trackStuckThresholdMs: 10000
    useSeekGhosting: true
    youtubePlaylistLoadLimit: 6
    playerUpdateInterval: 5
    youtubeSearchEnabled: true
    soundcloudSearchEnabled: false
    gc-warnings: true

plugins:
  youtube:
    enabled: true
    allowSearch: true
    allowDirectVideoIds: true
    allowDirectPlaylistIds: true
    clients:
      - TV               # ÚNICO cliente OAuth-compatível (requer login)
      - TVHTML5_SIMPLY   # TV simplificado, não requer login
      - WEB              # Web padrão
      - MUSIC            # YouTube Music (busca)
    oauth:
      enabled: true
      refreshToken: "$TOKEN"

metrics:
  prometheus:
    enabled: false
    endpoint: /metrics

sentry:
  dsn: ""
  environment: ""

logging:
  file:
    path: ./logs/
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

echo "✅ application.yml criado em /opt/lavalink/"
echo "Reinicie: sudo systemctl restart lavalink"
