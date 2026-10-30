
CREATE TABLE cliente (
    id_cliente SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    telefone VARCHAR(20)
);


CREATE TABLE funcionario (
    id_funcionario SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    telefone VARCHAR(20),
    cargo VARCHAR(50),
    senha VARCHAR(255)
);


CREATE TABLE disponibilidade (
    id_disponibilidade SERIAL PRIMARY KEY,
    id_funcionario INTEGER NOT NULL,
    data DATE NOT NULL,
    horario_inicio TIME NOT NULL,
    horario_fim TIME NOT NULL,

    CONSTRAINT fk_disponibilidade_funcionario
        FOREIGN KEY (id_funcionario)
        REFERENCES funcionario(id_funcionario)
        ON DELETE CASCADE,

    CONSTRAINT horario_valido
        CHECK (horario_inicio < horario_fim)
);


CREATE TABLE servico (
    id_servico SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    preco DECIMAL(10,2) NOT NULL
);


CREATE TABLE agendamento (
    id_agendamento SERIAL PRIMARY KEY,
    data DATE NOT NULL,
    horario TIME NOT NULL,
    id_cliente INTEGER NOT NULL,
    id_funcionario INTEGER NOT NULL,
    status VARCHAR(30) NOT NULL,
    valor_total DECIMAL(10,2) DEFAULT 0,
    pagamento_status VARCHAR(20) DEFAULT 'PENDENTE',
    data_pagamento TIMESTAMP,

    CONSTRAINT fk_agendamento_cliente
        FOREIGN KEY (id_cliente)
        REFERENCES cliente(id_cliente),

    CONSTRAINT fk_agendamento_funcionario
        FOREIGN KEY (id_funcionario)
        REFERENCES funcionario(id_funcionario)
);


CREATE TABLE agendamento_servico (
    id_agendamento INTEGER NOT NULL,
    id_servico INTEGER NOT NULL,

    PRIMARY KEY (id_agendamento, id_servico),

    CONSTRAINT fk_agendamento_servico_agendamento
        FOREIGN KEY (id_agendamento)
        REFERENCES agendamento(id_agendamento)
        ON DELETE CASCADE,

    CONSTRAINT fk_agendamento_servico_servico
        FOREIGN KEY (id_servico)
        REFERENCES servico(id_servico)
        ON DELETE CASCADE
);


CREATE TABLE regra_comissao (
    id_regra SERIAL PRIMARY KEY,
    descricao VARCHAR(100) NOT NULL,
    percentual_material_profissional DECIMAL(5,2) NOT NULL,
    percentual_comissao DECIMAL(5,2) NOT NULL
);


INSERT INTO regra_comissao (
    descricao,
    percentual_material_profissional,
    percentual_comissao
)
VALUES
    ('Produtos do Studio', 0.00, 30.00),
    ('Metade Studio e metade profissional', 50.00, 50.00),
    ('80% do material do profissional', 80.00, 60.00);


CREATE TABLE fechamento_comissao (
    id_fechamento SERIAL PRIMARY KEY,
    id_funcionario INTEGER NOT NULL
        REFERENCES funcionario(id_funcionario),
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    valor_total NUMERIC(10,2) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    data_pagamento TIMESTAMP,

    CONSTRAINT periodo_valido
        CHECK (data_fim >= data_inicio),

    CONSTRAINT status_fechamento_valido
        CHECK (status IN ('PENDENTE', 'PAGO')),

    CONSTRAINT fechamento_unico
        UNIQUE (id_funcionario, data_inicio, data_fim)
);


CREATE TABLE comissao (
    id_comissao SERIAL PRIMARY KEY,
    id_agendamento INTEGER NOT NULL,
    id_servico INTEGER NOT NULL,
    id_regra INTEGER NOT NULL,
    id_fechamento INTEGER,
    valor DECIMAL(10,2) NOT NULL,
    data_calculo DATE NOT NULL,

    CONSTRAINT fk_comissao_agendamento_servico
        FOREIGN KEY (id_agendamento, id_servico)
        REFERENCES agendamento_servico(id_agendamento, id_servico),

    CONSTRAINT fk_comissao_regra
        FOREIGN KEY (id_regra)
        REFERENCES regra_comissao(id_regra),

    CONSTRAINT fk_comissao_fechamento
        FOREIGN KEY (id_fechamento)
        REFERENCES fechamento_comissao(id_fechamento),

    CONSTRAINT uq_comissao_procedimento
        UNIQUE (id_agendamento, id_servico)
);


CREATE TABLE notificacao (
    id_notificacao SERIAL PRIMARY KEY,
    id_cliente INTEGER,
    id_funcionario INTEGER,
    id_agendamento INTEGER,
    mensagem TEXT NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    lida BOOLEAN NOT NULL DEFAULT FALSE,
    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_notificacao_cliente
        FOREIGN KEY (id_cliente)
        REFERENCES cliente(id_cliente),

    CONSTRAINT fk_notificacao_funcionario
        FOREIGN KEY (id_funcionario)
        REFERENCES funcionario(id_funcionario),

    CONSTRAINT fk_notificacao_agendamento
        FOREIGN KEY (id_agendamento)
        REFERENCES agendamento(id_agendamento),

    CONSTRAINT notificacao_destinatario
        CHECK (
            (id_cliente IS NOT NULL AND id_funcionario IS NULL)
            OR
            (id_cliente IS NULL AND id_funcionario IS NOT NULL)
        )
);
