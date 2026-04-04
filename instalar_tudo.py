import os
import subprocess
import sys

def instalar_requirements():
    print("Iniciando varredura por arquivos requirements.txt...\n")
    
    # os.walk percorre a pasta raiz e todas as subpastas
    for pasta_atual, subpastas, arquivos in os.walk("."):
        
        # Previne que o script procure dentro de pastas de ambiente virtual ou git
        pastas_ignoradas = [".venv", "venv", ".git", "__pycache__"]
        for ignorar in pastas_ignoradas:
            if ignorar in subpastas:
                subpastas.remove(ignorar)
                
        if "requirements.txt" in arquivos:
            caminho_arquivo = os.path.join(pasta_atual, "requirements.txt")
            print(f"--> Instalando dependências encontradas em: {caminho_arquivo}")
            
            try:
                # Usa o executável Python do ambiente virtual atual para rodar o pip
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", "-r", caminho_arquivo
                ])
                print(f"[OK] Sucesso ao instalar {caminho_arquivo}\n")
            except subprocess.CalledProcessError:
                print(f"[ERRO] Falha ao instalar as dependências de {caminho_arquivo}\n")
                sys.exit(1)

if __name__ == "__main__":
    instalar_requirements()