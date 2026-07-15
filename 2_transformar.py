"""
===============================================================================
PROJETO AVALIATIVO - ANÁLISE DE DADOS COM PYTHON [T1]
Módulo 1 - Semana 13 | Arquitetura Medallion (Fase 2: Camada Silver)
===============================================================================
Arquivo: 2_transformar.py
Descrição: 
    Responsável por realizar a leitura dos dados brutos (Camada Raw/Bronze),
    aplicar técnicas de limpeza, conversão de tipos de dados (tipagem correta),
    garantir a integridade referencial entre as tabelas e carregar as 
    informações na Camada Silver.

Objetivos Pedagógicos e Requisitos Atendidos:
    1. Tipagem e Limpeza (Critério 4): Conversão robusta de textos para valores 
       monetários (DECIMAL/NUMERIC) e datas (DATE), eliminando formatos falsos.
    2. Colunas Calculadas (Seção 4): Criação e cálculo automático das colunas 
       derivadas 'valor_total' e 'duracao_dias' na tabela principal.
    3. Modelagem Relacional (Critério 8): Respeito estrito às Primary Keys (PK)
       e Foreign Keys (FK), garantindo que apenas registros válidos avancem.
    4. Seleção de Colunas (Seção 5.4): Exclusão de colunas extras existentes na
       Raw que não pertencem ao modelo analítico da Silver.
    5. Idempotência: Limpeza prévia das tabelas para evitar duplicação.
===============================================================================
"""

import banco

# ==============================================================================
# 1. GARANTIA DE IDEMPOTÊNCIA (LIMPEZA PRÉVIA DAS TABELAS SILVER)
# ==============================================================================
# Para que o pipeline possa ser executado múltiplas vezes sem duplicar dados,
# aplicamos o comando TRUNCATE. 
# O uso de 'RESTART IDENTITY' zera os contadores sequenciais (SERIAL/ID), e o 
# 'CASCADE' garante que as tabelas filhas sejam limpas respeitando as FKs.
LIMPAR_SILVER = [
    "TRUNCATE TABLE silver_trecho RESTART IDENTITY CASCADE;",
    "TRUNCATE TABLE silver_passagem RESTART IDENTITY CASCADE;",
    "TRUNCATE TABLE silver_pagamento RESTART IDENTITY CASCADE;",
    "TRUNCATE TABLE silver_viagem RESTART IDENTITY CASCADE;"
]

# ==============================================================================
# 2. TRANSFORMAÇÃO E CARGA: TABELA PRINCIPAL DE VIAGENS (silver_viagem)
# ==============================================================================
# Seção 5.4: As colunas extras 'cpf_viajante' e 'funcao', presentes na Raw, são 
# propositalmente ignoradas aqui, pois o modelo Silver não as utiliza.
# Seção 5.6: Realizamos o tratamento de datas (TO_DATE) e valores monetários,
# removendo pontos de milhar e substituindo a vírgula decimal por ponto.
SQL_VIAGEM = """
INSERT INTO silver_viagem (
    id_viagem, num_proposta, situacao, viagem_urgente,
    cod_orgao_superior, nome_orgao_superior, nome_viajante,
    cargo, data_inicio, data_fim, destinos, motivo,
    valor_diarias, valor_passagens, valor_devolucao, valor_outros_gastos,
    valor_total, duracao_dias
)
SELECT 
    id_viagem, 
    num_proposta, 
    situacao, 
    viagem_urgente,
    cod_orgao_superior, 
    nome_orgao_superior, 
    nome_viajante,
    cargo,
    
    -- [Critério 4] Conversão de texto (DD/MM/AAAA) para tipo nativo DATE[cite: 7]:
    TO_DATE(NULLIF(TRIM(data_inicio), ''), 'DD/MM/YYYY') AS data_inicio,
    TO_DATE(NULLIF(TRIM(data_fim), ''), 'DD/MM/YYYY') AS data_fim,
    
    destinos, 
    motivo,
    
    -- [Critério 4] Conversão de string monetária brasileira para DECIMAL(10,2)[cite: 7]:
    CAST(REPLACE(REPLACE(NULLIF(TRIM(valor_diarias), ''), '.', ''), ',', '.') AS NUMERIC(10,2)),
    CAST(REPLACE(REPLACE(NULLIF(TRIM(valor_passagens), ''), '.', ''), ',', '.') AS NUMERIC(10,2)),
    CAST(REPLACE(REPLACE(NULLIF(TRIM(valor_devolucao), ''), '.', ''), ',', '.') AS NUMERIC(10,2)),
    CAST(REPLACE(REPLACE(NULLIF(TRIM(valor_outros_gastos), ''), '.', ''), ',', '.') AS NUMERIC(10,2)),
    
    -- [Requisito - Seção 4] Cálculo da coluna derivada 'valor_total'[cite: 7]:
    -- Fórmula: Diárias + Passagens + Outros Gastos - Devolução.
    -- O COALESCE garante que valores NULL sejam tratados como 0 para não invalidar a conta.
    ( COALESCE(CAST(REPLACE(REPLACE(NULLIF(TRIM(valor_diarias), ''), '.', ''), ',', '.') AS NUMERIC(10,2)), 0) +
      COALESCE(CAST(REPLACE(REPLACE(NULLIF(TRIM(valor_passagens), ''), '.', ''), ',', '.') AS NUMERIC(10,2)), 0) +
      COALESCE(CAST(REPLACE(REPLACE(NULLIF(TRIM(valor_outros_gastos), ''), '.', ''), ',', '.') AS NUMERIC(10,2)), 0) -
      COALESCE(CAST(REPLACE(REPLACE(NULLIF(TRIM(valor_devolucao), ''), '.', ''), ',', '.') AS NUMERIC(10,2)), 0)
    ) AS valor_total,
    
    -- [Requisito - Seção 4] Cálculo da coluna derivada 'duracao_dias'[cite: 7]:
    -- Subtração entre datas + 1 para englobar corretamente o dia de partida e de retorno.
    (TO_DATE(NULLIF(TRIM(data_fim), ''), 'DD/MM/YYYY') - TO_DATE(NULLIF(TRIM(data_inicio), ''), 'DD/MM/YYYY')) + 1 AS duracao_dias
    
FROM raw_viagem
-- Garantia de unicidade da Primary Key (PK)[cite: 7]:
ON CONFLICT (id_viagem) DO NOTHING;
"""

# ==============================================================================
# 3. TRANSFORMAÇÃO E CARGA: TABELAS FILHAS (INTEGRIDADE REFERENCIAL)
# ==============================================================================
# Critério 8: Para garantir a modelagem relacional perfeita, todas as inserções
# nas tabelas filhas verificam a existência do 'id_viagem' na tabela principal
# através do operador otimizado 'WHERE EXISTS'. Isso impede erro de Foreign Key (FK).

SQL_PAGAMENTO = """
INSERT INTO silver_pagamento (
    id_viagem, num_proposta, nome_orgao_pagador, nome_ug_pagadora, tipo_pagamento, valor
)
SELECT 
    rp.id_viagem, 
    rp.num_proposta, 
    rp.nome_orgao_pagador, 
    rp.nome_ug_pagadora, 
    rp.tipo_pagamento,
    -- Tipagem monetária sem perda de precisão[cite: 7]:
    CAST(REPLACE(REPLACE(NULLIF(TRIM(rp.valor), ''), '.', ''), ',', '.') AS NUMERIC(10,2))
FROM raw_pagamento rp
-- [Critério 8] Validação de Integridade Referencial (FK -> silver_viagem)[cite: 7]:
WHERE EXISTS (
    SELECT 1 
    FROM silver_viagem sv 
    WHERE sv.id_viagem = rp.id_viagem
);
"""

SQL_PASSAGEM = """
INSERT INTO silver_passagem (
    id_viagem, meio_transporte,
    pais_origem_ida, uf_origem_ida, cidade_origem_ida,
    pais_destino_ida, uf_destino_ida, cidade_destino_ida,
    valor_passagem, taxa_servico, data_emissao
)
SELECT 
    rp.id_viagem, 
    rp.meio_transporte,
    rp.pais_origem_ida, 
    rp.uf_origem_ida, 
    rp.cidade_origem_ida,
    rp.pais_destino_ida, 
    rp.uf_destino_ida, 
    rp.cidade_destino_ida,
    
    -- Tipagem monetária[cite: 7]:
    CAST(REPLACE(REPLACE(NULLIF(TRIM(rp.valor_passagem), ''), '.', ''), ',', '.') AS NUMERIC(10,2)),
    CAST(REPLACE(REPLACE(NULLIF(TRIM(rp.taxa_servico), ''), '.', ''), ',', '.') AS NUMERIC(10,2)),
    
    -- Tipagem de data de emissão[cite: 7]:
    TO_DATE(NULLIF(TRIM(rp.data_emissao), ''), 'DD/MM/YYYY')
FROM raw_passagem rp
-- [Seção 5.4] A coluna 'dados de volta da passagem' da Raw foi omitida conforme modelo[cite: 7].
-- [Critério 8] Validação de Integridade Referencial (FK -> silver_viagem)[cite: 7]:
WHERE EXISTS (
    SELECT 1 
    FROM silver_viagem sv 
    WHERE sv.id_viagem = rp.id_viagem
);
"""

SQL_TRECHO = """
INSERT INTO silver_trecho (
    id_viagem, sequencia_trecho,
    origem_data, origem_uf, origem_cidade,
    destino_data, destino_uf, destino_cidade,
    meio_transporte, numero_diarias
)
SELECT 
    rt.id_viagem,
    -- Conversão para valor inteiro sequencial[cite: 7]:
    CAST(NULLIF(TRIM(rt.sequencia_trecho), '') AS INTEGER),
    
    -- Conversões de datas de partida e chegada do trecho[cite: 7]:
    TO_DATE(NULLIF(TRIM(rt.origem_data), ''), 'DD/MM/YYYY'), 
    rt.origem_uf, 
    rt.origem_cidade,
    TO_DATE(NULLIF(TRIM(rt.destino_data), ''), 'DD/MM/YYYY'), 
    rt.destino_uf, 
    rt.destino_cidade,
    
    rt.meio_transporte,
    
    -- Conversão do número de diárias para DECIMAL/NUMERIC[cite: 7]:
    CAST(REPLACE(REPLACE(NULLIF(TRIM(rt.numero_diarias), ''), '.', ''), ',', '.') AS NUMERIC(10,2))
FROM raw_trecho rt
-- [Critério 8] Validação de Integridade Referencial (FK -> silver_viagem)[cite: 7]:
WHERE EXISTS (
    SELECT 1 
    FROM silver_viagem sv 
    WHERE sv.id_viagem = rt.id_viagem
)
-- Seção 5.4 / 5.5: Prevenção de duplicidade na chave composta (id_viagem, sequencia_trecho)[cite: 7]:
ON CONFLICT (id_viagem, sequencia_trecho) DO NOTHING;
"""


def main():
    """
    Controlador do Pipeline da Fase 2 (Raw -> Silver).
    Executa as queries SQL nativas garantindo performance otimizada (Pushdown SQL).
    """
    print("===================================================================")
    print("      PIPELINE DE DADOS - FASE 2: TRANSFORMAÇÃO E CAMADA SILVER    ")
    print("===================================================================")
    try:
        conexao = banco.conectar()
        
        print("\n[Etapa 1/2] Limpando tabelas da Camada Silver (Idempotência)...")
        for comando in LIMPAR_SILVER:
            banco.executar(conexao, comando)
        print("            ✔ Tabelas esvaziadas com sucesso via TRUNCATE CASCADE.")
        
        print("\n[Etapa 2/2] Extraindo da Raw, convertendo tipos e carregando na Silver...")
        
        print("            ⌛ [1/4] Processando e calculando 'silver_viagem'...")
        banco.executar(conexao, SQL_VIAGEM)
        print("            ✔ Tabela 'silver_viagem' carregada e tipada com sucesso!")
        
        print("            ⌛ [2/4] Processando 'silver_pagamento' (com checagem de FK)...")
        banco.executar(conexao, SQL_PAGAMENTO)
        print("            ✔ Tabela 'silver_pagamento' carregada com sucesso!")
        
        print("            ⌛ [3/4] Processando 'silver_passagem' (com checagem de FK)...")
        banco.executar(conexao, SQL_PASSAGEM)
        print("            ✔ Tabela 'silver_passagem' carregada com sucesso!")
        
        print("            ⌛ [4/4] Processando 'silver_trecho' (com checagem de FK)...")
        banco.executar(conexao, SQL_TRECHO)
        print("            ✔ Tabela 'silver_trecho' carregada com sucesso!")
        
        conexao.close()
        print("\n===================================================================")
        print(" 🏆 FASE 2 CONCLUÍDA! Dados limpos, tipados e modelados na Silver. ")
        print("===================================================================\n")
        
    except Exception as erro:
        print("\n[ERRO CRÍTICO] Falha durante a execução da transformação na Camada Silver:", erro)
        raise

if __name__ == "__main__":
    main()