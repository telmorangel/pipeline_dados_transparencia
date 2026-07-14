"""
===============================================================================
PROJETO AVALIATIVO - ANÁLISE DE DADOS COM PYTHON [T1]
Módulo 1 - Semana 13 | Arquitetura Medallion (Fase 1: Camada Raw)
===============================================================================
Arquivo: 1_extrair.py
Descrição: 
    Responsável pela ingestão automatizada de dados abertos de Viagens a 
    Serviço do Portal da Transparência. O script realiza o download do 
    arquivo ZIP no Google Drive, descompacta os arquivos CSV locais, efetua a
    leitura em blocos (chunks) e carrega os dados nas tabelas da Camada Raw 
    do banco PostgreSQL sem alterar o conteúdo original.

Objetivos Pedagógicos e Requisitos Atendidos:
    1. Extração Automatizada (Critério 3): Download direto da fonte oficial
       através do DRIVE_FILE_ID sem necessidade de intervenção manual.
    2. Resiliência (Critério 3): Estruturação de tratamento de exceções com 
       blocos try/except para capturar e registrar falhas no pipeline.
    3. Idempotência (Critério 3): Limpeza prévia (TRUNCATE) das tabelas Raw 
       para evitar duplicidade de registros em reexecuções do script.
    4. Cópia Fiel do Dado Bruto (Seções 4 e 5.3): Manutenção de todas as colunas
       no tipo VARCHAR (texto), preservando vírgulas, datas e colunas extras 
       para fins de rastreabilidade e auditoria futura.
    5. Otimização de Memória: Leitura de grandes volumes (6 meses de 2025) 
       utilizando chunksize no Pandas.
===============================================================================
"""

import zipfile
import logging
import pandas as pd
import gdown

from config import DADOS_VIAGENS, DRIVE_FILE_ID
from banco import conectar, executar, obter_engine

# ==============================================================================
# CONFIGURAÇÃO DE LOGS (MONITORAMENTO DO PIPELINE)
# ==============================================================================
# Boas Práticas: Utilização da biblioteca logging para substituição de prints 
# simples, permitindo rastrear carimbos de tempo (timestamp), níveis de severidade
# (INFO, WARNING, ERROR) e auditar a execução de ponta a ponta.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# ==============================================================================
# MAPEAMENTO ESPELHADO DE COLUNAS (CSV BRUTO -> SQL RAW)
# ==============================================================================
# Seção 5.3 e 5.4: Dicionário relacionando os cabeçalhos originais dos arquivos 
# CSV aos nomes padronizados das colunas nas tabelas da Camada Raw.
# Nota: A Camada Raw replica o CSV inteiro, incluindo colunas que a Silver 
# não usa (ex: cpf_viajante, funcao, dados de volta da passagem).
MAPEAMENTO_COLUNAS = {
    "raw_viagem": {
        "identificador do processo de viagem": "id_viagem",
        "número da proposta (pcdp)": "num_proposta",
        "situação": "situacao",
        "viagem urgente": "viagem_urgente",
        "código do órgão superior": "cod_orgao_superior",
        "nome do órgão superior": "nome_orgao_superior",
        "cpf viajante": "cpf_viajante",
        "nome": "nome_viajante",
        "nome do viajante": "nome_viajante",
        "função": "funcao",
        "cargo": "cargo",
        "período - data de início": "data_inicio",
        "período - data de fim": "data_fim",
        "destinos": "destinos",
        "motivo": "motivo",
        "valor diárias": "valor_diarias",
        "valor passagens": "valor_passagens",
        "valor devolução": "valor_devolucao",
        "valor outros gastos": "valor_outros_gastos"
    },
    "raw_passagem": {
        "identificador do processo de viagem": "id_viagem",
        "meio de transporte": "meio_transporte",
        "país - origem ida": "pais_origem_ida",
        "uf - origem ida": "uf_origem_ida",
        "cidade - origem ida": "cidade_origem_ida",
        "país - destino ida": "pais_destino_ida",
        "uf - destino ida": "uf_destino_ida",
        "cidade - destino ida": "cidade_destino_ida",
        "valor da passagem": "valor_passagem",
        "taxa de serviço": "taxa_servico",
        "data da emissão/compra": "data_emissao",
        "dados de volta da passagem": "dados_volta_passagem"
    },
    "raw_pagamento": {
        "identificador do processo de viagem": "id_viagem",
        "número da proposta (pcdp)": "num_proposta",
        "nome do órgão pagador": "nome_orgao_pagador",
        "nome da unidade gestora pagadora": "nome_ug_pagadora",
        "tipo de pagamento": "tipo_pagamento",
        "valor": "valor"
    },
    "raw_trecho": {
        "identificador do processo de viagem": "id_viagem",
        "sequência trecho": "sequencia_trecho",
        "origem - data": "origem_data",
        "origem - uf": "origem_uf",
        "origem - cidade": "origem_cidade",
        "destino - data": "destino_data",
        "destino - uf": "destino_uf",
        "destino - cidade": "destino_cidade",
        "meio de transporte": "meio_transporte",
        "número diárias": "numero_diarias"
    }
}

# Relacionamento dos 4 arquivos CSV contidos no arquivo ZIP às tabelas alvo.
ARQUIVOS_ALVO = {
    "2025_Viagem.csv": "raw_viagem",
    "2025_Passagem.csv": "raw_passagem",
    "2025_Pagamento.csv": "raw_pagamento",
    "2025_Trecho.csv": "raw_trecho"
}


def baixar_e_extrair_zip():
    """
    [Critério 3] Realiza o download automatizado do arquivo ZIP do Google Drive
    e extrai o conteúdo no diretório local configurado sem intervenção manual.
    """
    caminho_zip = DADOS_VIAGENS / "viagens_2025.zip"
    
    # Boas práticas: Validação de segurança para garantir a leitura do arquivo .env.
    if not DRIVE_FILE_ID:
        raise ValueError("DRIVE_FILE_ID não foi encontrado ou está vazio no arquivo .env!")

    logging.info(f"Iniciando download automatizado do Google Drive (ID: {DRIVE_FILE_ID})...")
    url = f"https://drive.google.com/uc?id={DRIVE_FILE_ID}"
    
    try:
        # Requisita o download via gdown e descompacta os CSVs.
        gdown.download(url, str(caminho_zip), quiet=False)
        logging.info("Download concluído com sucesso!")
        
        with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
            zip_ref.extractall(DADOS_VIAGENS)
        logging.info(f"Arquivos CSV extraídos com sucesso em: {DADOS_VIAGENS}")
        
    except Exception as e:
        # [Critério 3] Resiliência: Captura e registro de falhas na extração[cite: .
        logging.error(f"Erro durante o download ou descompactação do arquivo ZIP: {e}")
        raise


def truncar_tabelas_raw():
    """
    [Critério 3 - Idempotência] Limpa todas as tabelas da Camada Raw no banco
    de dados antes de iniciar a carga, impedindo a duplicação em reexecuções.
    """
    logging.info("Truncando tabelas da Camada Raw (Garantia de Idempotência)...")
    try:
        conexao = conectar()
        tabelas = list(ARQUIVOS_ALVO.values())
        for tabela in tabelas:
            # O RESTART IDENTITY zera contadores sequenciais e o CASCADE limpa dependências.
            executar(conexao, f"TRUNCATE TABLE {tabela} RESTART IDENTITY CASCADE;")
            logging.info(f"✔ Tabela Raw '{tabela}' esvaziada com sucesso.")
        conexao.close()
    except Exception as e:
        logging.error(f"Erro ao tentar truncar as tabelas Raw: {e}")
        raise


def carregar_csv_para_raw(nome_arquivo_csv, tabela_destino, chunksize=10000):
    """
    [Seções 4 e 5.3] Lê o CSV em blocos (chunks) e carrega na tabela Raw do PostgreSQL.
    Os dados são mantidos exatamente como texto (dtype=str) preservando o histórico original.
    """
    caminho_csv = DADOS_VIAGENS / nome_arquivo_csv
    
    # Tratamento de caminho: Localiza o CSV caso a extração tenha gerado subpastas.
    if not caminho_csv.exists():
        encontrados = list(DADOS_VIAGENS.rglob(nome_arquivo_csv))
        if encontrados:
            caminho_csv = encontrados[0]
        else:
            logging.warning(f"Arquivo '{nome_arquivo_csv}' não encontrado em {DADOS_VIAGENS}. Pulando carga...")
            return

    logging.info(f"Iniciando leitura em blocos ({chunksize} linhas): {nome_arquivo_csv} ➔ {tabela_destino}")
    engine = obter_engine()
    mapa_colunas = MAPEAMENTO_COLUNAS.get(tabela_destino, {})

    try:
        # [Seção 5.3] Leitura preservando todas as colunas como string (dtype=str),
        # mantendo vírgulas decimais, formatos de data DD/MM/AAAA e colunas extras.
        leitor_csv = pd.read_csv(
            caminho_csv,
            sep=';',
            encoding='latin-1',
            dtype=str,
            chunksize=chunksize,
            on_bad_lines='skip'
        )

        total_linhas = 0
        for i, chunk in enumerate(leitor_csv, start=1):
            # Normalização de cabeçalhos para minúsculas e remoção de espaços extras
            chunk.columns = [col.strip().lower() for col in chunk.columns]
            
            # Renomeação das colunas do CSV para os nomes de atributos do banco SQL
            chunk = chunk.rename(columns=mapa_colunas)
            
            # Criação de identificadores sequenciais na memória caso a tabela exija
            if tabela_destino in ['raw_trecho', 'raw_pagamento', 'raw_passagem'] and f"id_{tabela_destino.split('_')[1]}" not in chunk.columns:
                col_id = f"id_{tabela_destino.split('_')[1]}"
                chunk.insert(0, col_id, range(total_linhas + 1, total_linhas + 1 + len(chunk)))
                chunk[col_id] = chunk[col_id].astype(str)

            # Filtra estritamente as colunas mapeadas na estrutura do banco de dados
            colunas_existentes = [col for col in chunk.columns if col in mapa_colunas.values() or col.startswith('id_')]
            chunk = chunk[colunas_existentes]

            # Carga em lotes no PostgreSQL utilizando a engine do SQLAlchemy
            chunk.to_sql(
                name=tabela_destino,
                con=engine,
                if_exists='append',
                index=False,
                method='multi',
                chunksize=2000
            )
            
            total_linhas += len(chunk)
            logging.info(f"[{tabela_destino}] Bloco {i} processado ➔ Acumulado: {total_linhas:,} linhas.")

        logging.info(f"✔ Carga finalizada: '{nome_arquivo_csv}' ({total_linhas:,} linhas carregadas na Raw).")

    except Exception as e:
        # [Critério 3] Resiliência durante a leitura e processamento de blocos de dados.
        logging.error(f"Erro crítico no processamento do arquivo '{nome_arquivo_csv}': {e}")
        raise


def executar_pipeline_extracao():
    """
    Orquestrador Principal da Fase 1 (Extração e Camada Raw).
    Controla o fluxo de execução: Download ➔ Limpeza Idempotente ➔ Carga dos CSVs.
    """
    logging.info("===================================================================")
    print("      PIPELINE DE DADOS - FASE 1: EXTRAÇÃO E CAMADA RAW            ")
    logging.info("===================================================================")
    try:
        # 1. Download e descompactação dos arquivos do Portal da Transparência
        baixar_e_extrair_zip()
        
        # 2. Limpeza prévia para garantir idempotência em execuções repetidas
        truncar_tabelas_raw()
        
        # 3. Leitura otimizada em blocos e inserção de cada arquivo na Camada Raw
        for csv_file, tabela_sql in ARQUIVOS_ALVO.items():
            carregar_csv_para_raw(csv_file, tabela_sql, chunksize=15000)
            
        logging.info("===================================================================")
        logging.info(" 🏆 FASE 1 CONCLUÍDA! Dados brutos carregados na Camada Raw (Bronze).")
        logging.info("===================================================================\n")
    except Exception as erro_fatal:
        logging.critical(f"❌ Pipeline de extração interrompido por falha crítica: {erro_fatal}")
        raise


if __name__ == "__main__":
    executar_pipeline_extracao()