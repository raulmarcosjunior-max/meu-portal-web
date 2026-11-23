import os
import re
import sqlite3
from functools import wraps
from flask import Flask, flash, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave-secreta-sefaz-al-2026")
SENHA_ADMIN = os.environ.get("SENHA_ADMIN", "admin123")
DB_PATH = "portal_dados.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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


DISCIPLINAS_EDITAL = [
    ("P1 – Básicos (60 itens)", "Matemática Financeira", "5", "8,3% de P1", False, False),
    ("", "Direito Constitucional", "5", "8,3% de P1", False, False),
    ("", "Direito Administrativo", "5", "8,3% de P1", False, False),
    ("", "Contabilidade Geral", "5", "8,3% de P1", False, False),
    ("", "Direito Tributário", "10", "16,7% de P1", False, False),
    ("", "Estatística e Probabilidade", "10", "16,7% de P1", False, False),
    ("", "Contabilidade Pública", "10", "16,7% de P1", False, False),
    ("", "Economia", "10", "16,7% de P1", False, False),
    ("P2 – Específicos (100 itens)", "Finanças Públicas", "10", "10% de P2", False, True),
    ("", "Legislação Tributária Estadual", "10", "10% de P2", False, False),
    ("", "Inteligência Artificial", "10", "10% de P2", True, False),
    ("", "Desenvolvimento de Sistemas", "10", "10% de P2", False, False),
    ("", "Infraestrutura de TIC e Segurança da Informação", "10", "10% de P2", False, False),
    ("", "Reforma Tributária", "15", "15% de P2", False, False),
    ("", "Auditoria Fiscal", "15", "15% de P2", False, False),
    ("", "Ciência de Dados", "20", "20% de P2 (Maior peso isolado)", True, False),
]

TOPICOS_CIENCIA_DADOS = [
    ("1. Fundamentos da Informação e Tipos de Dados", 0),
    ("1.1. Ciclo da informação: dado, informação, conhecimento e inteligência", 1),
    ("1.2. Tipologia de dados", 1),
    ("1.2.1. Dados estruturados e não estruturados", 2),
    ("1.2.2. Dados abertos", 2),
    ("2. Ciclo de Vida e Manipulação de Dados", 0),
    ("2.1. Coleta de dados", 1),
    ("2.2. Tratamento e limpeza de dados", 1),
    ("2.3. Armazenamento de dados", 1),
    ("2.4. Integração de dados", 1),
    ("2.5. Recuperação de dados", 1),
    ("3. Bancos de Dados e Modelagem", 0),
    ("3.1. Bancos de dados relacionais", 1),
    ("3.1.1. Conceitos e características", 2),
    ("3.1.2. Metadados, tabelas e visões (views)", 2),
    ("3.1.3. Índices, chaves e relacionamentos", 2),
    ("3.2. Modelagem de dados", 1),
    ("3.2.1. Modelagem relacional", 2),
    ("3.2.2. Modelagem dimensional e multidimensional", 2),
    ("3.3. Linguagem SQL e uso de planilhas", 1),
    ("4. Processo e Metodologia em Ciência de Dados", 0),
    ("4.1. Modelo de referência CRISP-DM", 1),
    ("4.2. Técnicas de pré-processamento e limpeza de dados", 1),
    ("5. Exploração e Visualização de Dados", 0),
    ("5.1. Análise exploratória de dados (EDA)", 1),
    ("5.2. Técnicas de visualização de dados", 1),
    ("6. Mineração de Dados (Data Mining)", 0),
    ("6.1. Classificação", 1),
    ("6.2. Regras de associação", 1),
    ("6.3. Regressão", 1),
    ("6.4. Análise de agrupamentos (clustering)", 1),
    ("6.5. Detecção de anomalias", 1),
    ("6.6. Modelagem preditiva", 1),
    ("7. Aprendizado de Máquina (Machine Learning)", 0),
    ("7.1. Fundamentos de aprendizado de máquina", 1),
    ("7.2. Principais algoritmos preditivos", 1),
    ("7.3. Métricas de desempenho e avaliação", 1),
    ("8. Big Data e Inteligência de Negócios", 0),
    ("8.1. Big Data: conceitos, premissas e aplicações", 1),
    ("8.2. Business Intelligence (BI): conceitos e ferramentas", 1),
]


def init_db():
    with get_db() as conn:
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS topicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                materia_slug TEXT NOT NULL,
                materia_nome TEXT NOT NULL,
                titulo TEXT NOT NULL,
                nivel INTEGER DEFAULT 0,
                ordem INTEGER DEFAULT 0,
                teoria_html TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS exercicios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topico_id INTEGER NOT NULL,
                banca_meta TEXT DEFAULT '',
                enunciado_html TEXT NOT NULL,
                gabarito TEXT DEFAULT '',
                bloco_a_html TEXT DEFAULT '',
                bloco_b_html TEXT DEFAULT '',
                bloco_c_html TEXT DEFAULT '',
                bloco_d_html TEXT DEFAULT '',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Garante migração segura caso a tabela exercicios já exista sem as colunas dos blocos A, B, C, D
        colunas_existentes = [row[1] for row in conn.execute("PRAGMA table_info(exercicios)").fetchall()]
        for col in ["bloco_a_html", "bloco_b_html", "bloco_c_html", "bloco_d_html"]:
            if col not in colunas_existentes:
                conn.execute(f"ALTER TABLE exercicios ADD COLUMN {col} TEXT DEFAULT ''")

        existe_info = conn.execute("SELECT 1 FROM info_concurso WHERE id = 1").fetchone()
        if not existe_info:
            conn.execute("""
                INSERT INTO info_concurso (id, orgao, cargos, banca_status, remuneracao, vagas_requisitos, aviso_geral)
                VALUES (1, ?, ?, ?, ?, ?, ?)
            """, (
                "Secretaria de Estado da Fazenda de Alagoas (SEFAZ-AL)",
                "Auditor Fiscal da Receita Estadual / Auditor de Finanças e Controle",
                "Prova Objetiva: 160 itens (P1: 60 itens | P2: 100 itens)",
                "A partir de R$ 9.500,00 + Produtividade / Gratificações",
                "Nível Superior em qualquer área de formação",
                "Clique em qualquer disciplina na tabela abaixo para abrir o edital verticalizado, resumos teóricos e exercícios comentados (Protocolo v1.6)."
            ))

        existe_cd = conn.execute("SELECT 1 FROM topicos WHERE materia_slug = 'ciencia-de-dados'").fetchone()
        if not existe_cd:
            for idx, (titulo, nivel) in enumerate(TOPICOS_CIENCIA_DADOS, start=1):
                conn.execute(
                    "INSERT INTO topicos (materia_slug, materia_nome, titulo, nivel, ordem) VALUES (?, ?, ?, ?, ?)",
                    ("ciencia-de-dados", "Ciência de Dados", titulo, nivel, idx)
                )


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
        .faixa-alagoas { height: 5px; background: linear-gradient(90deg, var(--al-vermelho) 33.3%, #ffffff 33.3%, #ffffff 66.6%, var(--al-azul) 66.6%); }
        
        header { background: linear-gradient(135deg, var(--al-azul-escuro), var(--al-azul)); color: white; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.12); }
        .brand { display: flex; flex-direction: column; }
        .brand a { color: white; text-decoration: none; font-weight: 800; font-size: 20px; letter-spacing: 0.3px; }
        .brand span { font-size: 12px; color: #cbd5e1; margin-top: 2px; }
        
        .nav-actions { display: flex; gap: 10px; align-items: center; }
        .btn { padding: 7px 13px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; transition: 0.15s; }
        .btn-primary { background: var(--al-azul); color: white; }
        .btn-primary:hover { background: var(--al-azul-escuro); }
        .btn-destaque { background: var(--al-vermelho); color: white; }
        .btn-destaque:hover { background: #a60d1e; }
        .btn-verde { background: #059669; color: white; }
        .btn-verde:hover { background: #047857; }
        .btn-outline { background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.35); color: white; }
        .btn-outline:hover { background: rgba(255,255,255,0.22); }
        .btn-danger { background: #dc2626; color: white; }
        .btn-copy { background: #e2e8f0; color: #1e293b; font-size: 12px; padding: 5px 10px; }
        .btn-copy:hover { background: #cbd5e1; }
        
        .container { max-width: 1120px; margin: 24px auto; padding: 0 20px; }
        .breadcrumb { font-size: 13px; color: #64748b; margin-bottom: 16px; }
        .breadcrumb a { color: var(--al-azul); text-decoration: none; font-weight: 600; }

        /* Painel Superior de Informações do Concurso */
        .painel-concurso { background: white; border-radius: 10px; border: 1px solid #cbd5e1; border-top: 4px solid var(--al-azul); padding: 22px 24px; margin-bottom: 22px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); }
        .painel-topo { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 16px; }
        .painel-topo h2 { margin: 0; font-size: 18px; color: var(--al-azul-escuro); display: flex; align-items: center; gap: 8px; }
        .tag-estado { background: var(--al-vermelho); color: white; font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: 700; }
        
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
        .info-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; }
        .info-label { font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--al-azul); letter-spacing: 0.4px; margin-bottom: 4px; }
        .info-valor { font-size: 13.5px; font-weight: 600; color: #1e293b; line-height: 1.4; }
        .aviso-concurso { margin-top: 14px; background: #eff6ff; border-left: 4px solid var(--al-azul); padding: 10px 14px; font-size: 13px; color: #1e3a8a; border-radius: 0 6px 6px 0; }

        /* Quadro de Peso e Distribuição das Disciplinas */
        .quadro-disciplinas { background: white; border-radius: 10px; border: 1px solid #cbd5e1; padding: 22px 24px; margin-bottom: 26px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); overflow-x: auto; }
        .quadro-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 10px; }
        .quadro-header h2 { margin: 0; font-size: 19px; color: #1e293b; font-weight: 600; }
        .tabela-edital { width: 100%; border-collapse: collapse; font-size: 14px; min-width: 600px; }
        .tabela-edital thead th { text-align: left; padding: 12px 10px; color: #475569; font-weight: 600; border-bottom: 1.5px solid #94a3b8; font-size: 13.5px; }
        .tabela-edital tbody td { padding: 12px 10px; border-bottom: 1px solid #e2e8f0; color: #1e293b; vertical-align: middle; }
        .tabela-edital tbody tr:hover { background-color: #f8fafc; }
        .tabela-edital tbody tr.destaque-materia td { font-weight: 700; color: #0f172a; }
        .tabela-edital tbody tr.divisor-p2 td { border-top: 1.5px solid #cbd5e1; }
        .link-disc { color: var(--al-azul); text-decoration: none; font-weight: 600; }
        .link-disc:hover { text-decoration: underline; color: var(--al-azul-escuro); }
        .pill-num { display: inline-flex; align-items: center; justify-content: center; background: #f1f5f9; color: #64748b; border-radius: 50%; width: 20px; height: 20px; font-size: 11px; font-weight: 600; margin-left: 6px; }

        /* Árvore Verticalizada de Tópicos */
        .box-materia { background: white; border-radius: 10px; border: 1px solid #cbd5e1; padding: 28px 32px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); }
        .materia-titulo { font-size: 28px; font-weight: 400; color: #1e293b; margin: 0 0 20px 0; padding-bottom: 12px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        .lista-edital { list-style: none; padding: 0; margin: 0; }
        .topico-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; border-bottom: 1px solid #f1f5f9; gap: 12px; flex-wrap: wrap; border-radius: 6px; }
        .topico-row:hover { background: #f8fafc; }
        .topico-texto { display: flex; align-items: center; gap: 10px; font-size: 15px; color: #1e293b; }
        .bullet-circulo { width: 6px; height: 6px; border: 1.5px solid #334155; border-radius: 50%; display: inline-block; flex-shrink: 0; }
        .nivel-0 { font-weight: 700; font-size: 15.5px; margin-top: 8px; }
        .nivel-1 { padding-left: 28px; }
        .nivel-2 { padding-left: 56px; font-size: 14.5px; }
        .topico-acoes { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
        .tag-ok { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
        .tag-vazio { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
        .tag-ex { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }

        /* Cartões de Exercícios e os 4 Blocos v1.6 */
        .exercicio-card { background: white; border: 1px solid #cbd5e1; border-left: 4px solid var(--al-azul); border-radius: 8px; padding: 20px 24px; margin-bottom: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.03); }
        .ex-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #f1f5f9; flex-wrap: wrap; gap: 8px; }
        .ex-badge { background: #dbeafe; color: var(--al-azul-escuro); font-weight: 700; font-size: 12px; padding: 3px 10px; border-radius: 4px; }
        .ex-resolucao { display: none; margin-top: 18px; padding-top: 16px; border-top: 2px dashed #cbd5e1; }
        
        .bloco-card { border-radius: 8px; padding: 16px 20px; margin-bottom: 14px; border: 1px solid #e2e8f0; }
        .bloco-titulo { font-weight: 700; font-size: 13.5px; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid rgba(0,0,0,0.08); display: flex; justify-content: space-between; align-items: center; }
        .bloco-a { background: #eff6ff; border-left: 4px solid #2563eb; }
        .bloco-a .bloco-titulo { color: #1e40af; }
        .bloco-b { background: #f0fdf4; border-left: 4px solid #059669; }
        .bloco-b .bloco-titulo { color: #166534; }
        .bloco-c { background: #fefce8; border-left: 4px solid #ca8a04; }
        .bloco-c .bloco-titulo { color: #854d0e; }
        .bloco-d { background: #f8fafc; border-left: 4px solid #475569; }
        .bloco-d .bloco-titulo { color: #1e293b; }

        .secao-form-bloco { border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; margin-top: 16px; background: #f8fafc; }
        .secao-form-bloco label { margin-top: 0; font-size: 14px; color: #002d62; }

        .box-form { background: white; padding: 28px; border-radius: 10px; border: 1px solid #e2e8f0; max-width: 920px; margin: 0 auto; }
        label { display: block; font-weight: 600; margin-top: 14px; margin-bottom: 6px; font-size: 13px; }
        input[type="text"], input[type="password"], select, textarea { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; box-sizing: border-box; font-family: inherit; background: white; }
        
        .editor-box { height: 200px; font-size: 14.5px; font-family: 'Segoe UI', Arial, sans-serif; background: white; }
        .ql-toolbar.ql-snow { border-top-left-radius: 6px; border-top-right-radius: 6px; background: #f1f5f9; border-color: #cbd5e1; }
        .ql-container.ql-snow { border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; border-color: #cbd5e1; background: white; }

        .conteudo-leitura { background: white; padding: 36px 44px; border-radius: 10px; border: 1px solid #e2e8f0; line-height: 1.65; font-size: 16px; overflow-x: auto; }
        .conteudo-leitura p, .bloco-card p { margin: 0 0 10px 0; }
        .conteudo-leitura table, .bloco-card table { border-collapse: collapse; width: 100%; margin: 12px 0; background: white; }
        .conteudo-leitura table td, .conteudo-leitura table th, .bloco-card table td, .bloco-card table th { border: 1px solid #cbd5e1; padding: 8px 12px; }
        .alerta { background: #fef3c7; color: #92400e; padding: 10px 14px; border-radius: 6px; margin-bottom: 16px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="faixa-alagoas"></div>
    <header>
        <div class="brand">
            <a href="/">🏛️ Central de Estudos • SEFAZ-AL</a>
            <span>Edital Verticalizado, Teoria & Exercícios Comentados (Protocolo v1.6)</span>
        </div>
        <div class="nav-actions">
            <a href="/" class="btn btn-outline">Início</a>
            {% if session.get('logado') %}
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

        function alternarResolucao(id) {
            const box = document.getElementById('res-' + id);
            box.style.display = (box.style.display === 'block') ? 'none' : 'block';
        }

        const editores = [];
        document.querySelectorAll('.quill-target').forEach(function(el) {
            const inputId = el.getAttribute('data-input');
            const quill = new Quill(el, {
                theme: 'snow',
                placeholder: 'Cole aqui o conteúdo formatado gerado pela IA / Word / Docs (Ctrl + V)...',
                modules: {
                    toolbar: [
                        [{ 'header': [1, 2, 3, false] }],
                        ['bold', 'italic', 'underline', 'strike'],
                        [{ 'color': [] }, { 'background': [] }],
                        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                        ['blockquote', 'code-block', 'link'],
                        ['clean']
                    ]
                }
            });
            editores.push({ quill: quill, inputId: inputId });
        });

        if (editores.length > 0) {
            const form = document.querySelector('form.form-quill');
            if (form) {
                form.addEventListener('submit', function() {
                    editores.forEach(function(item) {
                        document.getElementById(item.inputId).value = item.quill.root.innerHTML;
                    });
                });
            }
        }
    </script>
</body>
</html>
"""


def renderizar_blocos_v16(ex):
    """Renderiza visualmente os 4 blocos do Protocolo v1.6 de um exercício."""
    gab_banner = ""
    if ex["gabarito"]:
        gab_banner = f'<div style="background:#166534; color:white; padding:8px 14px; border-radius:6px; font-weight:700; margin-bottom:14px; display:inline-block;">✅ Gabarito Oficial: {ex["gabarito"]}</div>'

    blocos = [
        ("bloco-a", "Bloco A — Catalogação e Rede de Interdependência no Edital", ex["bloco_a_html"]),
        ("bloco-b", "Bloco B — Dissecação Profunda e Raciocínio (Padrão v1.6)", ex["bloco_b_html"]),
        ("bloco-c", "Bloco C — Caderno Teórico Acumulado Sob Demanda (Sem Repetição — Padrão v1.6)", ex["bloco_c_html"]),
        ("bloco-d", "Bloco D — Status e Evolução do Script Mestre (Protocolo v1.6)", ex["bloco_d_html"]),
    ]

    html_blocos = gab_banner
    for classe, titulo, conteudo in blocos:
        limpo = re.sub(r"<[^>]+>", "", conteudo or "").strip()
        if limpo:
            html_blocos += f"""
            <div class="bloco-card {classe}">
                <div class="bloco-titulo">{titulo}</div>
                <div style="line-height:1.6;">{conteudo}</div>
            </div>
            """
    return html_blocos


@app.route("/")
def index():
    init_db()
    with get_db() as conn:
        info = conn.execute("SELECT * FROM info_concurso WHERE id = 1").fetchone()
        contagens = dict(conn.execute(
            "SELECT materia_slug, COUNT(*) FROM topicos GROUP BY materia_slug"
        ).fetchall())

    btn_editar_painel = ""
    if session.get("logado"):
        btn_editar_painel = '<a href="/editar-painel" class="btn btn-primary">✏️ Editar Painel</a>'

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
                <div class="info-label">Estrutura / Banca</div>
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
            <strong>📌 Quadro de Avisos & Instruções:</strong> {info['aviso_geral']}
        </div>
    </div>
    """

    linhas_tabela = ""
    for prova, disciplina, qtd, part, destaque, divisor_p2 in DISCIPLINAS_EDITAL:
        classes = []
        if destaque:
            classes.append("destaque-materia")
        if divisor_p2:
            classes.append("divisor-p2")
        class_attr = ' class="' + " ".join(classes) + '"' if classes else ""

        prova_html = f"<strong>{prova}</strong>" if prova else ""
        slug_mat = gerar_slug(disciplina)
        qtd_topicos = contagens.get(slug_mat, 0)
        badge_topicos = f'<span class="pill-num" title="{qtd_topicos} tópicos cadastrados">{qtd_topicos}</span>' if qtd_topicos else ""

        linhas_tabela += f"""
        <tr{class_attr}>
            <td>{prova_html}</td>
            <td><a href="/materia/{slug_mat}" class="link-disc">{disciplina} →</a></td>
            <td>{qtd}</td>
            <td>{part} {badge_topicos}</td>
        </tr>
        """

    quadro_html = f"""
    <div class="quadro-disciplinas">
        <div class="quadro-header">
            <h2>Quadro de Peso e Distribuição das Disciplinas nas Provas Objetivas</h2>
            <span style="font-size:13px; color:#64748b;">Clique na disciplina para abrir o conteúdo programático</span>
        </div>
        <table class="tabela-edital">
            <thead>
                <tr>
                    <th style="width: 22%;">Prova</th>
                    <th style="width: 40%;">Disciplina</th>
                    <th style="width: 13%;">N.º de Itens</th>
                    <th style="width: 25%;">Participação na Prova Específica / Geral</th>
                </tr>
            </thead>
            <tbody>
                {linhas_tabela}
            </tbody>
        </table>
    </div>
    """

    return render_template_string(BASE_HTML, titulo_pagina="Início", corpo=painel_html + quadro_html)


@app.route("/materia/<slug>")
def ver_materia(slug):
    init_db()
    nome_materia = slug.replace("-", " ").title()
    for _, disc, _, _, _, _ in DISCIPLINAS_EDITAL:
        if gerar_slug(disc) == slug:
            nome_materia = disc
            break

    with get_db() as conn:
        topicos = conn.execute(
            "SELECT * FROM topicos WHERE materia_slug = ? ORDER BY ordem ASC, id ASC",
            (slug,)
        ).fetchall()
        contagem_ex = dict(conn.execute(
            "SELECT topico_id, COUNT(*) FROM exercicios GROUP BY topico_id"
        ).fetchall())

    itens_lista = ""
    for t in topicos:
        nivel_cls = f"nivel-{t['nivel']}"
        tem_teoria = bool(t["teoria_html"] and re.sub(r"<[^>]+>", "", t["teoria_html"]).strip())
        cls_teoria = "tag-ok" if tem_teoria else "tag-vazio"
        txt_teoria = "📘 Teoria ✓" if tem_teoria else "📘 + Teoria"

        qtd_ex = contagem_ex.get(t["id"], 0)
        txt_ex = f"✍️ Exercícios ({qtd_ex})"

        btn_del = ""
        if session.get("logado"):
            btn_del = f'<a href="/topico/{t["id"]}/excluir" class="btn btn-copy" style="color:#dc2626;" onclick="return confirm(\'Excluir este tópico?\');">✕</a>'

        itens_lista += f"""
        <li class="topico-row {nivel_cls}">
            <div class="topico-texto">
                <span class="bullet-circulo"></span>
                <span>{t['titulo']}</span>
            </div>
            <div class="topico-acoes">
                <a href="/topico/{t['id']}/teoria" class="btn {cls_teoria}">{txt_teoria}</a>
                <a href="/topico/{t['id']}/exercicios" class="btn tag-ex">{txt_ex}</a>
                {btn_del}
            </div>
        </li>
        """

    if not itens_lista:
        itens_lista = '<p style="color:#64748b;">Nenhum tópico do edital cadastrado ainda para esta disciplina.</p>'

    form_add_topico = ""
    if session.get("logado"):
        form_add_topico = f"""
        <div style="margin-top: 28px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
            <h3 style="margin-top:0; font-size:16px; color:#002d62;">+ Adicionar Tópicos do Edital em {nome_materia}</h3>
            <form method="POST" action="/materia/{slug}/adicionar-topicos">
                <input type="hidden" name="materia_nome" value="{nome_materia}">
                <label>Cole vários tópicos de uma vez (um por linha — a indentação 1., 1.1., 1.1.1. é detectada automaticamente):</label>
                <textarea name="lista_topicos" rows="6" placeholder="Ex:&#10;1. Conceitos Básicos&#10;1.1. Subtópico A&#10;1.1.1. Detalhe B" required></textarea>
                <button type="submit" class="btn btn-primary" style="margin-top:12px;">Salvar Tópicos na Matéria</button>
            </form>
        </div>
        """

    corpo = f"""
    <div class="breadcrumb"><a href="/">← Voltar ao Quadro Geral SEFAZ-AL</a> / {nome_materia}</div>
    <div class="box-materia">
        <div class="materia-titulo">
            <span>{nome_materia}</span>
            <button type="button" class="btn btn-copy" onclick="copiarLink(window.location.href)">Copiar Link da Matéria</button>
        </div>
        <ul class="lista-edital">
            {itens_lista}
        </ul>
        {form_add_topico}
    </div>
    """
    return render_template_string(BASE_HTML, titulo_pagina=nome_materia, corpo=corpo)


@app.route("/materia/<slug>/adicionar-topicos", methods=["POST"])
@admin_required
def adicionar_topicos(slug):
    materia_nome = request.form.get("materia_nome", slug).strip()
    linhas = request.form.get("lista_topicos", "").splitlines()

    with get_db() as conn:
        max_ordem = conn.execute(
            "SELECT COALESCE(MAX(ordem), 0) FROM topicos WHERE materia_slug = ?", (slug,)
        ).fetchone()[0]

        for linha in linhas:
            texto = linha.strip()
            if not texto:
                continue
            m = re.match(r"^(\d+(?:\.\d+)*)\.?\s+", texto)
            nivel = 0
            if m:
                pontos = m.group(1).count(".")
                nivel = min(pontos, 2)
            max_ordem += 1
            conn.execute(
                "INSERT INTO topicos (materia_slug, materia_nome, titulo, nivel, ordem) VALUES (?, ?, ?, ?, ?)",
                (slug, materia_nome, texto, nivel, max_ordem)
            )

    flash("Tópicos adicionados com sucesso!")
    return redirect(url_for("ver_materia", slug=slug))


@app.route("/topico/<int:topico_id>/excluir")
@admin_required
def excluir_topico(topico_id):
    with get_db() as conn:
        t = conn.execute("SELECT materia_slug FROM topicos WHERE id = ?", (topico_id,)).fetchone()
        if t:
            conn.execute("DELETE FROM exercicios WHERE topico_id = ?", (topico_id,))
            conn.execute("DELETE FROM topicos WHERE id = ?", (topico_id,))
            flash("Tópico excluído.")
            return redirect(url_for("ver_materia", slug=t["materia_slug"]))
    return redirect(url_for("index"))


@app.route("/topico/<int:topico_id>/teoria", methods=["GET", "POST"])
def ver_teoria(topico_id):
    init_db()
    with get_db() as conn:
        topico = conn.execute("SELECT * FROM topicos WHERE id = ?", (topico_id,)).fetchone()
        if not topico:
            return "Tópico não encontrado.", 404

        if request.method == "POST":
            if not session.get("logado"):
                return redirect(url_for("login"))
            teoria_html = request.form.get("teoria_html", "")
            conn.execute("UPDATE topicos SET teoria_html = ? WHERE id = ?", (teoria_html, topico_id))
            flash("Conteúdo teórico atualizado!")
            return redirect(url_for("ver_teoria", topico_id=topico_id))

    modo_editar = request.args.get("editar") == "1" and session.get("logado")
    tem_conteudo = bool(topico["teoria_html"] and re.sub(r"<[^>]+>", "", topico["teoria_html"]).strip())

    if modo_editar or (not tem_conteudo and session.get("logado")):
        bloco_principal = f"""
        <div class="box-form">
            <h2>Editar Conteúdo Teórico: {topico['titulo']}</h2>
            <form method="POST" class="form-quill">
                <div class="editor-box quill-target" data-input="teoria_html" style="height:360px;">{topico['teoria_html']}</div>
                <input type="hidden" name="teoria_html" id="teoria_html">
                <div style="margin-top:16px; display:flex; gap:10px;">
                    <button type="submit" class="btn btn-primary">Salvar Conteúdo Teórico</button>
                    <a href="/topico/{topico_id}/teoria" class="btn btn-copy">Cancelar</a>
                </div>
            </form>
        </div>
        """
    else:
        btn_edit = ""
        if session.get("logado"):
            btn_edit = f'<a href="/topico/{topico_id}/teoria?editar=1" class="btn btn-primary">✏️ Editar Teoria</a>'

        conteudo_exibir = topico["teoria_html"] if tem_conteudo else "<p style='color:#64748b;'>Nenhum resumo teórico cadastrado para este tópico ainda. Entre na Área de Edição para colar seu material do Word/Google Docs.</p>"
        bloco_principal = f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
            <h1 style="margin:0; font-size:22px; color:#002d62;">📘 {topico['titulo']}</h1>
            <div style="display:flex; gap:8px;">
                <a href="/topico/{topico_id}/exercicios" class="btn btn-verde">✍️ Ir para Exercícios deste Tópico</a>
                {btn_edit}
            </div>
        </div>
        <div class="conteudo-leitura">{conteudo_exibir}</div>
        """

    corpo = f"""
    <div class="breadcrumb">
        <a href="/">Início</a> / <a href="/materia/{topico['materia_slug']}">{topico['materia_nome']}</a> / Teoria
    </div>
    {bloco_principal}
    """
    return render_template_string(BASE_HTML, titulo_pagina=f"Teoria - {topico['titulo']}", corpo=corpo)


@app.route("/topico/<int:topico_id>/exercicios", methods=["GET", "POST"])
def ver_exercicios(topico_id):
    init_db()
    with get_db() as conn:
        topico = conn.execute("SELECT * FROM topicos WHERE id = ?", (topico_id,)).fetchone()
        if not topico:
            return "Tópico não encontrado.", 404

        if request.method == "POST":
            if not session.get("logado"):
                return redirect(url_for("login"))
            banca_meta = request.form.get("banca_meta", "").strip()
            gabarito = request.form.get("gabarito", "").strip()
            enunciado_html = request.form.get("enunciado_html", "").strip()
            bloco_a_html = request.form.get("bloco_a_html", "").strip()
            bloco_b_html = request.form.get("bloco_b_html", "").strip()
            bloco_c_html = request.form.get("bloco_c_html", "").strip()
            bloco_d_html = request.form.get("bloco_d_html", "").strip()

            conn.execute(
                """INSERT INTO exercicios
                   (topico_id, banca_meta, enunciado_html, gabarito, bloco_a_html, bloco_b_html, bloco_c_html, bloco_d_html)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (topico_id, banca_meta, enunciado_html, gabarito, bloco_a_html, bloco_b_html, bloco_c_html, bloco_d_html)
            )
            flash("Exercício e Blocos v1.6 adicionados ao tópico!")
            return redirect(url_for("ver_exercicios", topico_id=topico_id))

        exercicios = conn.execute(
            "SELECT * FROM exercicios WHERE topico_id = ? ORDER BY id ASC", (topico_id,)
        ).fetchall()

    lista_ex_html = ""
    for idx, ex in enumerate(exercicios, start=1):
        btn_edit_del = ""
        if session.get("logado"):
            btn_edit_del = f"""
                <a href="/exercicio/{ex['id']}/editar" class="btn btn-copy">✏️ Editar</a>
                <a href="/exercicio/{ex['id']}/excluir" class="btn btn-copy" style="color:#dc2626;" onclick="return confirm('Excluir este exercício?');">Excluir</a>
            """

        meta_txt = f" • {ex['banca_meta']}" if ex["banca_meta"] else ""
        blocos_renderizados = renderizar_blocos_v16(ex)

        lista_ex_html += f"""
        <div class="exercicio-card" id="ex-{ex['id']}">
            <div class="ex-header">
                <span class="ex-badge">Questão {idx:02d}{meta_txt}</span>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    <a href="/exercicio/{ex['id']}" class="btn btn-copy" title="Abrir página individual com link próprio">Abrir Link da Resolução ↗</a>
                    <button type="button" class="btn btn-verde" onclick="alternarResolucao({ex['id']})">👁️ Ver Resolução Comentada (Blocos A–D)</button>
                    {btn_edit_del}
                </div>
            </div>
            <div style="line-height:1.6;">{ex['enunciado_html']}</div>
            <div class="ex-resolucao" id="res-{ex['id']}">
                {blocos_renderizados}
            </div>
        </div>
        """

    if not lista_ex_html:
        lista_ex_html = "<p style='color:#64748b;'>Nenhum exercício cadastrado neste tópico ainda.</p>"

    form_novo_ex = ""
    if session.get("logado"):
        form_novo_ex = f"""
        <div class="box-form" style="margin-top:28px; max-width:100%;">
            <h3 style="margin-top:0; color:#002d62;">+ Adicionar Exercício Comentado ao Tópico (Protocolo v1.6)</h3>
            <form method="POST" class="form-quill">
                <div style="display:grid; grid-template-columns: 2fr 1fr; gap:12px;">
                    <div>
                        <label>Banca / Órgão / Ano (opcional):</label>
                        <input type="text" name="banca_meta" placeholder="Ex: Cebraspe - SEFAZ-AL">
                    </div>
                    <div>
                        <label>Gabarito Oficial:</label>
                        <input type="text" name="gabarito" placeholder="Ex: Certo ou Letra C">
                    </div>
                </div>

                <label>Enunciado e Alternativas da Questão:</label>
                <div class="editor-box quill-target" data-input="enunciado_html" style="height:170px;"></div>
                <input type="hidden" name="enunciado_html" id="enunciado_html">

                <div class="secao-form-bloco" style="border-left: 4px solid #2563eb;">
                    <label>Bloco A — Catalogação e Rede de Interdependência no Edital (Copiar e Colar no Portal):</label>
                    <div class="editor-box quill-target" data-input="bloco_a_html" style="height:160px;"></div>
                    <input type="hidden" name="bloco_a_html" id="bloco_a_html">
                </div>

                <div class="secao-form-bloco" style="border-left: 4px solid #059669;">
                    <label>Bloco B — Dissecação Profunda e Raciocínio (Copiar e Colar no Portal — Padrão v1.6):</label>
                    <div class="editor-box quill-target" data-input="bloco_b_html" style="height:220px;"></div>
                    <input type="hidden" name="bloco_b_html" id="bloco_b_html">
                </div>

                <div class="secao-form-bloco" style="border-left: 4px solid #ca8a04;">
                    <label>Bloco C — Caderno Teórico Acumulado Sob Demanda (Sem Repetição — Padrão v1.6):</label>
                    <div class="editor-box quill-target" data-input="bloco_c_html" style="height:200px;"></div>
                    <input type="hidden" name="bloco_c_html" id="bloco_c_html">
                </div>

                <div class="secao-form-bloco" style="border-left: 4px solid #475569;">
                    <label>Bloco D — Status e Evolução do Script Mestre (Protocolo v1.6):</label>
                    <div class="editor-box quill-target" data-input="bloco_d_html" style="height:150px;"></div>
                    <input type="hidden" name="bloco_d_html" id="bloco_d_html">
                </div>

                <button type="submit" class="btn btn-primary" style="margin-top:20px; padding:12px 20px; font-size:15px;">Salvar Exercício e Gerar Link de Resolução</button>
            </form>
        </div>
        """

    corpo = f"""
    <div class="breadcrumb">
        <a href="/">Início</a> / <a href="/materia/{topico['materia_slug']}">{topico['materia_nome']}</a> / Exercícios
    </div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; flex-wrap:wrap; gap:10px;">
        <h1 style="margin:0; font-size:21px; color:#002d62;">✍️ Exercícios: {topico['titulo']}</h1>
        <a href="/topico/{topico_id}/teoria" class="btn btn-primary">📘 Ver Teoria deste Tópico</a>
    </div>
    {lista_ex_html}
    {form_novo_ex}
    """
    return render_template_string(BASE_HTML, titulo_pagina=f"Exercícios - {topico['titulo']}", corpo=corpo)


@app.route("/exercicio/<int:ex_id>")
def ver_exercicio_individual(ex_id):
    init_db()
    with get_db() as conn:
        ex = conn.execute("SELECT * FROM exercicios WHERE id = ?", (ex_id,)).fetchone()
        if not ex:
            return "Exercício não encontrado.", 404
        topico = conn.execute("SELECT * FROM topicos WHERE id = ?", (ex["topico_id"],)).fetchone()

    btn_edit = ""
    if session.get("logado"):
        btn_edit = f'<a href="/exercicio/{ex["id"]}/editar" class="btn btn-primary">✏️ Editar Blocos</a>'

    blocos_renderizados = renderizar_blocos_v16(ex)

    corpo = f"""
    <div class="breadcrumb">
        <a href="/">Início</a> / <a href="/materia/{topico['materia_slug']}">{topico['materia_nome']}</a> / <a href="/topico/{topico['id']}/exercicios">{topico['titulo']}</a> / Questão #{ex['id']}
    </div>
    <div class="conteudo-leitura">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:8px;">
            <span class="ex-badge">{ex['banca_meta'] or 'Questão Comentada • Protocolo v1.6'}</span>
            <div style="display:flex; gap:8px;">
                <button type="button" class="btn btn-copy" onclick="copiarLink(window.location.href)">Copiar Link desta Questão</button>
                {btn_edit}
            </div>
        </div>
        <div style="margin-bottom:24px; padding-bottom:18px; border-bottom:2px solid #e2e8f0;">
            {ex['enunciado_html']}
        </div>
        {blocos_renderizados}
    </div>
    """
    return render_template_string(BASE_HTML, titulo_pagina=f"Questão #{ex['id']}", corpo=corpo)


@app.route("/exercicio/<int:ex_id>/editar", methods=["GET", "POST"])
@admin_required
def editar_exercicio(ex_id):
    init_db()
    with get_db() as conn:
        ex = conn.execute("SELECT * FROM exercicios WHERE id = ?", (ex_id,)).fetchone()
        if not ex:
            return "Exercício não encontrado.", 404
        topico = conn.execute("SELECT * FROM topicos WHERE id = ?", (ex["topico_id"],)).fetchone()

        if request.method == "POST":
            conn.execute("""
                UPDATE exercicios
                SET banca_meta = ?, gabarito = ?, enunciado_html = ?,
                    bloco_a_html = ?, bloco_b_html = ?, bloco_c_html = ?, bloco_d_html = ?
                WHERE id = ?
            """, (
                request.form.get("banca_meta", "").strip(),
                request.form.get("gabarito", "").strip(),
                request.form.get("enunciado_html", "").strip(),
                request.form.get("bloco_a_html", "").strip(),
                request.form.get("bloco_b_html", "").strip(),
                request.form.get("bloco_c_html", "").strip(),
                request.form.get("bloco_d_html", "").strip(),
                ex_id
            ))
            flash("Exercício e Blocos v1.6 atualizados!")
            return redirect(url_for("ver_exercicio_individual", ex_id=ex_id))

    corpo = f"""
    <div class="breadcrumb">
        <a href="/">Início</a> / <a href="/materia/{topico['materia_slug']}">{topico['materia_nome']}</a> / <a href="/topico/{topico['id']}/exercicios">Exercícios</a> / Editar Questão #{ex['id']}
    </div>
    <div class="box-form" style="max-width:100%;">
        <h2 style="margin-top:0; color:#002d62;">✏️ Editar Exercício & Blocos v1.6</h2>
        <form method="POST" class="form-quill">
            <div style="display:grid; grid-template-columns: 2fr 1fr; gap:12px;">
                <div>
                    <label>Banca / Órgão / Ano:</label>
                    <input type="text" name="banca_meta" value="{ex['banca_meta'] or ''}">
                </div>
                <div>
                    <label>Gabarito Oficial:</label>
                    <input type="text" name="gabarito" value="{ex['gabarito'] or ''}">
                </div>
            </div>

            <label>Enunciado e Alternativas:</label>
            <div class="editor-box quill-target" data-input="enunciado_html" style="height:170px;">{ex['enunciado_html']}</div>
            <input type="hidden" name="enunciado_html" id="enunciado_html">

            <div class="secao-form-bloco" style="border-left: 4px solid #2563eb;">
                <label>Bloco A — Catalogação e Rede de Interdependência no Edital:</label>
                <div class="editor-box quill-target" data-input="bloco_a_html" style="height:160px;">{ex['bloco_a_html'] or ''}</div>
                <input type="hidden" name="bloco_a_html" id="bloco_a_html">
            </div>

            <div class="secao-form-bloco" style="border-left: 4px solid #059669;">
                <label>Bloco B — Dissecação Profunda e Raciocínio (Padrão v1.6):</label>
                <div class="editor-box quill-target" data-input="bloco_b_html" style="height:220px;">{ex['bloco_b_html'] or ''}</div>
                <input type="hidden" name="bloco_b_html" id="bloco_b_html">
            </div>

            <div class="secao-form-bloco" style="border-left: 4px solid #ca8a04;">
                <label>Bloco C — Caderno Teórico Acumulado Sob Demanda (Padrão v1.6):</label>
                <div class="editor-box quill-target" data-input="bloco_c_html" style="height:200px;">{ex['bloco_c_html'] or ''}</div>
                <input type="hidden" name="bloco_c_html" id="bloco_c_html">
            </div>

            <div class="secao-form-bloco" style="border-left: 4px solid #475569;">
                <label>Bloco D — Status e Evolução do Script Mestre (Protocolo v1.6):</label>
                <div class="editor-box quill-target" data-input="bloco_d_html" style="height:150px;">{ex['bloco_d_html'] or ''}</div>
                <input type="hidden" name="bloco_d_html" id="bloco_d_html">
            </div>

            <div style="margin-top:20px; display:flex; gap:10px;">
                <button type="submit" class="btn btn-primary">Salvar Alterações</button>
                <a href="/exercicio/{ex['id']}" class="btn btn-copy">Cancelar</a>
            </div>
        </form>
    </div>
    """
    return render_template_string(BASE_HTML, titulo_pagina=f"Editar Questão #{ex['id']}", corpo=corpo)


@app.route("/exercicio/<int:ex_id>/excluir")
@admin_required
def excluir_exercicio(ex_id):
    with get_db() as conn:
        ex = conn.execute("SELECT topico_id FROM exercicios WHERE id = ?", (ex_id,)).fetchone()
        if ex:
            conn.execute("DELETE FROM exercicios WHERE id = ?", (ex_id,))
            flash("Exercício excluído.")
            return redirect(url_for("ver_exercicios", topico_id=ex["topico_id"]))
    return redirect(url_for("index"))


@app.route("/editar-painel", methods=["GET", "POST"])
@admin_required
def editar_painel():
    init_db()
    with get_db() as conn:
        if request.method == "POST":
            conn.execute("""
                UPDATE info_concurso
                SET orgao = ?, cargos = ?, banca_status = ?, remuneracao = ?, vagas_requisitos = ?, aviso_geral = ?
                WHERE id = 1
            """, (
                request.form.get("orgao", "").strip(),
                request.form.get("cargos", "").strip(),
                request.form.get("banca_status", "").strip(),
                request.form.get("remuneracao", "").strip(),
                request.form.get("vagas_requisitos", "").strip(),
                request.form.get("aviso_geral", "").strip()
            ))
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
            <label>Estrutura / Banca Organizadora:</label>
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
    return render_template_string(BASE_HTML, titulo_pagina="Editar Painel SEFAZ-AL", corpo=corpo)


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


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5005))
    print(f"\nPortal SEFAZ-AL iniciado! Acesse: http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
