from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file
import pandas as pd
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import json
import uuid
import hashlib
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'supersecret123'
CONFIG_FILE = 'config.json'
DEFAULT_USERS_FILE = 'users.xlsx'
DEFAULT_STOCK_FILE = 'estoque.xlsx'
DEFAULT_SALES_FILE = 'vendas.xlsx'

# ---------- CONFIGURAÇÃO ----------
def carregar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        config = {
            "stock_path": DEFAULT_STOCK_FILE,
            "sales_path": DEFAULT_SALES_FILE,
            "users_path": DEFAULT_USERS_FILE
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        return config

def salvar_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

config = carregar_config()

# ---------- USUÁRIOS ----------
def criar_usuario_default(path):
    if not path:
        path = DEFAULT_USERS_FILE
    if not os.path.exists(path):
        df = pd.DataFrame([{"username": "admin", "password": generate_password_hash("admin123"), "role": "admin"}])
        df.to_excel(path, index=False)

def carregar_usuarios():
    path = config.get("users_path") or DEFAULT_USERS_FILE
    criar_usuario_default(path)
    return pd.read_excel(path)

def salvar_usuarios(df):
    path = config.get("users_path") or DEFAULT_USERS_FILE
    df.to_excel(path, index=False)

# ---------- ESTOQUE E VENDAS ----------
def carregar_estoque():
    path = config.get("stock_path") or DEFAULT_STOCK_FILE
    if os.path.exists(path):
        return pd.read_excel(path)
    else:
        df = pd.DataFrame(columns=["codigo","nome","preco","estoque"])
        df.to_excel(path, index=False)
        return df

def salvar_estoque(df):
    path = config.get("stock_path") or DEFAULT_STOCK_FILE
    df.to_excel(path, index=False)

def carregar_vendas():
    path = config.get("sales_path") or DEFAULT_SALES_FILE
    if os.path.exists(path):
        return pd.read_excel(path)
    else:
        df = pd.DataFrame(columns=["datetime","usuario","itens","total"])
        df.to_excel(path, index=False)
        return df

def salvar_vendas(df):
    path = config.get("sales_path") or DEFAULT_SALES_FILE
    df.to_excel(path, index=False)

# ---------- ROTAS ----------
@app.route('/')
def home():
    return redirect(url_for("login"))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        df_users = carregar_usuarios()
        user = df_users[df_users["username"]==username]
        if not user.empty and check_password_hash(user.iloc[0]["password"], password):
            session["user"] = username
            session["role"] = user.iloc[0]["role"]
            return redirect(url_for("vendas"))
        else:
            flash("Usuário ou senha inválidos")
    return render_template("login.html")

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]
        df_users = carregar_usuarios()
        if username in df_users["username"].values:
            flash("Usuário já existe!")
        else:
            df_users = pd.concat([df_users, pd.DataFrame([{
                "username": username,
                "password": generate_password_hash(password),
                "role": role
            }])], ignore_index=True)
            salvar_usuarios(df_users)
            flash("Cadastro realizado! Faça login.")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route('/config', methods=["GET","POST"])
def config_page():
    if "user" not in session:
        return redirect(url_for("login"))
    if request.method=="POST":
        config["stock_path"] = request.form.get("stock_path") or DEFAULT_STOCK_FILE
        config["sales_path"] = request.form.get("sales_path") or DEFAULT_SALES_FILE
        config["users_path"] = request.form.get("users_path") or DEFAULT_USERS_FILE
        salvar_config(config)
        flash("Configuração salva!")
    return render_template("config.html", config=config)

# ---------- ESTOQUE ----------
df_estoque = carregar_estoque()

@app.route('/estoque', methods=["GET","POST"])
def estoque():
    if "user" not in session:
        return redirect(url_for("login"))
    global df_estoque
    df_estoque = carregar_estoque()
    return render_template(
        "estoque.html",
        estoque=df_estoque.to_dict(orient="records"),
        role=session.get("role")
    )

@app.route('/adicionar_produto', methods=['POST'])
def adicionar_produto():
    if "user" not in session:
        return redirect(url_for("login"))
    codigo = request.form['codigo']
    nome = request.form['nome']
    preco = float(request.form['preco'])
    estoque_val = int(request.form['estoque'])
    global df_estoque
    novo_produto = pd.DataFrame([{
        'codigo': codigo,
        'nome': nome,
        'preco': preco,
        'estoque': estoque_val
    }])
    df_estoque = pd.concat([df_estoque, novo_produto], ignore_index=True)
    salvar_estoque(df_estoque)
    return redirect(url_for('estoque'))

# ---------- VENDAS ----------
@app.route('/vendas', methods=['GET', 'POST'])
def vendas():
    if "user" not in session:
        return redirect(url_for("login"))
    df_estoque = carregar_estoque()
    return render_template("vendas.html", estoque=df_estoque.to_dict(orient="records"))

@app.route('/registrar_venda', methods=["POST"])
def registrar_venda():
    if "user" not in session:
        return jsonify({"erro":"Sem sessão"}),403
    dados = request.get_json()
    itens = dados.get("itens", [])
    total = float(dados.get("total",0))
    df_vendas = carregar_vendas()
    df_vendas = pd.concat([df_vendas, pd.DataFrame([{
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "usuario": session["user"],
        "itens": str(itens),
        "total": total
    }])], ignore_index=True)
    salvar_vendas(df_vendas)
    df_estoque = carregar_estoque()
    for item in itens:
        df_estoque.loc[df_estoque["codigo"]==item["codigo"],"estoque"] -= item["quantidade"]
    salvar_estoque(df_estoque)
    return jsonify({"mensagem":"Venda registrada!"})

# ---------- HISTÓRICO ----------
@app.route("/historico_vendas_json")
def historico_vendas_json():
    df_vendas = carregar_vendas()
    data_filtro = request.args.get("data", "")
    usuario_filtro = request.args.get("usuario", "")
    if data_filtro:
        df_vendas = df_vendas[df_vendas["datetime"].str.startswith(data_filtro)]
    if usuario_filtro:
        df_vendas = df_vendas[df_vendas["usuario"] == usuario_filtro]
    historico_dict = {}
    for _, row in df_vendas.iterrows():
        data_somente = row["datetime"].split(" ")[0]
        itens = eval(row["itens"])
        for i in itens:
            key = (data_somente, i["nome"], row["usuario"])
            if key not in historico_dict:
                historico_dict[key] = {"quantidade": 0, "total": 0}
            historico_dict[key]["quantidade"] += i["quantidade"]
            historico_dict[key]["total"] += i["quantidade"] * i["preco"]
    historico = []
    soma_total = 0
    for (data, nome, usuario), values in historico_dict.items():
        historico.append({
            "data": data,
            "nome": nome,
            "quantidade": values["quantidade"],
            "total": values["total"],
            "usuario": usuario
        })
        soma_total += values["total"]
    return jsonify({
        "historico": historico,
        "soma_total": soma_total
    })

@app.route('/historico_vendas')
def historico_vendas():
    df_usuarios = carregar_usuarios()
    usuarios = df_usuarios.to_dict(orient="records")
    data_filtro = request.args.get("data", "")
    usuario_filtro = request.args.get("usuario", "")
    return render_template("historico_vendas.html", historico=[], soma_total=0, usuarios=usuarios, data_filtro=data_filtro, usuario_filtro=usuario_filtro, role=session.get("role"))

@app.route('/deletar_historico', methods=['POST'])
def deletar_historico():
    if "user" not in session or session.get("role") != "admin":
        flash("Acesso negado!")
        return redirect(url_for("historico_vendas"))
    df_vendas = pd.DataFrame(columns=["datetime","usuario","itens","total"])
    salvar_vendas(df_vendas)
    flash("Histórico deletado com sucesso!")
    return redirect(url_for("historico_vendas"))

# ---------- USUÁRIOS ----------
@app.route('/usuarios', methods=["GET","POST"])
def usuarios():
    if "user" not in session or session.get("role")!="admin":
        return redirect(url_for("vendas"))
    df_users = carregar_usuarios()
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]
        df_users = pd.concat([df_users, pd.DataFrame([{
            "username": username,
            "password": generate_password_hash(password),
            "role": role
        }])], ignore_index=True)
        salvar_usuarios(df_users)
        flash("Usuário adicionado!")
    return render_template("usuarios.html", usuarios=df_users.to_dict(orient="records"))

# ---------- PRODUTOS ----------
@app.route('/deletar_produto', methods=['POST'])
def deletar_produto():
    if "user" not in session or session.get("role") != "admin":
        flash("Acesso negado!")
        return redirect(url_for("estoque"))
    codigo = request.form.get("codigo")
    df_estoque = carregar_estoque()
    df_estoque["codigo"] = df_estoque["codigo"].astype(str)
    df_estoque = df_estoque[df_estoque["codigo"] != codigo]
    salvar_estoque(df_estoque)
    flash("Produto deletado com sucesso!")
    return redirect(url_for("estoque"))

@app.route('/editar_estoque', methods=['POST'])
def editar_estoque():
    if "user" not in session or session.get("role") != "admin":
        flash("Acesso negado!")
        return redirect(url_for("estoque"))

    codigo = request.form.get("codigo")
    novo_estoque = request.form.get("novo_estoque")
    novo_preco = request.form.get("novo_preco")

    df_estoque = carregar_estoque()

    if codigo in df_estoque["codigo"].astype(str).values:
        if novo_estoque is not None:
            df_estoque.loc[df_estoque["codigo"].astype(str) == codigo, "estoque"] = int(novo_estoque)
        if novo_preco is not None:
            df_estoque.loc[df_estoque["codigo"].astype(str) == codigo, "preco"] = float(novo_preco)
        salvar_estoque(df_estoque)
        flash("Produto atualizado com sucesso!")
        return redirect(url_for("estoque"))
    else:
        flash("Produto não encontrado! Cadastre-o abaixo.")
        # Redireciona para o formulário de cadastro
        return redirect(url_for("cadastrar_item"))

@app.route('/upload_estoque', methods=['POST'])
def upload_estoque():
    if "user" not in session or session.get("role") != "admin":
        flash("Acesso negado!")
        return redirect(url_for("estoque"))
    arquivo = request.files.get('arquivo_excel')
    if arquivo and arquivo.filename.endswith('.xlsx'):
        caminho = config.get("stock_path") or DEFAULT_STOCK_FILE
        arquivo.save(caminho)
        flash("Estoque atualizado com sucesso!")
    else:
        flash("Arquivo inválido. Envie um arquivo .xlsx válido.")
    return redirect(url_for("estoque"))

@app.route('/estoque_json')
def estoque_json():
    try:
        return jsonify(df_estoque.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__=="__main__":
    app.run(debug=True, host="0.0.0.0", port=5006)
