from flask import Flask, render_template, request, redirect, session
import psycopg
import re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "sistema-ambar-chave-secreta"


def conectar_banco():
    return psycopg.connect(
        "dbname=sistema_agendamento user=postgres password=919580 host=localhost"
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

@app.route("/perfil")
def perfil():

    if "usuario_id" not in session:
        return redirect("/login")

    conn = conectar_banco()

    with conn.cursor() as cursor:

        if session["tipo_usuario"] == "cliente":

            cursor.execute("""
                SELECT nome, email, telefone
                FROM cliente
                WHERE id_cliente = %s
            """, (session["usuario_id"],))

            usuario = cursor.fetchone()

        else:

            cursor.execute("""
                SELECT nome, email, telefone, cargo
                FROM funcionario
                WHERE id_funcionario = %s
            """, (session["usuario_id"],))

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

        data = request.form["data"]
        horario = request.form["horario"]
        id_cliente = session["usuario_id"]
        id_funcionario = request.form["id_funcionario"]

        
        id_servicos = request.form.getlist("id_servico")


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

        conn.commit()

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

        hora = inicio.hour
        minuto = inicio.minute

        while True:

            horario = f"{hora:02d}:{minuto:02d}"

            if horario not in horarios_agendados:
                horarios.append(horario)

            minuto += 60

            if minuto >= 60:
                hora += minuto // 60
                minuto = minuto % 60

            if hora > fim.hour or (
                hora == fim.hour and minuto >= fim.minute
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

@app.route("/marcar-pago/<int:id_agendamento>")
def marcar_pago(id_agendamento):

    if "usuario_id" not in session:
        return redirect("/login")

    conn = conectar_banco()

    with conn.cursor() as cursor:

        cursor.execute("""
            SELECT valor_total
            FROM agendamento
            WHERE id_agendamento = %s
              AND id_funcionario = %s
        """, (
            id_agendamento,
            session["usuario_id"]
        ))

        resultado = cursor.fetchone()

        if resultado:

            valor_total = resultado[0]

            cursor.execute("""
                UPDATE agendamento
                SET pagamento_status = 'PAGO',
                    data_pagamento = CURRENT_TIMESTAMP,
                    valor_total = %s
                WHERE id_agendamento = %s
                  AND id_funcionario = %s
            """, (
                valor_total,
                id_agendamento,
                session["usuario_id"]
            ))

    conn.commit()
    conn.close()

    return redirect("/meus-agendamentos")

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