#!/usr/bin/env python3
"""
Script para facilitar a instalação de dependências por projeto.
Uso: python install_dependencies.py [--project nome] [--all]
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def get_pip_command():
    """Retorna o comando pip correto para o ambiente atual."""
    if os.name == 'nt':  # Windows
        if '.venv' in sys.executable:
            return '.venv\\Scripts\\pip.exe'
        else:
            return 'pip'
    else:  # Linux/Mac
        if '.venv' in sys.executable:
            return '.venv/bin/pip'
        else:
            return 'pip'


def run_command(command, description):
    """Executa um comando e exibe o resultado."""
    print(f"\n🔧 {description}")
    print(f"Comando: {command}")
    print("-" * 50)
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print("✅ Sucesso!")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro: {e}")
        if e.stderr:
            print(f"Detalhes: {e.stderr}")
        return False


def install_global_dependencies():
    """Instala dependências globais."""
    pip_cmd = get_pip_command()
    return run_command(
        f"{pip_cmd} install -r requirements.txt",
        "Instalando dependências globais (Streamlit, etc.)"
    )


def install_marketing_dependencies():
    """Instala dependências do projeto de Marketing."""
    pip_cmd = get_pip_command()
    return run_command(
        f"{pip_cmd} install -r marketing/requirements.txt",
        "Instalando dependências do projeto de Marketing"
    )


def install_suporte_dependencies():
    """Instala dependências do projeto de Suporte e Atendimento."""
    pip_cmd = get_pip_command()
    return run_command(
        f"{pip_cmd} install -r suporte_atendimento/requirements.txt",
        "Instalando dependências do projeto de Suporte e Atendimento"
    )


def list_available_projects():
    """Lista os projetos disponíveis."""
    print("\n📁 Projetos disponíveis:")
    print("-" * 30)
    
    projects = []
    
    # Verificar se existem requirements específicos
    if Path("marketing/requirements.txt").exists():
        projects.append("marketing")
        print("📢 marketing - Geração de conteúdo de marketing")
    
    if Path("suporte_atendimento/requirements.txt").exists():
        projects.append("suporte")
        print("🎧 suporte - Sistema de atendimento com RAG")
    
    if not projects:
        print("❌ Nenhum projeto específico encontrado.")
    
    return projects


def main():
    parser = argparse.ArgumentParser(
        description="Instala dependências do projeto LangChain/CrewAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python install_dependencies.py --all           # Instala tudo
  python install_dependencies.py --project marketing  # Instala apenas marketing
  python install_dependencies.py --list          # Lista projetos disponíveis
        """
    )
    
    parser.add_argument(
        "--project", "-p",
        help="Projeto específico para instalar (marketing, suporte)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Instalar dependências de todos os projetos"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Listar projetos disponíveis"
    )
    
    args = parser.parse_args()
    
    print("🚀 Instalador de Dependências - LangChain/CrewAI")
    print("=" * 60)
    
    if args.list:
        list_available_projects()
        return
    
    # Sempre instalar dependências globais primeiro
    if not install_global_dependencies():
        print("\n❌ Falha ao instalar dependências globais. Abortando.")
        sys.exit(1)
    
    success = True
    
    if args.all:
        print("\n🔄 Instalando todos os projetos...")
        if not install_marketing_dependencies():
            success = False
        if not install_suporte_dependencies():
            success = False
    
    elif args.project:
        project = args.project.lower()
        
        if project in ["marketing", "mark"]:
            if not install_marketing_dependencies():
                success = False
        
        elif project in ["suporte", "support", "atendimento"]:
            if not install_suporte_dependencies():
                success = False
        
        else:
            print(f"\n❌ Projeto '{project}' não reconhecido.")
            print("Use --list para ver projetos disponíveis.")
            success = False
    
    else:
        print("\n📋 Nenhum projeto especificado.")
        print("Use --all para instalar tudo ou --project <nome> para um projeto específico.")
        print("Use --list para ver projetos disponíveis.")
        return
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Instalação concluída com sucesso!")
        print("\nPara rodar a aplicação:")
        print("  streamlit run app.py")
        print("\nPara rodar um projeto específico:")
        print("  streamlit run pages/3_marketing.py")
        print("  streamlit run pages/6_suporte_atendimento.py")
    else:
        print("⚠️ Alguns projetos não foram instalados. Verifique os erros acima.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
