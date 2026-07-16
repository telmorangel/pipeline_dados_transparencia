"""
============================================================================================
PROJETO AVALIATIVO - ANÁLISE DE DADOS COM PYTHON [T1]
Módulo 1 - Semana 13 | Módulo de Configurações e Variáveis de Ambiente (config.py)
============================================================================================
Arquivo: config.py
Descrição: 
    Responsável por gerenciar os parâmetros globais do pipeline, mapear os 
    caminhos de diretórios locais (via Pathlib) e realizar a leitura segura 
    das variáveis de ambiente estipuladas no arquivo .env.

Objetivos Pedagógicos e Boas Práticas Atendidas:
    1. Segurança e Boas Práticas (Seção 4): Isolamento absoluto de credenciais
       sensíveis (usuário, senha, host do banco de dados e ID do Google Drive), 
       garantindo que nenhuma chave ou senha fique exposta no código-fonte.
    2. Compatibilidade de Sistema Operacional: Uso da biblioteca Pathlib para
       garantir a resolução automática de caminhos no Windows, Linux ou macOS.
    3. Automação de Infraestrutura: Criação automática do diretório local de 
       armazenamento dos dados extraídos antes da execução das leituras.
=============================================================================================
"""

import os
from pathlib import Path
from sqlalchemy import create_engine

# ==========================================================================================
# 1. RESOLUÇÃO AUTOMÁTICA DE CAMINHOS DO PROJETO (PATHLIB)
# ==========================================================================================
# Descobre dinamicamente a pasta raiz do projeto de forma absoluta, impedindo
# erros de caminho relativo durante a execução no terminal ou em IDEs.
PASTA_RAIZ = Path(__file__).resolve().parent

# Configura o diretório de destino para os arquivos ZIP e CSVs extraídos.
# O parâmetro exist_ok=True cria a pasta 'dados_viagens' automaticamente caso 
# ela ainda não exista no computador do operador.
DADOS_VIAGENS = PASTA_RAIZ / "dados_viagens"
DADOS_VIAGENS.mkdir(exist_ok=True)


# ==============================================================================
# 2. GESTÃO DE SEGURANÇA E VARIÁVEIS DE AMBIENTE (.ENV)
# ==============================================================================
def carregar_env():
    """
    [Requisito - Seção 4] Lê o arquivo local .env e injeta as credenciais e 
    parametros no ambiente operacional do Python (os.environ).
    
    A função ignora comentários (linhas iniciadas em #), remove espaços ou 
    aspas excedentes e protege a aplicação caso o arquivo não seja encontrado.
    """
    arquivo_env = PASTA_RAIZ / ".env"
    if not arquivo_env.exists():
        return

    for linha in arquivo_env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        # Ignora linhas em branco, comentários ou formatações sem sinal de igualdade.
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        # Remove aspas simples ou duplas e define a variável de ambiente de forma limpa.
        os.environ.setdefault(chave.strip(), valor.strip().strip("'").strip('"'))

# Executa o carregamento imediatamente ao importar este módulo[cite: 10].
carregar_env()


# ==============================================================================
# 3. PARÂMETROS E DICIONÁRIOS DE CONEXÃO AO BANCO DE DADOS
# ==============================================================================
# Captura as variáveis de ambiente carregadas, aplicando valores padrão de fallback 
# para garantir que o sistema não quebre por falta de preenchimento básico.
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "1234")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "db_viagens_2025")

# Limpa o identificador do arquivo do Google Drive caso o usuário tenha colado
# a string inteira de atribuição (ex: 'DRIVE_FILE_ID = xxx') por engano.
DRIVE_FILE_ID = os.environ.get("DRIVE_FILE_ID", "").replace("DRIVE_FILE_ID = ", "").strip()

# Dicionário estruturado para injeção direta via desempacotamento (**kwargs)
# no conector nativo psycopg2.
POSTGRES_CONFIG = {
    "host": DB_HOST,
    "port": DB_PORT,
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD
}

# String de conexão formatada no padrão RFC 1738 para o SQLAlchemy:
# Formato: postgresql://usuario:senha@host:porta/nome_do_banco
DB_CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Cria a engine global do SQLAlchemy para consumo dos scripts analíticos.
engine = create_engine(DB_CONNECTION_STRING)