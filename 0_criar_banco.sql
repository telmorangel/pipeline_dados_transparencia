-- =============================================================================
-- FASE 0: BANCO E TABELAS (0_criar_banco.sql)
-- Projeto Avaliativo - Análise de Dados com Python
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. CRIAÇÃO DO BANCO DE DADOS
-- -----------------------------------------------------------------------------
CREATE DATABASE db_viagens_2025;

-- ATENÇÃO: Se você estiver executando este script via terminal do PostgreSQL (psql), 
-- descomente a linha abaixo para alternar para o banco recém-criado:
-- \c db_viagens_2025;

-- -----------------------------------------------------------------------------
-- LIMPEZA DE TABELAS ANTERIORES (Garante a Idempotência do Script de Estrutura)
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS silver_trecho CASCADE;
DROP TABLE IF EXISTS silver_pagamento CASCADE;
DROP TABLE IF EXISTS silver_passagem CASCADE;
DROP TABLE IF EXISTS silver_viagem CASCADE;

DROP TABLE IF EXISTS raw_trecho CASCADE;
DROP TABLE IF EXISTS raw_pagamento CASCADE;
DROP TABLE IF EXISTS raw_passagem CASCADE;
DROP TABLE IF EXISTS raw_viagem CASCADE;

-- =============================================================================
-- 2. CAMADA RAW (BRONZE)
-- Descrição: Todas as colunas VARCHAR e sem constraints.
-- Observação: Replica o CSV inteiro, incluindo colunas que a camada Silver não usa.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABELA: raw_viagem
-- -----------------------------------------------------------------------------
CREATE TABLE raw_viagem (
    id_viagem           VARCHAR(255),
    num_proposta        VARCHAR(255),
    situacao            VARCHAR(255),
    viagem_urgente      VARCHAR(255),
    cod_orgao_superior  VARCHAR(255),
    nome_orgao_superior VARCHAR(255),
    cpf_viajante        VARCHAR(255), -- Coluna extra contida no CSV bruto
    nome_viajante       VARCHAR(255),
    funcao              VARCHAR(255), -- Coluna extra contida no CSV bruto
    cargo               VARCHAR(255),
    data_inicio         VARCHAR(255),
    data_fim            VARCHAR(255),
    destinos            VARCHAR(4000),
    motivo              VARCHAR(4000),
    valor_diarias       VARCHAR(255),
    valor_passagens     VARCHAR(255),
    valor_devolucao     VARCHAR(255),
    valor_outros_gastos VARCHAR(255)
);

-- -----------------------------------------------------------------------------
-- TABELA: raw_passagem
-- -----------------------------------------------------------------------------
CREATE TABLE raw_passagem (
    id_passagem          VARCHAR(255),
    id_viagem            VARCHAR(255),
    meio_transporte      VARCHAR(255),
    pais_origem_ida      VARCHAR(255),
    uf_origem_ida        VARCHAR(255),
    cidade_origem_ida    VARCHAR(255),
    pais_destino_ida     VARCHAR(255),
    uf_destino_ida       VARCHAR(255),
    cidade_destino_ida   VARCHAR(255),
    valor_passagem       VARCHAR(255),
    taxa_servico         VARCHAR(255),
    data_emissao         VARCHAR(255),
    dados_volta_passagem VARCHAR(255)  -- Coluna extra contida no CSV bruto
);

-- -----------------------------------------------------------------------------
-- TABELA: raw_pagamento
-- -----------------------------------------------------------------------------
CREATE TABLE raw_pagamento (
    id_pagamento       VARCHAR(255),
    id_viagem          VARCHAR(255),
    num_proposta       VARCHAR(255),
    nome_orgao_pagador VARCHAR(255),
    nome_ug_pagadora   VARCHAR(255),
    tipo_pagamento     VARCHAR(255),
    valor              VARCHAR(255)
);

-- -----------------------------------------------------------------------------
-- TABELA: raw_trecho
-- -----------------------------------------------------------------------------
CREATE TABLE raw_trecho (
    id_trecho        VARCHAR(255),
    id_viagem        VARCHAR(255),
    sequencia_trecho VARCHAR(255),
    origem_data      VARCHAR(255),
    origem_uf        VARCHAR(255),
    origem_cidade    VARCHAR(255),
    destino_data     VARCHAR(255),
    destino_uf       VARCHAR(255),
    destino_cidade   VARCHAR(255),
    meio_transporte  VARCHAR(255),
    numero_diarias   VARCHAR(255)
);

-- =============================================================================
-- 3. CAMADA SILVER (PRATA)
-- Descrição: Dados limpos, tipados, com PK, FK e restrições explícitas.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABELA: silver_viagem
-- -----------------------------------------------------------------------------
CREATE TABLE silver_viagem (
    id_viagem           VARCHAR(20) PRIMARY KEY NOT NULL,
    num_proposta        VARCHAR(20),
    situacao            VARCHAR(50),
    viagem_urgente      VARCHAR(5),
    cod_orgao_superior  VARCHAR(20),
    nome_orgao_superior VARCHAR(255) NOT NULL,              -- Constraint 1: NOT NULL
    nome_viajante       VARCHAR(255),
    cargo               VARCHAR(255),
    data_inicio         DATE,
    data_fim            DATE,
    destinos            VARCHAR(4000),
    motivo              VARCHAR(4000),
    valor_diarias       DECIMAL(10,2) CHECK (valor_diarias >= 0), -- Constraint 2: CHECK
    valor_passagens     DECIMAL(10,2),
    valor_devolucao     DECIMAL(10,2),
    valor_outros_gastos DECIMAL(10,2),
    valor_total         DECIMAL(12,2),                      -- Campo calculado no script de transformação
    duracao_dias        INT                                 -- Campo calculado no script de transformação
);

-- -----------------------------------------------------------------------------
-- TABELA: silver_passagem
-- -----------------------------------------------------------------------------
CREATE TABLE silver_passagem (
    id_passagem        SERIAL PRIMARY KEY,                  -- AUTO_INCREMENT via SERIAL no PostgreSQL
    id_viagem          VARCHAR(20) NOT NULL,
    meio_transporte    VARCHAR(50),
    pais_origem_ida    VARCHAR(60),
    uf_origem_ida      VARCHAR(40),
    cidade_origem_ida  VARCHAR(80),
    pais_destino_ida   VARCHAR(60),
    uf_destino_ida     VARCHAR(40),
    cidade_destino_ida VARCHAR(80),
    valor_passagem     DECIMAL(10,2) CHECK (valor_passagem >= 0), -- Constraint 1: CHECK
    taxa_servico       DECIMAL(10,2) CHECK (taxa_servico >= 0),   -- Constraint 2: CHECK
    data_emissao       DATE,
    FOREIGN KEY (id_viagem) REFERENCES silver_viagem(id_viagem)
);

-- -----------------------------------------------------------------------------
-- TABELA: silver_pagamento
-- -----------------------------------------------------------------------------
CREATE TABLE silver_pagamento (
    id_pagamento       SERIAL PRIMARY KEY,
    id_viagem          VARCHAR(20) NOT NULL,
    num_proposta       VARCHAR(20),
    nome_orgao_pagador VARCHAR(255),
    nome_ug_pagadora   VARCHAR(255),
    tipo_pagamento     VARCHAR(50) NOT NULL,                -- Constraint 2: NOT NULL
    valor              DECIMAL(10,2) CHECK (valor >= 0),    -- Constraint 1: CHECK
    FOREIGN KEY (id_viagem) REFERENCES silver_viagem(id_viagem)
);

-- -----------------------------------------------------------------------------
-- TABELA: silver_trecho
-- -----------------------------------------------------------------------------
CREATE TABLE silver_trecho (
    id_trecho        SERIAL PRIMARY KEY,
    id_viagem        VARCHAR(20) NOT NULL,
    sequencia_trecho INT,
    origem_data      DATE,
    origem_uf        VARCHAR(40),
    origem_cidade    VARCHAR(80),
    destino_data     DATE,
    destino_uf       VARCHAR(40),
    destino_cidade   VARCHAR(80),
    meio_transporte  VARCHAR(50),
    numero_diarias   DECIMAL(10,2) CHECK (numero_diarias >= 0), -- Constraint 1: CHECK
    FOREIGN KEY (id_viagem) REFERENCES silver_viagem(id_viagem),
    CONSTRAINT uniq_viagem_sequencia UNIQUE (id_viagem, sequencia_trecho) -- Constraint 2: UNIQUE
);
);