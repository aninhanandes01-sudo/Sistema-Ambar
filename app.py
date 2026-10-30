
from flask import Flask, render_template, request, redirect, session, flash
import psycopg
import re
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import calendar

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


def conectar_banco():
    return psycopg.connect(
        os.getenv("DATABASE_URL")
    )





@app.route("/painel")
def painel():

    if "usuario_id" not in session:
        return redirect("/login")

    if session["tipo_usuario"] == "funcionario":

        if session.get("cargo", "").upper() == "ADMINISTRADOR":
            return render_template("painel_admin.html")

        return render_template("painel_funcionario.html")

    return render_template("painel.html")


@app.route("/clientes")
def clientes():
    conn = conectar_banco()

    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM cliente ORDER BY id_cliente"
        )
        clientes = cursor.fetchall()

    conn.close()

    return render_template(
        "clientes.html",
        clientes=clientes
    )


@app.route("/novo-cliente", methods=["GET", "POST"])
def novo_cliente():

    if request.method == "POST":

        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]
        telefone = re.sub(
            r"\D", "", request.form["telefone"]
        )

        if len(telefone) not in (10, 11):
            return render_template(
                "novo_cliente.html",
                erro="Digite um telefone válido com DDD."
            )

        if len(set(telefone)) == 1:
            return render_template(
                "novo_cliente.html",
                erro="Digite um telefone válido."
            )

        senha = generate_password_hash(senha)

        conn = conectar_banco()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO cliente
                (nome, email, senha, telefone)
                VALUES (%s, %s, %s, %s)
                """,
                (nome, email, senha, telefone)
            )

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("novo_cliente.html")


@app.route("/funcionarios")
def funcionarios():

    conn = conectar_banco()

    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM funcionario ORDER BY id_funcionario"
        )
        funcionarios = cursor.fetchall()

    conn.close()

    return render_template(
        "funcionarios.html",
        funcionarios=funcionarios
    )

@app.route("/minha-agenda", methods=["GET", "POST"])
def minha_agenda():

    id_funcionario = session["usuario_id"]

    conn = conectar_banco()
    cursor = conn.cursor()

    if request.method == "POST":

        cursor.execute("""
            INSERT INTO disponibilidade
            (id_funcionario, data, horario_inicio, horario_fim)
            VALUES (%s, %s, %s, %s)
        """, (
            id_funcionario,
            request.form["data"],
            request.form["horario_inicio"],
            request.form["horario_fim"]
        ))

        conn.commit()

    cursor.execute("""
        SELECT id_disponibilidade, data, horario_inicio, horario_fim
        FROM disponibilidade
        WHERE id_funcionario = %s
        ORDER BY data, horario_inicio
    """, (id_funcionario,))

    horarios = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("minha_agenda.html", horarios=horarios)


@app.route("/novo-funcionario", methods=["GET", "POST"])
def novo_funcionario():

    if request.method == "POST":

        nome = request.form["nome"]
        email = request.form["email"]
        senha = generate_password_hash(request.form["senha"])
        telefone = request.form["telefone"]
        cargo = request.form["cargo"]

        print("CADASTRANDO:", nome, email, telefone, cargo)

        conn = conectar_banco()

        try:

            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO funcionario
                    (nome, email, senha, telefone, cargo)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (nome, email, senha, telefone, cargo)
                )

            conn.commit()

            print("FUNCIONÁRIO CADASTRADO!")

        except Exception as erro:

            conn.rollback()
            print("ERRO AO CADASTRAR:", erro)

        finally:

            conn.close()

        return redirect("/login")

    return render_template("novo_funcionario.html")


@app.route("/")
def index():

    

    conn = conectar_banco()

    with conn.cursor() as cursor:

        cursor.execute("""
            SELECT id_servico, nome, descricao, preco
            FROM servico
            ORDER BY nome
        """)

        servicos = cursor.fetchall()

        print("SERVIÇOS ENCONTRADOS:", servicos)

    conn.close()

    return render_template(
        "index.html",
        servicos=servicos
    )


@app.route("/perfil", methods=["GET", "POST"])
def perfil():

    if "usuario_id" not in session:
        return redirect("/login")

    tipo_usuario = session["tipo_usuario"]
    usuario_id = session["usuario_id"]

    conn = conectar_banco()

    if request.method == "POST":

        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        telefone = request.form.get("telefone", "").strip()

        senha_atual = request.form.get("senha_atual", "")
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if not nome or not email:
            flash("Nome e e-mail são obrigatórios.", "erro")

        else:

            with conn.cursor() as cursor:

                if tipo_usuario == "cliente":

                    tabela = "cliente"
                    id_coluna = "id_cliente"

                    cursor.execute("""
                        SELECT id_cliente
                        FROM cliente
                        WHERE email = %s AND id_cliente != %s
                    """, (email, usuario_id))

                    email_cliente = cursor.fetchone()

                    cursor.execute("""
                        SELECT id_funcionario
                        FROM funcionario
                        WHERE email = %s
                    """, (email,))

                    email_funcionario = cursor.fetchone()

                else:

                    tabela = "funcionario"
                    id_coluna = "id_funcionario"

                    cursor.execute("""
                        SELECT id_funcionario
                        FROM funcionario
                        WHERE email = %s AND id_funcionario != %s
                    """, (email, usuario_id))

                    email_funcionario = cursor.fetchone()

                    cursor.execute("""
                        SELECT id_cliente
                        FROM cliente
                        WHERE email = %s
                    """, (email,))

                    email_cliente = cursor.fetchone()

                email_existente = email_cliente or email_funcionario

                if email_existente:

                    flash("Este e-mail já está cadastrado em outra conta.", "erro")

                else:

                    cursor.execute(
                        f"""
                        SELECT senha
                        FROM {tabela}
                        WHERE {id_coluna} = %s
                        """,
                        (usuario_id,)
                    )

                    resultado = cursor.fetchone()

                    if not resultado:
                        flash("Não foi possível localizar sua conta.", "erro")

                    elif senha_atual or nova_senha or confirmar_senha:

                        if not senha_atual or not nova_senha or not confirmar_senha:

                            flash("Preencha os três campos de senha para alterá-la.", "erro")

                        elif not resultado[0] or not check_password_hash(resultado[0], senha_atual):

                            flash("A senha atual está incorreta.", "erro")

                        elif nova_senha != confirmar_senha:

                            flash("A confirmação da nova senha não corresponde.", "erro")

                        elif len(nova_senha) < 8:

                            flash("A nova senha deve ter pelo menos 8 caracteres.", "erro")

                        else:

                            senha_hash = generate_password_hash(nova_senha)

                            cursor.execute(
                                f"""
                                UPDATE {tabela}
                                SET nome = %s,
                                    email = %s,
                                    telefone = %s,
                                    senha = %s
                                WHERE {id_coluna} = %s
                                """,
                                (nome, email, telefone, senha_hash, usuario_id)
                            )

                            conn.commit()

                            session["usuario_nome"] = nome

                            flash("Seus dados e sua senha foram atualizados!", "sucesso")

                    else:

                        cursor.execute(
                            f"""
                            UPDATE {tabela}
                            SET nome = %s,
                                email = %s,
                                telefone = %s
                            WHERE {id_coluna} = %s
                            """,
                            (nome, email, telefone, usuario_id)
                        )

                        conn.commit()

                        session["usuario_nome"] = nome

                        flash("Seus dados foram atualizados com sucesso!", "sucesso")

            conn.close()
            return redirect("/perfil")

    with conn.cursor() as cursor:

        if tipo_usuario == "cliente":

            cursor.execute("""
                SELECT nome, email, telefone
                FROM cliente
                WHERE id_cliente = %s
            """, (usuario_id,))

        else:

            cursor.execute("""
                SELECT nome, email, telefone, cargo
                FROM funcionario
                WHERE id_funcionario = %s
            """, (usuario_id,))

        usuario = cursor.fetchone()

    conn.close()

    return render_template(
        "perfil.html",
        usuario=usuario
    )

@app.route("/servicos")
def servicos():

    conn = conectar_banco()

    with conn.cursor() as cursor:

        cursor.execute("""
            SELECT id_servico, nome, descricao, preco
            FROM servico
            ORDER BY nome
        """)

        servicos = cursor.fetchall()

    conn.close()

    return render_template(
        "servicos.html",
        servicos=servicos
    )





@app.route("/agendamentos", methods=["GET", "POST"])
def agendamentos():

    if "usuario_nome" not in session:
        return redirect("/login")

    conn = conectar_banco()

    if request.method == "POST":

        data = request.form.get("data")
        horario = request.form.get("horario")
        id_cliente = session["usuario_id"]
        id_funcionario = request.form.get("id_funcionario")
        id_servicos = request.form.getlist("id_servicos")

        if not id_funcionario:
            conn.close()
            return "Erro: selecione um profissional."

        if not data or not horario:
            conn.close()
            return "Erro: selecione uma data e um horário."

        if not id_servicos:
            conn.close()
            return "Erro: selecione pelo menos um serviço."

        id_servicos = [int(id) for id in id_servicos]

        with conn.cursor() as cursor:

            cursor.execute(
                """
                SELECT SUM(preco)
                FROM servico
                WHERE id_servico = ANY(%s)
                """,
                (id_servicos,)
            )

            valor_total = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO agendamento
                (data, horario, id_cliente, id_funcionario, status, valor_total)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id_agendamento
                """,
                (
                    data,
                    horario,
                    id_cliente,
                    id_funcionario,
                    "PENDENTE",
                    valor_total
                )
            )

            id_agendamento = cursor.fetchone()[0]

            for id_servico in id_servicos:
                cursor.execute(
                    """
                    INSERT INTO agendamento_servico
                    (id_agendamento, id_servico)
                    VALUES (%s, %s)
                    """,
                    (id_agendamento, id_servico)
                )

            cursor.execute(
                """
                INSERT INTO notificacao
                (id_cliente, id_agendamento, mensagem, tipo)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    id_cliente,
                    id_agendamento,
                    f"Seu agendamento para o dia {data}, às {horario}, foi solicitado e está aguardando confirmação.",
                    "AGENDAMENTO"
                )
            )

        conn.commit()

        conn.close()

        return redirect("/meus-agendamentos-cliente")

    with conn.cursor() as cursor:

        cursor.execute(
            "SELECT id_cliente, nome FROM cliente ORDER BY nome"
        )
        clientes = cursor.fetchall()

        cursor.execute(
            "SELECT id_funcionario, nome FROM funcionario ORDER BY nome"
        )
        funcionarios = cursor.fetchall()

        cursor.execute(
            "SELECT * FROM servico ORDER BY nome"
        )
        servicos = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                a.id_agendamento,
                c.nome,
                f.nome,
                s.nome,
                a.data,
                a.horario,
                a.status,
                a.valor_total
            FROM agendamento a
            JOIN cliente c
                ON a.id_cliente = c.id_cliente
            JOIN funcionario f
                ON a.id_funcionario = f.id_funcionario
            JOIN agendamento_servico ags
                ON a.id_agendamento = ags.id_agendamento
            JOIN servico s
                ON ags.id_servico = s.id_servico
            ORDER BY a.data, a.horario
            """
        )

        agendamentos = cursor.fetchall()

    conn.close()

    return render_template(
        "agendamentos.html",
        clientes=clientes,
        funcionarios=funcionarios,
        servicos=servicos,
        agendamentos=agendamentos
    )


@app.route("/disponibilidade/<int:id_funcionario>")

def buscar_disponibilidade(id_funcionario):

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT data
        FROM disponibilidade
        WHERE id_funcionario = %s
          AND data >= CURRENT_DATE
        ORDER BY data
    """, (id_funcionario,))

    disponibilidades = cursor.fetchall()

    cursor.close()
    conn.close()

    resultado = []

    for disponibilidade in disponibilidades:
        resultado.append({
            "data": disponibilidade[0].strftime("%Y-%m-%d")
        })

    return resultado

@app.route("/horarios-disponiveis/<int:id_funcionario>/<data>")
def horarios_disponiveis(id_funcionario, data):

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT horario_inicio, horario_fim
        FROM disponibilidade
        WHERE id_funcionario = %s
          AND data = %s
        ORDER BY horario_inicio
    """, (id_funcionario, data))

    disponibilidades = cursor.fetchall()

    cursor.execute("""
        SELECT horario
        FROM agendamento
        WHERE id_funcionario = %s
          AND data = %s
          AND status != 'CANCELADO'
    """, (id_funcionario, data))

    agendados = cursor.fetchall()

    cursor.close()
    conn.close()

    horarios_agendados = {
        horario[0].strftime("%H:%M")
        for horario in agendados
    }

    horarios = []

    for inicio, fim in disponibilidades:

        hora_atual = inicio.hour
        minuto_atual = inicio.minute

        while True:

            horario = f"{hora_atual:02d}:{minuto_atual:02d}"

            if horario not in horarios_agendados:
                horarios.append(horario)

            minuto_atual += 60

            if minuto_atual >= 60:
                hora_atual += 1
                minuto_atual = 0

            if hora_atual > fim.hour or (
                hora_atual == fim.hour and minuto_atual >= fim.minute
            ):
                break

    return horarios

@app.route("/meus-agendamentos-cliente")
def meus_agendamentos_cliente():

    if "usuario_id" not in session:
        return redirect("/login")

    id_cliente = session["usuario_id"]

    conn = conectar_banco()

    with conn.cursor() as cursor:

        cursor.execute("""
            SELECT
                a.id_agendamento,
                a.data,
                a.horario,
                f.nome,
                s.nome,
                a.valor_total,
                a.status,
                a.pagamento_status
            FROM agendamento a

            JOIN funcionario f
                ON a.id_funcionario = f.id_funcionario

            JOIN agendamento_servico ags
                ON a.id_agendamento = ags.id_agendamento

            JOIN servico s
                ON ags.id_servico = s.id_servico

            WHERE a.id_cliente = %s

            ORDER BY a.data, a.horario
        """, (id_cliente,))

        resultados = cursor.fetchall()

    conn.close()

    agendamentos = []

    for resultado in resultados:

        id_agendamento = resultado[0]

        existente = None

        for agendamento in agendamentos:

            if agendamento[0] == id_agendamento:
                existente = agendamento
                break

        if existente:

            existente[4].append(resultado[4])

        else:

            agendamentos.append([
                resultado[0],       # id_agendamento
                resultado[1],       # data
                resultado[2],       # horario
                resultado[3],       # funcionario
                [resultado[4]],     # serviços
                resultado[5],       # valor total
                resultado[6],       # status
                resultado[7]        # pagamento
            ])

    return render_template(
        "meus_agendamentos_cliente.html",
        agendamentos=agendamentos
    )

@app.route("/cancelar-agendamento/<int:id_agendamento>")
def cancelar_agendamento(id_agendamento):

    if "usuario_id" not in session:
        return redirect("/login")

    conn = conectar_banco()

    with conn.cursor() as cursor:

        cursor.execute("""
            UPDATE agendamento
            SET status = 'CANCELADO'
            WHERE id_agendamento = %s
              AND id_cliente = %s
        """, (
            id_agendamento,
            session["usuario_id"]
        ))

    conn.commit()
    conn.close()

    return redirect("/meus-agendamentos-cliente")

@app.route("/meus-agendamentos")
def meus_agendamentos():

    if "usuario_id" not in session:
        return redirect("/login")

    id_funcionario = session["usuario_id"]

    conn = conectar_banco()

    with conn.cursor() as cursor:

        cursor.execute("""
            SELECT
                a.id_agendamento,
                a.data,
                a.horario,
                c.nome,
                s.nome,
                a.valor_total,
                a.status,
                a.pagamento_status,
                a.data_pagamento
            FROM agendamento a

            JOIN cliente c
                ON a.id_cliente = c.id_cliente

            JOIN agendamento_servico ags
                ON a.id_agendamento = ags.id_agendamento

            JOIN servico s
                ON ags.id_servico = s.id_servico

            WHERE a.id_funcionario = %s

            ORDER BY a.data, a.horario
        """, (id_funcionario,))

        resultados = cursor.fetchall()

    conn.close()

    agendamentos = []

    for resultado in resultados:

        id_agendamento = resultado[0]

        existente = None

        for agendamento in agendamentos:
            if agendamento[0] == id_agendamento:
                existente = agendamento
                break

        if existente:
            existente[4].append(resultado[4])

        else:
            agendamentos.append([
                resultado[0],  
                resultado[1],  
                resultado[2],  
                resultado[3],  
                [resultado[4]],  
                resultado[5],  
                resultado[6],  
                resultado[7],  
                resultado[8]   
            ])

    return render_template(
        "meus_agendamentos.html",
        agendamentos=agendamentos
    )

@app.route("/marcar-pago/<int:id_agendamento>", methods=["GET", "POST"])
def marcar_pago(id_agendamento):

    if "usuario_id" not in session:
        return redirect("/login")

    conn = conectar_banco()

    with conn.cursor() as cursor:

        
        cursor.execute("""
            SELECT
                s.id_servico,
                s.nome,
                s.preco
            FROM agendamento_servico ags
            JOIN servico s
                ON ags.id_servico = s.id_servico
            JOIN agendamento a
                ON a.id_agendamento = ags.id_agendamento
            WHERE ags.id_agendamento = %s
              AND a.id_funcionario = %s
        """, (
            id_agendamento,
            session["usuario_id"]
        ))

        servicos = cursor.fetchall()

       
        cursor.execute("""
            SELECT
                id_regra,
                descricao,
                percentual_comissao
            FROM regra_comissao
            ORDER BY id_regra
        """)

        regras = cursor.fetchall()

       
        cursor.execute("""
            SELECT pagamento_status
            FROM agendamento
            WHERE id_agendamento = %s
              AND id_funcionario = %s
        """, (
            id_agendamento,
            session["usuario_id"]
        ))

        agendamento = cursor.fetchone()

    conn.close()

    if not servicos:
        return "Agendamento não encontrado."

    if not agendamento:
        return "Você não tem permissão para esse agendamento."

    if agendamento[0] == "PAGO":
        return "Esse agendamento já foi pago."

    if request.method == "POST":

        conn = conectar_banco()

        try:

            with conn.cursor() as cursor:

                
                cursor.execute("""
                    SELECT pagamento_status
                    FROM agendamento
                    WHERE id_agendamento = %s
                      AND id_funcionario = %s
                """, (
                    id_agendamento,
                    session["usuario_id"]
                ))

                pagamento = cursor.fetchone()

                if not pagamento:
                    return "Agendamento não encontrado."

                if pagamento[0] == "PAGO":
                    return "Esse agendamento já foi pago."

               
                for servico in servicos:

                    id_servico = servico[0]
                    preco = servico[2]

                   
                    id_regra = request.form.get(f"regra_{id_servico}")

                    if not id_regra:
                        conn.rollback()
                        return "Escolha uma regra para todos os serviços."

                    cursor.execute("""
                        SELECT percentual_comissao
                        FROM regra_comissao
                        WHERE id_regra = %s
                    """, (id_regra,))

                    regra = cursor.fetchone()

                    if not regra:
                        conn.rollback()
                        return "Regra de comissão inválida."

                    percentual = regra[0]

                   
                    valor_comissao = preco * percentual / 100

                   
                    cursor.execute("""
                        INSERT INTO comissao
                        (
                            id_agendamento,
                            id_servico,
                            id_regra,
                            valor,
                            data_calculo
                        )
                        VALUES (%s, %s, %s, %s, CURRENT_DATE)
                    """, (
                        id_agendamento,
                        id_servico,
                        id_regra,
                        valor_comissao
                    ))

                
                cursor.execute("""
                    UPDATE agendamento
                    SET pagamento_status = 'PAGO',
                        data_pagamento = CURRENT_TIMESTAMP
                    WHERE id_agendamento = %s
                      AND id_funcionario = %s
                """, (
                    id_agendamento,
                    session["usuario_id"]
                ))

            conn.commit()

        except Exception as erro:

            conn.rollback()
            print("ERRO AO REGISTRAR PAGAMENTO:", erro)
            return "Erro ao registrar pagamento."

        finally:
            conn.close()

        return redirect("/meus-agendamentos")

    return render_template(
        "marcar_pago.html",
        id_agendamento=id_agendamento,
        servicos=servicos,
        regras=regras
    )

@app.route("/relatorio-faturamento")
def relatorio_faturamento():

    if "usuario_id" not in session:
        return redirect("/login")

    if session.get("tipo_usuario") != "funcionario" or session.get("cargo", "").upper() != "ADMINISTRADOR":
        return redirect("/painel")

    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")

    conn = conectar_banco()

    with conn.cursor() as cursor:

        consulta = """
            SELECT
                COUNT(*) AS quantidade_pagamentos,
                COALESCE(SUM(valor_total), 0) AS faturamento
            FROM agendamento
            WHERE pagamento_status = 'PAGO'
        """

        parametros = []

        if data_inicio:
            consulta += " AND data_pagamento::date >= %s"
            parametros.append(data_inicio)

        if data_fim:
            consulta += " AND data_pagamento::date <= %s"
            parametros.append(data_fim)

        cursor.execute(consulta, parametros)
        resumo = cursor.fetchone()

        consulta_detalhes = """
            SELECT
                a.id_agendamento,
                a.data_pagamento,
                c.nome,
                f.nome,
                a.valor_total
            FROM agendamento a
            JOIN cliente c
                ON a.id_cliente = c.id_cliente
            JOIN funcionario f
                ON a.id_funcionario = f.id_funcionario
            WHERE a.pagamento_status = 'PAGO'
        """

        parametros_detalhes = []

        if data_inicio:
            consulta_detalhes += " AND a.data_pagamento::date >= %s"
            parametros_detalhes.append(data_inicio)

        if data_fim:
            consulta_detalhes += " AND a.data_pagamento::date <= %s"
            parametros_detalhes.append(data_fim)

        consulta_detalhes += " ORDER BY a.data_pagamento DESC"

        cursor.execute(consulta_detalhes, parametros_detalhes)
        pagamentos = cursor.fetchall()

    conn.close()

    return render_template(
        "relatorio_faturamento.html",
        faturamento=resumo[1],
        quantidade_pagamentos=resumo[0],
        pagamentos=pagamentos,
        data_inicio=data_inicio,
        data_fim=data_fim
    )



@app.route("/relatorio-comissoes", methods=["GET", "POST"])
def relatorio_comissoes():

    if "usuario_id" not in session:
        return redirect("/login")

    if (
        session.get("tipo_usuario") != "funcionario"
        or session.get("cargo", "").upper() != "ADMINISTRADOR"
    ):
        return redirect("/painel")

    hoje = date.today()
    mes_atual = hoje.strftime("%Y-%m")

    if request.method == "POST":

        quinzena = request.form.get("quinzena", "")
        mes_selecionado = request.form.get("mes", mes_atual)

        try:
            ano, mes = map(int, mes_selecionado.split("-"))

            # Valida o mês escolhido.
            primeiro_dia = date(ano, mes, 1)
            ultimo_dia_mes = calendar.monthrange(ano, mes)[1]

            if quinzena == "1":
                data_inicio = primeiro_dia
                data_fim = date(ano, mes, 15)

            elif quinzena == "2":
                data_inicio = date(ano, mes, 16)
                data_fim = date(ano, mes, ultimo_dia_mes)

            else:
                return "Selecione uma quinzena válida."

        except (ValueError, TypeError):
            return "O mês ou a quinzena informados são inválidos."

        conn = conectar_banco()

        try:
            with conn.cursor() as cursor:

                # Busca as comissões que ainda não pertencem
                # a nenhum fechamento.
                cursor.execute("""
                    SELECT
                        a.id_funcionario,
                        SUM(c.valor)
                    FROM comissao c
                    JOIN agendamento a
                        ON a.id_agendamento = c.id_agendamento
                    WHERE a.pagamento_status = 'PAGO'
                      AND a.data_pagamento::date
                          BETWEEN %s AND %s
                      AND c.id_fechamento IS NULL
                    GROUP BY a.id_funcionario
                """, (data_inicio, data_fim))

                funcionarios = cursor.fetchall()

                if not funcionarios:
                    conn.rollback()
                    return redirect(
                        "/relatorio-comissoes?sem_comissoes=1"
                    )

                for funcionario in funcionarios:

                    id_funcionario = funcionario[0]

                    # Cria o fechamento se ele ainda não existir.
                    cursor.execute("""
                        INSERT INTO fechamento_comissao (
                            id_funcionario,
                            data_inicio,
                            data_fim,
                            valor_total,
                            status
                        )
                        VALUES (%s, %s, %s, 0, 'PENDENTE')
                        ON CONFLICT (
                            id_funcionario,
                            data_inicio,
                            data_fim
                        ) DO NOTHING
                    """, (
                        id_funcionario,
                        data_inicio,
                        data_fim
                    ))

                    # Bloqueia o fechamento durante a conferência.
                    cursor.execute("""
                        SELECT id_fechamento, status
                        FROM fechamento_comissao
                        WHERE id_funcionario = %s
                          AND data_inicio = %s
                          AND data_fim = %s
                        FOR UPDATE
                    """, (
                        id_funcionario,
                        data_inicio,
                        data_fim
                    ))

                    fechamento = cursor.fetchone()

                    if fechamento[1] == "PAGO":
                        raise ValueError(
                            "Este fechamento já foi pago. "
                            "Não é possível adicionar comissões."
                        )

                    id_fechamento = fechamento[0]

                    # Vincula somente as comissões ainda livres.
                    cursor.execute("""
                        UPDATE comissao c
                        SET id_fechamento = %s
                        FROM agendamento a
                        WHERE a.id_agendamento = c.id_agendamento
                          AND a.id_funcionario = %s
                          AND a.pagamento_status = 'PAGO'
                          AND a.data_pagamento::date
                              BETWEEN %s AND %s
                          AND c.id_fechamento IS NULL
                    """, (
                        id_fechamento,
                        id_funcionario,
                        data_inicio,
                        data_fim
                    ))

                    # Atualiza o total com os valores já registrados.
                    cursor.execute("""
                        UPDATE fechamento_comissao
                        SET valor_total = (
                            SELECT COALESCE(SUM(valor), 0)
                            FROM comissao
                            WHERE id_fechamento = %s
                        )
                        WHERE id_fechamento = %s
                    """, (id_fechamento, id_fechamento))

            conn.commit()

        except ValueError as erro:
            conn.rollback()
            return str(erro)

        except Exception as erro:
            conn.rollback()
            print("ERRO NO FECHAMENTO DE COMISSÕES:", erro)
            return "Erro ao gerar o fechamento de comissões."

        finally:
            conn.close()

        return redirect("/relatorio-comissoes?gerado=1")

    conn = conectar_banco()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    fc.id_fechamento,
                    f.nome,
                    fc.data_inicio,
                    fc.data_fim,
                    fc.valor_total,
                    fc.status,
                    fc.data_pagamento
                FROM fechamento_comissao fc
                JOIN funcionario f
                    ON f.id_funcionario = fc.id_funcionario
                ORDER BY fc.data_inicio DESC, f.nome
            """)

            fechamentos = cursor.fetchall()

    finally:
        conn.close()

    return render_template(
        "relatorio_comissoes.html",
        fechamentos=fechamentos,
        gerado=request.args.get("gerado"),
        sem_comissoes=request.args.get("sem_comissoes"),
        mes_atual=mes_atual
    )


@app.route("/relatorios")
def relatorios():

    if "usuario_id" not in session:
        return redirect("/login")

    if (
        session.get("tipo_usuario") != "funcionario"
        or session.get("cargo", "").upper() != "ADMINISTRADOR"
    ):
        return redirect("/painel")

    return render_template("relatorios.html")


@app.route("/notificacoes")
def notificacoes():

    if "usuario_id" not in session:
        return redirect("/login")

    if session.get("tipo_usuario") != "cliente":
        return redirect("/painel")

    id_cliente = session["usuario_id"]

    conn = conectar_banco()

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                id_notificacao,
                id_agendamento,
                mensagem,
                tipo,
                lida,
                data_criacao
            FROM notificacao
            WHERE id_cliente = %s
            ORDER BY data_criacao DESC
        """, (id_cliente,))

        notificacoes = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*)
            FROM notificacao
            WHERE id_cliente = %s
              AND lida = FALSE
        """, (id_cliente,))

        nao_lidas = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "notificacoes.html",
        notificacoes=notificacoes,
        nao_lidas=nao_lidas
    )


@app.route("/notificacao-lida/<int:id_notificacao>", methods=["POST"])
def marcar_notificacao_lida(id_notificacao):

    if "usuario_id" not in session:
        return redirect("/login")

    if session.get("tipo_usuario") != "cliente":
        return redirect("/painel")

    conn = conectar_banco()

    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE notificacao
            SET lida = TRUE
            WHERE id_notificacao = %s
              AND id_cliente = %s
        """, (
            id_notificacao,
            session["usuario_id"]
        ))

    conn.commit()
    conn.close()

    return redirect("/notificacoes")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        senha = request.form["senha"]

        conn = conectar_banco()

        with conn.cursor() as cursor:

            # Tenta login de cliente
            cursor.execute(
                """
                SELECT id_cliente, nome, senha
                FROM cliente
                WHERE email = %s
                """,
                (email,)
            )

            usuario = cursor.fetchone()

            if usuario:
                if check_password_hash(usuario[2], senha):

                    session["usuario_id"] = usuario[0]
                    session["usuario_nome"] = usuario[1]
                    session["tipo_usuario"] = "cliente"

                    conn.close()

                    return redirect("/painel")


            
            cursor.execute(
                """
                SELECT id_funcionario, nome, senha, cargo
                FROM funcionario
                WHERE email = %s
                """,
                (email,)
            )

            funcionario = cursor.fetchone()

            print("FUNCIONÁRIO:", funcionario)

            if funcionario:
                if check_password_hash(funcionario[2], senha):

                    session["usuario_id"] = funcionario[0]
                    session["usuario_nome"] = funcionario[1]
                    session["tipo_usuario"] = "funcionario"
                    session["cargo"] = funcionario[3]

                    conn.close()

                    return redirect("/painel")


        conn.close()

        return "E-mail ou senha incorretos."

    return render_template("login.html")



@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)