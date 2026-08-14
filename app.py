from flask import Flask, render_template, request, redirect, session
import psycopg
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "sistema-ambar-chave-secreta"


def conectar_banco():
    return psycopg.connect(
        "dbname=sistema_agendamento user=postgres password=919580 host=localhost"
    )


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/painel")
def painel():
    if "usuario_id" not in session:
        return redirect("/login")

    return render_template("painel.html")


@app.route("/clientes")
def clientes():
    conn = conectar_banco()

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM cliente ORDER BY id_cliente")
        clientes = cursor.fetchall()

    conn.close()

    return render_template("clientes.html", clientes=clientes)


@app.route("/novo-cliente", methods=["GET", "POST"])
def novo_cliente():

    if request.method == "POST":

        nome = request.form["nome"]
        email = request.form["email"]
        senha = generate_password_hash(request.form["senha"])
        telefone = request.form["telefone"]

        conn = conectar_banco()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO cliente (nome, email, senha, telefone)
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


@app.route("/novo-funcionario", methods=["GET", "POST"])
def novo_funcionario():

    if request.method == "POST":

        nome = request.form["nome"]
        email = request.form["email"]
        senha = generate_password_hash(request.form["senha"])
        telefone = request.form["telefone"]
        cargo = request.form["cargo"]

        conn = conectar_banco()

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
        conn.close()

        return redirect("/login")

    return render_template("login.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        senha = request.form["senha"]

        conn = conectar_banco()

        with conn.cursor() as cursor:

            cursor.execute(
                "SELECT id_cliente, nome, senha FROM cliente WHERE email = %s",
                (email,)
            )

            usuario = cursor.fetchone()

            if usuario and check_password_hash(usuario[2], senha):

                session["usuario_id"] = usuario[0]
                session["usuario_nome"] = usuario[1]
                session["tipo_usuario"] = "cliente"

                conn.close()

                return redirect("/painel")

            cursor.execute(
                "SELECT id_funcionario, nome, senha FROM funcionario WHERE email = %s",
                (email,)
            )

            usuario = cursor.fetchone()

            if usuario and check_password_hash(usuario[2], senha):

                session["usuario_id"] = usuario[0]
                session["usuario_nome"] = usuario[1]
                session["tipo_usuario"] = "funcionario"

                conn.close()

                return redirect("/painel")

        conn.close()

        return "E-mail ou senha incorretos."

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)