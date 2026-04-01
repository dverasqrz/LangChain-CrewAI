#!/usr/bin/env python3
"""
Script de teste para verificar conexão com Ollama
"""
import os
import requests
import json
from urllib.parse import urljoin

# Carregar configurações do .env se existir
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Obter URL do Ollama da variável de ambiente ou usar placeholder
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Testes de URLs possíveis
urls_to_test = [
    f"https://{ollama_base_url.replace('http://', '').replace('https://', '')}",
    f"https://{ollama_base_url.replace('http://', '').replace('https://', '')}:11434",
    f"http://{ollama_base_url.replace('http://', '').replace('https://', '')}",
    f"http://{ollama_base_url.replace('http://', '').replace('https://', '')}:11434",
]

print("=" * 70)
print("TESTANDO CONEXÃO COM SERVIDORES OLLAMA")
print("=" * 70)

for base_url in urls_to_test:
    api_url = urljoin(base_url, "/api/tags")
    print(f"\n🔍 Testando: {api_url}")

    try:
        response = requests.get(api_url, timeout=5)
        print(f"   ✅ Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            print(f"   📊 Modelos encontrados: {len(models)}")
            if models:
                print("   📋 Primeiros 3 modelos:")
                for model in models[:3]:
                    name = model.get("name", "?")
                    size = model.get("size", 0)
                    size_gb = f"{size / 1e9:.2f} GB" if size > 0 else "?"
                    print(f"      - {name} ({size_gb})")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Erro de conexão: {str(e)[:60]}")
    except requests.exceptions.Timeout:
        print(f"   ⏱️  Timeout (servidor não respondeu)")
    except Exception as e:
        print(f"   ⚠️  Erro: {str(e)[:60]}")

print("\n" + "=" * 70)
print("TESTE AVANÇADO - SIMULANDO CÓDIGO DO STREAMLIT")
print("=" * 70)

# Teste específico simulando o código do service.py
test_configs = [
    {
        "name": "Configuração atual (.env)",
        "base_url": ollama_base_url,
        "api_urls": [
            f"{ollama_base_url}/api/tags",
            f"{ollama_base_url}:11434/api/tags" if ":" not in ollama_base_url.split("://")[1] else f"{ollama_base_url}/api/tags",
        ]
    },
    {
        "name": "Configuração SEM porta (recomendada)",
        "base_url": ollama_base_url.replace(":11434", ""),
        "api_urls": [
            f"{ollama_base_url.replace(':11434', '')}/api/tags"
        ]
    }
]

for config in test_configs:
    print(f"\n🔧 {config['name']}")
    print(f"   Base URL: {config['base_url']}")

    for api_url in config['api_urls']:
        print(f"   🌐 Testando API: {api_url}")
        try:
            # Mesmo timeout que o código usa (10 segundos)
            response = requests.get(api_url, timeout=10)
            print(f"      ✅ Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                print(f"      📊 Modelos: {len(models)}")
                if models:
                    embed_models = [m for m in models if any(k in m.get("name", "").lower() for k in ["embed", "embedding"])]
                    print(f"      🎯 Modelos de embedding: {len(embed_models)}")
                    print("      ✅ SUCESSO! Esta configuração funciona!")
        except requests.exceptions.ConnectionError as e:
            print(f"      ❌ Erro de conexão: {str(e)[:50]}...")
        except requests.exceptions.Timeout:
            print("      ⏱️  Timeout (10s)")
        except Exception as e:
            print(f"      ⚠️  Erro: {str(e)[:50]}...")

print("\n" + "=" * 70)
print("FIM DO TESTE")
print("=" * 70)
