from functools import wraps
import os
import re
import sqlite3
from flask import Flask, flash, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave-secreta-sefaz-al-2026")
SENHA_ADMIN = os.environ.get("SENHA_ADMIN", "admin123")
DB_PATH = "portal_dados.db"


def get_db():
  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row
  return conn


def init_db():
  with get_db() as conn:
    conn.execute("""
            CREATE TABLE IF NOT EXISTS itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                categoria TEXT DEFAULT 'Legislação Tributária',
                resumo TEXT,
                conteudo TEXT NOT NULL,
                link_externo TEXT,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.execute("""
            CREATE TABLE IF NOT EXISTS info_concurso (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                orgao TEXT,
                cargos TEXT,
                banca_status TEXT,
                remuneracao TEXT,
                vagas_requisitos TEXT,
                aviso_geral TEXT
            )
        """)
    # Insere os dados iniciais padrão da SEFAZ-AL se ainda não existirem
    existe = conn.execute("SELECT 1 FROM info_concurso WHERE id = 1").fetchone()
    if not existe:
      conn.execute(
          """
                INSERT INTO info_concurso (id, orgao, cargos, banca_status, remuneracao, vagas_requisitos, aviso_geral)
                VALUES (1, ?, ?, ?, ?, ?, ?)
            """,
          (
              "Secretaria de Estado da Fazenda de Alagoas (SEFAZ-AL)",
              "Auditor Fiscal da Receita Estadual e Auditor de Finanças e"
              " Controle",
              "Em preparação / Aguardando definição (Última banca: Cebraspe)",
              "A partir de R$ 9.500,00 + Produtividade / Gratificações",
              "Nível Superior em qualquer área de formação",
              "Clique em 'Área de Edição' e depois em 'Editar Painel' para"
              " atualizar datas, comissão ou links do edital.",
          ),
      )


def gerar_slug(texto):
  texto = texto.lower().strip()
  texto = re.sub(r"[áàâãä]", "a", texto)
  texto = re.sub(r"[éèêë]", "e", texto)
  texto = re.sub(r"[íìîï]", "i", texto)
  texto = re.sub(r"[óòôõö]", "o", texto)
  texto = re.sub(r"[úùûü]", "u", texto)
  texto = re.sub(r"[ç]", "c", texto)
  texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
  return texto or "item"


def limpar_tags_html(texto_html):
  limpo = re.sub(r"<[^>]+>", " ", texto_html)
  limpo = re.sub(r"\s+", " ", limpo).strip()
  return limpo


def admin_required(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    if not session.get("logado"):
      return redirect(url_for("login", next=request.url))
    return f(*args, **kwargs)

  return decorated


BASE_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ titulo_pagina }} | Portal SEFAZ-AL</title>
    <link href="https://cdn.quilljs.com/1.3.7/quill.snow.css" rel="stylesheet">
    <style>
        :root {
            --al-azul: #004a99;
            --al-azul-escuro: #002d62;
            --al-vermelho: #ce1126;
            --bg: #f1f5f9;
            --card: #ffffff;
            --text: #0f172a;
            --muted: #475569;
        }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 0; }
        
        /* Faixa tricolor discreta inspirada na bandeira de Alagoas */
        .faixa-alagoas { height: 5px; background: linear-gradient(90deg, var(--al-vermelho) 33.3%, #ffffff 33.3%, #ffffff 66.6%, var(--al-azul) 66.6%); }
        
        header { background: linear-gradient(135deg, var(--al-azul-escuro), var(--al-azul)); color: white; padding: 18px 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.12); }
        .brand { display: flex; flex-direction: column; }
        .brand a { color: white; text-decoration: none; font-weight: 800; font-size: 20px; letter-spacing: 0.3px; }
        .brand span { font-size: 12px; color: #cbd5e1; margin-top: 2px; }
        
        .nav-actions { display: flex; gap: 10px; align-items: center; }
        .btn { padding: 8px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; border: none; cursor: pointer; display: inline-block; transition: 0.15s; }
        .btn-primary { background: var(--al-azul); color: white; }
        .btn-primary:hover { background: var(--al-azul-escuro); }
        .btn-destaque { background: var(--al-vermelho); color: white; }
        .btn-destaque:hover { background: #a60d1e; }
        .btn-outline { background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.35); color: white; }
        .btn-outline:hover { background: rgba(255,255,255,0.22); }
        .btn-danger { background: #dc2626; color: white; }
        .btn-copy { background: #e2e8f0; color: #1e293b; font-size: 12px; padding: 6px 10px; }
        .btn-copy:hover { background: #cbd5e1; }
        
        .container { max-width: 1100px; margin: 24px auto; padding: 0 20px; }
        
        /* Painel Superior de Informações do Concurso SEFAZ-AL */
        .painel-concurso { background: white; border-radius: 10px; border: 1px solid #cbd5e1; border-top: 4px solid var(--al-azul); padding: 22px 24px; margin-bottom: 26px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); }
        .painel-topo { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 16px; }
        .painel-topo h2 { margin: 0; font-size: 18px; color: var(--al-azul-escuro); display: flex; align-items: center; gap: 8px; }
        .tag-estado { background: var(--al-vermelho); color: white; font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: 700; }
        
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
        .info-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; }
        .info-label { font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--al-azul); letter-spacing: 0.4px; margin-bottom: 4px; }
        .info-valor { font-size: 14px; font-weight: 600; color: #1e293b; line-height: 1.4; }
        .aviso-concurso { margin-top: 14px; background: #eff6ff; border-left: 4px solid var(--al-azul); padding: 10px 14px; font-size: 13px; color: #1e3a8a; border-radius: 0 6px 6px 0; }

        .busca-bar { display: flex; gap: 10px; margin-bottom: 20px; }
        .busca-bar input { flex: 1; padding: 12px 14px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 15px; background: white; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 18px; }
        .card { background: var(--card); border: 1px solid #e2e8f0; border-left: 4px solid var(--al-azul); border-radius: 10px; padding: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); display: flex; flex-direction: column; justify-content: space-between; }
        .badge { display: inline-block; background: #dbeafe; color: var(--al-azul-escuro); font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; margin-bottom: 8px; }
        .card h3 { margin: 0 0 8px 0; font-size: 17px; }
        .card h3 a { color: var(--text); text-decoration: none; }
        .card h3 a:hover { color: var(--al-azul); }
        .card p { color: var(--muted); font-size: 14px; margin: 0 0 16px 0; line-height: 1.45; }
        .card-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 12px; gap: 6px; flex-wrap: wrap; }
        
        .box-form { background: white; padding: 28px; border-radius: 10px; border: 1px solid #e2e8f0; max-width: 850px; margin: 0 auto; }
        label { display: block; font-weight: 600; margin-top: 14px; margin-bottom: 5px; font-size: 13px; }
        input[type="text"], input[type="password"], input[type="url"] { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; box-sizing: border-box; font-family: inherit; }
        
        #editor-container { height: 380px; font-size: 15px; font-family: 'Segoe UI', Arial, sans-serif; background: white; }
        .ql-toolbar.ql-snow { border-top-left-radius: 6px; border-top-right-radius: 6px; background: #f8fafc; border-color: #cbd5e1; }
        .ql-container.ql-snow { border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; border-color: #cbd5e1; }

        .conteudo-leitura { background: white; padding: 40px 48px; border-radius: 10px; border: 1px solid #e2e8f0; line-height: 1.65; font-size: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); overflow-x: auto; }
        .conteudo-leitura p { margin: 0 0 12px 0; }
        .conteudo-leitura h1, .conteudo-leitura h2, .conteudo-leitura h3 { margin-top: 20px; margin-bottom: 10px; color: var(--al-azul-escuro); }
        .conteudo-leitura ul, .conteudo-leitura ol { padding-left: 24px; margin-bottom: 14px; }
        .conteudo-leitura blockquote { border-left: 4px solid var(--al-azul); margin: 16px 0; padding: 8px 16px; background: #f8fafc; color: #334155; }
        .conteudo-leitura table { border-collapse: collapse; width: 100%; margin: 16px 0; }
        .conteudo-leitura table td, .conteudo-leitura table th { border: 1px solid #cbd5e1; padding: 8px 12px; }
        @media (max-width: 650px) { .conteudo-leitura { padding: 24px 20px; } }
        .alerta { background: #fef3c7; color: #92400e; padding: 10px 14px; border-radius: 6px; margin-bottom: 16px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="faixa-alagoas"></div>
    <header>
        <div class="brand">
            <a href="/">🏛️ Central de Estudos • SEFAZ-AL</a>
            <span>Secretaria de Estado da Fazenda de Alagoas — Repositório de Materiais & Links</span>
        </div>
        <div class="nav-actions">
            {% if session.get('logado') %}
                <a href="/novo" class="btn btn-destaque">+ Novo Material</a>
                <a href="/logout" class="btn btn-outline">Sair</a>
            {% else %}
                <a href="/login" class="btn btn-outline">Área de Edição</a>
            {% endif %}
        </div>
    </header>
    <div class="container">
        {% with msgs = get_flashed_messages() %}
            {% if msgs %}<div class="alerta">{{ msgs[0] }}</div>{% endif %}
        {% endwith %}
        {{ corpo | safe }}
    </div>

    <script src="https://cdn.quilljs.com/1.3.7/quill.min.js"></script>
    <script>
        function copiarLink(url) {
            navigator.clipboard.writeText(url);
            alert('Link direto copiado: ' + url);
        }

        const editorDiv = document.getElementById('editor-container');
        if (editorDiv) {
            const quill = new Quill('#editor-container', {
                theme: 'snow',
                placeholder: 'Cole aqui o texto diretamente do Word ou Google Docs (Ctrl + V), ou digite e formate usando a barra acima...',
                modules: {
                    toolbar: [
                        [{ 'header': [1, 2, 3, false] }],
                        ['bold', 'italic', 'underline', 'strike'],
                        [{ 'color': [] }, { 'background': [] }],
                        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                        [{ 'align': [] }],
                        ['blockquote', 'link'],
                        ['clean']
                    ]
                }
            });

            const form = editorDiv.closest('form');
            form.addEventListener('submit', function(e) {
                const inputOculto = document.getElementById('conteudo_html');
                inputOculto.value = quill.root.innerHTML;
                if (quill.getText().trim().length === 0) {
                    e.preventDefault();
                    alert('Por favor, insira algum conteúdo antes de salvar.');
                }
            });
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
  busca = request.args.get("q", "").strip()
  cat = request.args.get("cat", "").strip()
  with get_db() as conn:
    info = conn.execute("SELECT * FROM info_concurso WHERE id = 1").fetchone()
    if busca:
      itens = conn.execute(
          "SELECT * FROM itens WHERE titulo LIKE ? OR resumo LIKE ? OR conteudo"
          " LIKE ? ORDER BY atualizado_em DESC",
          (f"%{busca}%", f"%{busca}%", f"%{busca}%"),
      ).fetchall()
    elif cat:
      itens = conn.execute(
          "SELECT * FROM itens WHERE categoria = ? ORDER BY atualizado_em DESC",
          (cat,),
      ).fetchall()
    else:
      itens = conn.execute(
          "SELECT * FROM itens ORDER BY atualizado_em DESC"
      ).fetchall()

    categorias = conn.execute(
        "SELECT DISTINCT categoria FROM itens ORDER BY categoria"
    ).fetchall()

  btn_editar_painel = ""
  if session.get("logado"):
    btn_editar_painel = (
        '<a href="/editar-painel" class="btn btn-primary">✏️ Editar Painel do'
        " Concurso</a>"
    )

  painel_html = f"""
    <div class="painel-concurso">
        <div class="painel-topo">
            <h2><span class="tag-estado">ALAGOAS</span> Panorama Geral — Concurso SEFAZ-AL</h2>
            {btn_editar_painel}
        </div>
        <div class="info-grid">
            <div class="info-box">
                <div class="info-label">Órgão</div>
                <div class="info-valor">{info['orgao']}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Cargos Previstos</div>
                <div class="info-valor">{info['cargos']}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Status / Banca</div>
                <div class="info-valor">{info['banca_status']}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Remuneração</div>
                <div class="info-valor">{info['remuneracao']}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Escolaridade / Requisitos</div>
                <div class="info-valor">{info['vagas_requisitos']}</div>
            </div>
        </div>
        <div class="aviso-concurso">
            <strong>📌 Quadro de Avisos & Cronograma:</strong> {info['aviso_geral']}
        </div>
    </div>
    """

  pills = (
      '<div style="margin-bottom: 18px; display:flex; gap:8px; flex-wrap:wrap;'
      ' align-items:center;">'
  )
  pills += (
      '<span style="font-size:13px; font-weight:700; color:#475569;'
      ' margin-right:4px;">Disciplinas / Pastas:</span>'
  )
  pills += '<a href="/" class="btn btn-copy">Todos</a>'
  for c in categorias:
    pills += (
        f'<a href="/?cat={c["categoria"]}" class="btn'
        f' btn-copy">{c["categoria"]}</a>'
    )
  pills += "</div>"

  cards_html = ""
  for item in itens:
    url_direta = request.host_url.rstrip("/") + url_for(
        "ver_item", slug=item["slug"]
    )
    botoes_admin = ""
    if session.get("logado"):
      botoes_admin = (
          f'<a href="/editar/{item["id"]}" class="btn btn-copy">Editar</a>'
      )

    ext_btn = ""
    if item["link_externo"]:
      ext_btn = (
          f'<a href="{item["link_externo"]}" target="_blank" class="btn'
          ' btn-primary">Abrir Link ↗</a>'
      )

    texto_previa = (
        item["resumo"] or limpar_tags_html(item["conteudo"])[:140] + "..."
    )

    cards_html += f"""
        <div class="card">
            <div>
                <span class="badge">{item['categoria']}</span>
                <h3><a href="/p/{item['slug']}">{item['titulo']}</a></h3>
                <p>{texto_previa}</p>
            </div>
            <div class="card-footer">
                <a href="/p/{item['slug']}" class="btn btn-copy">Abrir Página</a>
                <button type="button" class="btn btn-copy" onclick="copiarLink('{url_direta}')">Copiar Link</button>
                {ext_btn}
                {botoes_admin}
            </div>
        </div>
        """

  if not cards_html:
    cards_html = (
        "<p>Nenhum material cadastrado ainda. Clique em <strong>Área de"
        " Edição</strong> no topo para inserir suas matérias da SEFAZ-AL.</p>"
    )

  corpo = f"""
    {painel_html}
    <form class="busca-bar" method="GET" action="/">
        <input type="text" name="q" value="{busca}" placeholder="Pesquisar em Legislação Tributária, Auditoria, Contabilidade, Links...">
        <button type="submit" class="btn btn-primary">Buscar</button>
    </form>
    {pills}
    <div class="grid">{cards_html}</div>
    """
  return render_template_string(BASE_HTML, titulo_pagina="Início", corpo=corpo)


@app.route("/editar-painel", methods=["GET", "POST"])
@admin_required
def editar_painel():
  with get_db() as conn:
    if request.method == "POST":
      conn.execute(
          """
                UPDATE info_concurso
                SET orgao = ?, cargos = ?, banca_status = ?, remuneracao = ?, vagas_requisitos = ?, aviso_geral = ?
                WHERE id = 1
            """,
          (
              request.form.get("orgao", "").strip(),
              request.form.get("cargos", "").strip(),
              request.form.get("banca_status", "").strip(),
              request.form.get("remuneracao", "").strip(),
              request.form.get("vagas_requisitos", "").strip(),
              request.form.get("aviso_geral", "").strip(),
          ),
      )
      flash("Informações gerais da SEFAZ-AL atualizadas!")
      return redirect(url_for("index"))

    info = conn.execute("SELECT * FROM info_concurso WHERE id = 1").fetchone()

  corpo = f"""
    <div class="box-form">
        <h2>Editar Painel Geral — Concurso SEFAZ-AL</h2>
        <form method="POST">
            <label>Órgão:</label>
            <input type="text" name="orgao" value="{info['orgao']}" required>

            <label>Cargos:</label>
            <input type="text" name="cargos" value="{info['cargos']}" required>

            <label>Status / Banca Organizadora:</label>
            <input type="text" name="banca_status" value="{info['banca_status']}" required>

            <label>Remuneração:</label>
            <input type="text" name="remuneracao" value="{info['remuneracao']}" required>

            <label>Escolaridade / Vagas / Requisitos:</label>
            <input type="text" name="vagas_requisitos" value="{info['vagas_requisitos']}" required>

            <label>Quadro de Avisos / Datas / Cronograma:</label>
            <input type="text" name="aviso_geral" value="{info['aviso_geral']}" required>

            <button type="submit" class="btn btn-primary" style="margin-top:18px;">Salvar Dados do Concurso</button>
        </form>
    </div>
    """
  return render_template_string(
      BASE_HTML, titulo_pagina="Editar Painel SEFAZ-AL", corpo=corpo
  )


@app.route("/p/<slug>")
def ver_item(slug):
  with get_db() as conn:
    item = conn.execute(
        "SELECT * FROM itens WHERE slug = ?", (slug,)
    ).fetchone()
  if not item:
    return "Página não encontrada.", 404

  url_direta = request.host_url.rstrip("/") + url_for(
      "ver_item", slug=item["slug"]
  )
  acoes = (
      '<button type="button" class="btn btn-copy"'
      f" onclick=\"copiarLink('{url_direta}')\">Copiar Link desta"
      " Página</button>"
  )
  if item["link_externo"]:
    acoes += (
        f' <a href="{item["link_externo"]}" target="_blank" class="btn'
        ' btn-primary">Acessar Link Externo ↗</a>'
    )
  if session.get("logado"):
    acoes += (
        f' <a href="/editar/{item["id"]}" class="btn btn-copy">Editar'
        " Conteúdo</a>"
    )

  corpo = f"""
    <div style="margin-bottom: 16px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div>
            <span class="badge">{item['categoria']}</span>
            <h1 style="margin:4px 0; color:#002d62;">{item['titulo']}</h1>
            <small style="color:#64748b;">Link direto: <code>{url_direta}</code></small>
        </div>
        <div>{acoes}</div>
    </div>
    <div class="conteudo-leitura">{item['conteudo']}</div>
    """
  return render_template_string(
      BASE_HTML, titulo_pagina=item["titulo"], corpo=corpo
  )


@app.route("/login", methods=["GET", "POST"])
def login():
  if request.method == "POST":
    if request.form.get("senha") == SENHA_ADMIN:
      session["logado"] = True
      return redirect(url_for("index"))
    flash("Senha incorreta.")
  corpo = """
    <div class="box-form" style="max-width:400px;">
        <h2>Acesso Administrativo • SEFAZ-AL</h2>
        <form method="POST">
            <label>Senha de Edição:</label>
            <input type="password" name="senha" required autofocus>
            <button type="submit" class="btn btn-primary" style="margin-top:16px; width:100%;">Entrar</button>
        </form>
    </div>
    """
  return render_template_string(BASE_HTML, titulo_pagina="Login", corpo=corpo)


@app.route("/logout")
def logout():
  session.clear()
  return redirect(url_for("index"))


@app.route("/novo", methods=["GET", "POST"])
@admin_required
def novo():
  if request.method == "POST":
    titulo = request.form.get("titulo", "").strip()
    categoria = (
        request.form.get("categoria", "Legislação Tributária").strip()
        or "Legislação Tributária"
    )
    resumo = request.form.get("resumo", "").strip()
    conteudo = request.form.get("conteudo", "").strip()
    link_externo = request.form.get("link_externo", "").strip()
    slug_base = gerar_slug(request.form.get("slug") or titulo)

    with get_db() as conn:
      slug = slug_base
      contador = 2
      while conn.execute(
          "SELECT 1 FROM itens WHERE slug = ?", (slug,)
      ).fetchone():
        slug = f"{slug_base}-{contador}"
        contador += 1

      conn.execute(
          "INSERT INTO itens (titulo, slug, categoria, resumo, conteudo,"
          " link_externo) VALUES (?, ?, ?, ?, ?, ?)",
          (titulo, slug, categoria, resumo, conteudo, link_externo),
      )
    flash("Material publicado com sucesso!")
    return redirect(url_for("ver_item", slug=slug))

  corpo = """
    <div class="box-form">
        <h2>Cadastrar Novo Material • SEFAZ-AL</h2>
        <form method="POST">
            <label>Título:</label>
            <input type="text" name="titulo" placeholder="Ex: Lei Estadual nº 5.900/96 - ICMS Alagoas" required>

            <label>Link personalizado (opcional - ex: icms-alagoas):</label>
            <input type="text" name="slug" placeholder="Deixe em branco para gerar automaticamente pelo título">

            <label>Disciplina / Categoria:</label>
            <input type="text" name="categoria" value="Legislação Tributária" placeholder="Ex: Legislação Tributária, Auditoria, Contabilidade, Direito Constitucional">

            <label>Resumo curto (aparece no cartão da página inicial):</label>
            <input type="text" name="resumo" placeholder="Breve descrição do conteúdo">

            <label>Link externo de destino (opcional - ex: lei no portal da SEFAZ-AL ou caderno de questões):</label>
            <input type="url" name="link_externo" placeholder="https://...">

            <label>Conteúdo formatado (cole direto do Word / Google Docs):</label>
            <div id="editor-container"></div>
            <input type="hidden" name="conteudo" id="conteudo_html">

            <button type="submit" class="btn btn-primary" style="margin-top:18px;">Salvar e Gerar Link</button>
        </form>
    </div>
    """
  return render_template_string(
      BASE_HTML, titulo_pagina="Novo Material", corpo=corpo
  )


@app.route("/editar/<int:item_id>", methods=["GET", "POST"])
@admin_required
def editar(item_id):
  with get_db() as conn:
    item = conn.execute(
        "SELECT * FROM itens WHERE id = ?", (item_id,)
    ).fetchone()
    if not item:
      return "Item não encontrado.", 404

    if request.method == "POST":
      if request.form.get("acao") == "excluir":
        conn.execute("DELETE FROM itens WHERE id = ?", (item_id,))
        flash("Material excluído.")
        return redirect(url_for("index"))

      titulo = request.form.get("titulo", "").strip()
      categoria = (
          request.form.get("categoria", "Legislação Tributária").strip()
          or "Legislação Tributária"
      )
      resumo = request.form.get("resumo", "").strip()
      conteudo = request.form.get("conteudo", "").strip()
      link_externo = request.form.get("link_externo", "").strip()

      conn.execute(
          """UPDATE itens
                   SET titulo = ?, categoria = ?, resumo = ?, conteudo = ?, link_externo = ?, atualizado_em = CURRENT_TIMESTAMP
                   WHERE id = ?""",
          (titulo, categoria, resumo, conteudo, link_externo, item_id),
      )
      flash("Atualizado com sucesso!")
      return redirect(url_for("ver_item", slug=item["slug"]))

  corpo = f"""
    <div class="box-form">
        <h2>Editar: {item['titulo']}</h2>
        <form method="POST">
            <label>Título:</label>
            <input type="text" name="titulo" value="{item['titulo']}" required>

            <label>Disciplina / Categoria:</label>
            <input type="text" name="categoria" value="{item['categoria']}">

            <label>Resumo curto:</label>
            <input type="text" name="resumo" value="{item['resumo'] or ''}">

            <label>Link externo (opcional):</label>
            <input type="url" name="link_externo" value="{item['link_externo'] or ''}">

            <label>Conteúdo formatado:</label>
            <div id="editor-container">{item['conteudo']}</div>
            <input type="hidden" name="conteudo" id="conteudo_html">

            <div style="display:flex; justify-content:space-between; margin-top:18px;">
                <button type="submit" class="btn btn-primary">Salvar Alterações</button>
                <button type="submit" name="acao" value="excluir" class="btn btn-danger" onclick="return confirm('Excluir este material permanentemente?');">Excluir</button>
            </div>
        </form>
    </div>
    """
  return render_template_string(BASE_HTML, titulo_pagina="Editar", corpo=corpo)


init_db()

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5005))
  print(f"\nPortal SEFAZ-AL iniciado! Acesse: http://127.0.0.1:{port}")
  app.run(host="0.0.0.0", port=port, debug=False)
