"""
===============================================================================
PROJETO AVALIATIVO - ANÁLISE DE DADOS COM PYTHON [T1]
Módulo 1 - Semana 13 | Módulo de Conexão e Execução SQL (banco.py)
===============================================================================
Arquivo: banco.py
Descrição: 
    Módulo responsável por isolar e gerenciar a conectividade com o banco de 
    dados PostgreSQL, fornecendo funções utilitárias nativas (via psycopg2) e 
    motores de integração de alto nível (via SQLAlchemy) para o Pandas.

Objetivos Pedagógicos e Boas Práticas Atendidas:
    1. Modularização e PEP-8 (Seção 4): Separação clara de responsabilidades,
       evitando a repetição de código de conexão nos scripts de ETL.
    2. Resiliência e Tratamento de Exceções (Critério 3): Captura explícita de
       erros operacionais de banco de dados, retornando mensagens claras para
       facilitar a auditoria e depuração.
    3. Performance em Lote: Estruturação de funções otimizadas (executemany)
       para inserções massivas e criação de engine para processamento em blocos.
===============================================================================
"""

import psycopg2
from psycopg2 import Error
from sqlalchemy import create_engine
from config import POSTGRES_CONFIG, DB_CONNECTION_STRING


def conectar():
    """
    [Boas Práticas] Abre e retorna uma conexão nativa com o banco PostgreSQL.
    """
    try:
        return psycopg2.connect(
            host=str(POSTGRES_CONFIG["host"]),
            database=str(POSTGRES_CONFIG["dbname"]),
            user=str(POSTGRES_CONFIG["user"]),
            password=str(POSTGRES_CONFIG["password"]),
            port=str(POSTGRES_CONFIG["port"]),
        )
    except Error as erro:
        # [Critério 3] Resiliência na captura de falhas de conectividade.
        raise RuntimeError(
            f"❌ Não foi possível conectar ao PostgreSQL em {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']} / "
            f"database '{POSTGRES_CONFIG['dbname']}'. Erro detalhado: {erro}"
        )


def executar(conexao, sql):
    """
    Executa comandos SQL DDL ou DML simples no banco de dados.
    
    Ideal para rotinas de estrutura e controle do pipeline, como TRUNCATE, 
    CREATE TABLE, DROP TABLE ou queries nativas de transformação sem retorno.
    
    Args:
        conexao (psycopg2.connection): Instância de conexão ativa com o banco.
        conexao_sql (str): Instrução SQL em texto a ser executada no servidor.
    """
    # O uso do gerenciador de contexto (with) garante o fechamento seguro do cursor.
    with conexao.cursor() as cursor:
        cursor.execute(sql)
    # Efetiva a transação no banco de dados garantindo durabilidade das mudanças.
    conexao.commit()


def inserir_em_lote(conexao, sql_insert, linhas):
    """
    Insere múltiplas linhas simultaneamente de forma otimizada via executemany.
    
    Evita o gargalo de performance de loops com inserções linha por linha,
    enviando matrizes de dados em um único pacote transacional ao servidor.
    
    Args:
        conexao (psycopg2.connection): Conexão ativa com o banco.
        sql_insert (str): Query parametrizada de INSERT (ex: "INSERT INTO t VALUES (%s, %s)").
        linhas (list of tuples): Lista contendo as tuplas com os valores a serem gravados.
    """
    # Proteção de fluxo: Retorna silenciosamente se a lista de dados estiver vazia.
    if not linhas:
        return
    with conexao.cursor() as cursor:
        cursor.executemany(sql_insert, linhas)
    conexao.commit()


def obter_engine():
    """
    Cria e retorna o motor (Engine) de conexão de alto nível do SQLAlchemy.
    
    Indispensável para a integração com o Pandas na Arquitetura Medallion, 
    permitindo o uso dos métodos de leitura e gravação em blocos (.read_sql e .to_sql).
    
    Returns:
        sqlalchemy.engine.Engine: Motor de conexão configurado para o PostgreSQL.
    """
    return create_engine(DB_CONNECTION_STRING)