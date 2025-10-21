#!/bin/bash

# Script para deploy na VPS
echo "🚀 Iniciando deploy do NBA Bot..."

# Criar diretório de logs
mkdir -p logs

# Parar containers existentes
docker-compose down

# Rebuild e iniciar
docker-compose up -d --build

echo "✅ Deploy concluído!"
echo "📊 Containers rodando:"
docker-compose ps