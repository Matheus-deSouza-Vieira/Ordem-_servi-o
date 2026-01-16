import streamlit as st
import pandas as pd
from datetime import datetime
import os
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np
from sqlalchemy import create_engine, text
import streamlit.components.v1 as components
import socket

# --- HACK PARA FORÇAR IPV4 (CORREÇÃO DO ERRO DE CONEXÃO) ---
# Isso obriga o Streamlit a usar o "caminho velho" da internet que nunca falha
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfoIPv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfoIPv4

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Phone Parts System", layout="wide", page_icon="🍊")

# --- CONEXÃO COM A NUVEM (SUPABASE) ---
SUPABASE_URL = "postgresql://postgres:Floripa135001@db.rgkxplbvlermpfvvhxqq.supabase.co:6543/postgres"

@st.cache_resource
def get_db_connection():
    try:
        # Adicionei connect_timeout para ele não ficar esperando infinitamente
        engine = create_engine(SUPABASE_URL, connect_args={'connect_timeout': 10})
        return engine
    except Exception as e:
        st.error(f"Erro de Conexão com a Nuvem: {e}")
        return None

# --- FUNÇÕES DE BANCO DE DADOS BLINDADAS ---
def run_query(query, params=None):
    engine = get_db_connection()
    if engine is None: return pd.DataFrame() # Se não tem conexão, retorna vazio sem quebrar
    try:
        with engine.connect() as conn:
            if params:
                return pd.read_sql(text(query), conn, params=params)
            else:
                return pd.read_sql(text(query), conn)
    except Exception as e:
        st.error(f"Erro no SQL: {e}")
        return pd.DataFrame()

def run_action(query, params=None):
    engine = get_db_connection()
    if engine is None: return False
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params if params else {})
            return True
    except Exception as e:
        st.error(f"Erro de Gravação: {e}")
        return False

def get_empresa_info():
    df = run_query("SELECT * FROM empresa LIMIT 1")
    if not df.empty: return df.iloc[0]
    return {"nome": "Phone Parts", "cnpj": "000", "garantia": "Garantia"}

def get_sugestoes(campo):
    df = run_query(f"SELECT DISTINCT {campo} FROM ordens WHERE {campo} IS NOT NULL AND {campo} != '' ORDER BY {campo}")
    if not df.empty: return df[campo].tolist()
    return []

def clean_text(text):
    if text is None: return ""
    text = str(text)
    replacements = {'\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2022': '*', '\u2026': '...'}
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- CSS VISUAL ---
def local_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800&family=Roboto:wght@300;400&display=swap');
        .stApp { background-color: #050505; color: #e0e0e0; font-family: 'Roboto', sans-serif; }
        [data-testid="stSidebar"] { background-color: #080808; border-right: 2px solid #ff6600; }
        h1, h2, h3, .brand-text { font-family: 'Orbitron', sans-serif !important; color: #ff6600 !important; text-transform: uppercase; }
        .stTextInput > div > div > input, .stSelectbox > div > div > div, .stNumberInput > div > div > input, .stTextArea > div > div > textarea {
            background-color: #121212 !important; color: #ffffff !important; border: 1px solid #444 !important; border-radius: 4px; caret-color: #ff6600;
        }
        div.stButton > button[kind="primary"] { background: linear-gradient(90deg, #ff4500 0%, #ff8c00 100%); border: 1px solid #ffcc00; color: white; font-weight: 800; }
        div.stButton > button[kind="secondary"] { background-color: #ff0000; color: white; border: 1px solid #990000; }
    </style>""", unsafe_allow_html=True)

# --- REDE NEURAL (ANIMAÇÃO) ---
def get_neural_net_html():
    return """<!DOCTYPE html><html translate="no"><body><canvas id="neuralCanvas"></canvas><script>
    const canvas = document.getElementById('neuralCanvas'); const ctx = canvas.getContext('2d');
    let width, height, particles = []; const baseParticles = 15, connectionDist = 120, speedFactor = 0.8;
    function resize() { width = window.innerWidth; height = 200; canvas.width = width; canvas.height = height; }
    window.addEventListener('resize', resize); resize();
    class Particle { constructor(){ this.x = Math.random()*width; this.y = Math.random()*height; this.vx = (Math.random()-0.5)*speedFactor; this.vy = (Math.random()-0.5)*speedFactor; this.size = Math.random()*2+1; }
    update(){ this.x+=this.vx; this.y+=this.vy; if(this.x<0||this.x>width)this.vx*=-1; if(this.y<0||this.y>height)this.vy*=-1; }
    draw(){ ctx.beginPath(); ctx.arc(this.x, this.y, this.size, 0, Math.PI*2); ctx.fillStyle='rgba(255,102,0,0.8)'; ctx.fill(); } }
    function init(){ for(let i=0; i<baseParticles; i++) particles.push(new Particle()); }
    function animate(){ ctx.clearRect(0,0,width,height); particles.forEach((p, i) => { p.update(); p.draw(); particles.slice(i+1).forEach(p2 => { let d = Math.hypot(p.x-p2.x, p.y-p2.y); if(d<connectionDist){ ctx.beginPath(); ctx.strokeStyle=`rgba(255,102,0,${1-d/connectionDist})`; ctx.moveTo(p.x,p.y); ctx.lineTo(p2.x,p2.y); ctx.stroke(); }}); }); requestAnimationFrame(animate); }
    init(); animate(); </script></body></html>"""

# --- GERAÇÃO DE PDF ---
class PDF(FPDF):
    def dashed_line(self, x1, y1, x2, y2): self.line(x1, y1, x2, y2)

def gerar_pdf_split(os_data, cliente_data, empresa_data):
    pdf = PDF()
    pdf.set_auto_page_break(auto=False); pdf.add_page()
    pdf.set_y(10); pdf.set_font('Arial', 'B', 14)
    pdf.cell(130, 8, clean_text(f"{empresa_data['nome']} (VIA DA LOJA)"), 0, 0)
    pdf.cell(0, 8, f"OS N: {os_data['id']}", 0, 1, 'R')
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 5, clean_text(f"Cliente: {cliente_data['nome']} | Tel: {cliente_data['telefone']}"), 'B', 1)
    pdf.ln(3)
    pdf.cell(50, 6, clean_text(f"Tipo: {os_data['tipo_aparelho']}"), 1)
    pdf.cell(40, 6, clean_text(f"Marca: {os_data['marca']}"), 1)
    pdf.cell(50, 6, clean_text(f"Modelo: {os_data['modelo']}"), 1)
    pdf.cell(0, 6, clean_text(f"Cor: {os_data['cor']}"), 1, 1)
    pdf.cell(0, 6, clean_text(f"IMEI: {os_data['imei']} - Senha: {os_data['senha_device']}"), 1, 1)
    pdf.ln(2)
    pdf.multi_cell(0, 5, clean_text(f"Defeito: {os_data['defeito']}"), 1)
    pdf.multi_cell(0, 5, clean_text(f"Servico: {os_data['servico']}"), 1)
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 8, f"TOTAL: R$ {os_data['valor']:.2f}", 1, 1, 'R')
    pdf.dashed_line(5, 148.5, 205, 148.5); pdf.text(10, 146.5, "- - Corte Aqui - -")
    pdf.set_y(155); pdf.set_font('Arial', 'B', 14)
    pdf.cell(130, 8, clean_text(f"{empresa_data['nome']} (VIA CLIENTE)"), 0, 0)
    pdf.cell(0, 8, f"OS N: {os_data['id']}", 0, 1, 'R')
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 6, clean_text(f"Cliente: {cliente_data['nome']} | Aparelho: {os_data['marca']} {os_data['modelo']}"), 'B', 1)
    pdf.ln(3); pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 8, f"TOTAL: R$ {os_data['valor']:.2f}", 0, 1, 'R')
    pdf.ln(2); pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 5, clean_text(f"Servico: {os_data['servico']} ({os_data['defeito']})"), 1)
    pdf.ln(5); pdf.set_font('Arial', 'B', 8); pdf.cell(0, 5, "GARANTIA:", 0, 1)
    pdf.set_font('Arial', '', 7); pdf.multi_cell(0, 3.5, clean_text(empresa_data['garantia']))
    pdf.set_y(265); pdf.cell(0, 5, f"Data: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'C')
    pdf.cell(90, 5, "_"*40, 0, 0, 'C'); pdf.cell(90, 5, "_"*40, 0, 1, 'C')
    pdf.cell(90, 4, "Tecnico", 0, 0, 'C'); pdf.cell(90, 4, "Cliente", 0, 1, 'C')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

def render_campo_inteligente(label, sugestoes, key_suffix, valor_inicial=None):
    opcoes = ["Selecione..."] + sugestoes + ["➕ CADASTRAR NOVO..."]
    idx = 0
    if valor_inicial and valor_inicial not in sugestoes:
        opcoes.insert(1, valor_inicial); idx = 1
    elif valor_inicial and valor_inicial in sugestoes: idx = opcoes.index(valor_inicial)
    escolha = st.selectbox(label, opcoes, index=idx, key=f"sel_{key_suffix}")
    if escolha == "➕ CADASTRAR NOVO...": return st.text_input(f"Digite Novo {label}", key=f"txt_{key_suffix}")
    return escolha if escolha != "Selecione..." else valor_inicial

# --- MAIN ---
def main():
    local_css()
    if "password_correct" not in st.session_state: st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.markdown('<h1 class="brand-text" translate="no">🔐 PHONE PARTS</h1>', unsafe_allow_html=True)
            if st.text_input("Senha", type="password") == "admin123":
                st.session_state["password_correct"] = True; st.rerun()
            if st.button("ACESSAR", type="primary", use_container_width=True): st.error("Erro")
        return

    with st.sidebar:
        st.markdown('<h1 class="brand-text" style="text-align:center;" translate="no">PHONE PARTS</h1>', unsafe_allow_html=True)
        nav = st.radio("Navegação", ["Nova OS", "Histórico / Editar", "Compra & Venda", "Configurações"])
        st.markdown("---")
        components.html(get_neural_net_html(), height=200, scrolling=False)

    # --- PÁGINA: NOVA OS ---
    if nav == "Nova OS":
        if 'step' not in st.session_state: st.session_state.step = 1
        st.title("🛠️ Nova OS")
        
        if st.session_state.step == 1:
            st.subheader("1. Cliente")
            busca = st.text_input("Buscar CPF/CNPJ")
            cli = None
            if busca:
                df = run_query(f"SELECT * FROM clientes WHERE doc='{busca}'")
                if not df.empty:
                    cli = df.iloc[0]
                    st.success(f"Encontrado: {cli['nome']}")
            with st.form("f1"):
                c1,c2 = st.columns(2)
                nome = c1.text_input("Nome", value=cli['nome'] if cli is not None else "")
                doc = c2.text_input("CPF/CNPJ", value=busca)
                tel = c1.text_input("Tel", value=cli['telefone'] if cli is not None else "")
                email = c2.text_input("Email", value=cli['email'] if cli is not None and cli['email'] else "")
                end = st.text_input("Endereço", value=cli['endereco'] if cli is not None else "")
                tipo = st.radio("Tipo", ["Física", "Jurídica"], horizontal=True)
                if st.form_submit_button("Avançar >>", type="primary"):
                    if not nome: st.warning("Nome obrigatório")
                    else:
                        if cli is not None:
                            run_action("UPDATE clientes SET nome=:n, telefone=:t, email=:e, endereco=:en, tipo_pessoa=:tp WHERE id=:id", {"n":nome, "t":tel, "e":email, "en":end, "tp":tipo, "id":int(cli['id'])})
                            st.session_state.cli_id = int(cli['id'])
                        else:
                            # ID Manual Clientes (Blindado contra falha de conexão)
                            try:
                                max_id_df = run_query("SELECT COALESCE(MAX(id), 0) + 1 as novo_id FROM clientes")
                                if max_id_df.empty or max_id_df.iloc[0]['novo_id'] is None:
                                    novo_id_cli = 1
                                else:
                                    novo_id_cli = int(max_id_df.iloc[0]['novo_id'])
                            except:
                                novo_id_cli = 1 # Se tudo falhar, tenta salvar como 1
                            
                            engine = get_db_connection()
                            if engine:
                                with engine.begin() as conn:
                                    conn.execute(text("INSERT INTO clientes (id, nome, doc, telefone, email, endereco, tipo_pessoa) VALUES (:id, :n, :d, :t, :e, :en, :tp)"), 
                                        {"id": novo_id_cli, "n":nome, "d":doc, "t":tel, "e":email, "en":end, "tp":tipo})
                                st.session_state.cli_id = novo_id_cli
                                st.session_state.cli_nome = nome
                                st.session_state.step = 2
                                st.rerun()
                            else:
                                st.error("Sem conexão para salvar cliente.")

        elif st.session_state.step == 2:
            if st.button("⬅️ Voltar"): st.session_state.step = 1; st.rerun()
            st.subheader(f"2. Aparelho ({st.session_state.get('cli_nome', 'Cliente')})")
            with st.container():
                c1, c2, c3 = st.columns(3)
                tp = render_campo_inteligente("Tipo", get_sugestoes('tipo_aparelho'), "tp")
                mc = render_campo_inteligente("Marca", get_sugestoes('marca'), "mc")
                md = render_campo_inteligente("Modelo", get_sugestoes('modelo'), "md")
                c4, c5, c6 = st.columns(3)
                cor = c4.text_input("Cor"); senha = c5.text_input("Senha"); imei = c6.text_input("IMEI")
                st.markdown("---")
                cd, ce = st.columns([1, 2])
                with cd: st.write("**Padrão:**"); cv = st_canvas(fill_color="rgba(255,102,0,0.3)", stroke_width=4, stroke_color="#000", background_color="#EEE", height=150, width=150, key="cv")
                with ce: est = st.text_area("Estado Chegada", height=150)
                st.markdown("---")
                c_d, c_s = st.columns(2)
                defeito = c_d.text_area("Defeito"); servico = c_s.text_area("Serviço")
                cp1, cp2, cp3 = st.columns(3)
                val = cp1.number_input("Valor", min_value=0.0, format="%.2f")
                met = cp2.selectbox("Pagamento", ["Pendente", "Pix", "Dinheiro", "Cartão de Crédito"])
                parc = "1x"
                if met == "Cartão de Crédito": parc = cp3.selectbox("Parcelas", [f"{i}x" for i in range(1, 25)])
                
                if st.button("✅ FINALIZAR", type="primary", use_container_width=True):
                    dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                    # ID Manual OS (Blindado)
                    try:
                        max_os_df = run_query("SELECT COALESCE(MAX(id), 0) + 1 as novo_id FROM ordens")
                        if max_os_df.empty or max_os_df.iloc[0]['novo_id'] is None:
                            novo_id_os = 1
                        else:
                            novo_id_os = int(max_os_df.iloc[0]['novo_id'])
                        
                        engine = get_db_connection()
                        if engine:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO ordens (id, cliente_id, tipo_aparelho, marca, modelo, cor, imei, senha_device, defeito, servico, valor, status, data_entrada, estado_chegada, pagamento_metodo, pagamento_parcelas) VALUES (:id, :cid, :tp, :mc, :md, :cor, :im, :sn, :df, :sv, :vl, :st, :dt, :est, :pm, :pp)"),
                                    {"id": novo_id_os, "cid":st.session_state.cli_id, "tp":tp, "mc":mc, "md":md, "cor":cor, "im":imei, "sn":senha, "df":defeito, "sv":servico, "vl":val, "st":"Aberta", "dt":dt, "est":est, "pm":met, "pp":parc})
                            
                            st.session_state.last_os = novo_id_os
                            st.session_state.step = 3
                            st.rerun()
                        else:
                            st.error("Sem conexão para salvar OS.")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

        elif st.session_state.step == 3:
            st.success("Sucesso na Nuvem!")
            oid = st.session_state.get('last_os')
            
            # PROTEÇÃO CONTRA O ERRO ID=NONE
            if not oid:
                st.error("Não foi possível recuperar a OS recém-criada.")
                if st.button("Voltar ao Início"): st.session_state.step = 1; st.rerun()
            else:
                try:
                    od = run_query(f"SELECT * FROM ordens WHERE id={oid}")
                    if not od.empty:
                        od = od.iloc[0]
                        cd = run_query(f"SELECT * FROM clientes WHERE id={od['cliente_id']}").iloc[0]
                        ed = get_empresa_info()
                        pdf_a4 = gerar_pdf_split(od, cd, ed)
                        st.download_button("📄 PDF A4", pdf_a4, f"OS_{oid}.pdf", "application/pdf")
                    else:
                        st.warning("Aguardando sincronização do banco...")
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")
                
            if st.button("Nova OS"): st.session_state.step = 1; st.rerun()

    # --- PÁGINA: HISTÓRICO / EDITAR ---
    elif nav == "Histórico / Editar":
        st.title("📂 Histórico e Edição")
        
        st.subheader("🔍 Pesquisar")
        busca_os = st.text_input("Buscar por Nome do Cliente ou Nº OS")
        query_base = "SELECT o.id, c.nome, o.modelo, o.status, o.valor, o.data_entrada FROM ordens o JOIN clientes c ON o.cliente_id = c.id"
        
        if busca_os:
            if busca_os.isdigit():
                df_os = run_query(f"{query_base} WHERE o.id = {busca_os}")
            else:
                df_os = run_query(f"{query_base} WHERE c.nome ILIKE '%{busca_os}%'")
        else:
            df_os = run_query(f"{query_base} ORDER BY o.id DESC LIMIT 20")
        st.dataframe(df_os, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        st.subheader("📝 Gerenciar OS (Editar ou Excluir)")
        col_sel, col_btn = st.columns([1, 2])
        id_editor = col_sel.number_input("Digite o ID da OS para gerenciar", min_value=1, step=1)
        
        if id_editor:
            dados_completos = run_query(f"""
                SELECT o.*, c.id as cid, c.nome, c.telefone, c.email 
                FROM ordens o 
                JOIN clientes c ON o.cliente_id = c.id 
                WHERE o.id = {id_editor}
            """)

            if not dados_completos.empty:
                item = dados_completos.iloc[0]
                
                with st.expander(f"⚙️ Editar Dados: OS #{id_editor} - {item['nome']}", expanded=True):
                    with st.form("edit_form"):
                        st.markdown("**Dados do Cliente**")
                        c1, c2 = st.columns(2)
                        new_nome = c1.text_input("Nome", item['nome'])
                        new_tel = c2.text_input("Telefone", item['telefone'])
                        
                        st.markdown("**Dados da Ordem**")
                        c3, c4, c5 = st.columns(3)
                        new_modelo = c3.text_input("Modelo", item['modelo'])
                        new_valor = c4.number_input("Valor (R$)", value=float(item['valor']), format="%.2f")
                        status_list = ["Aberta", "Em Análise", "Aguardando Peça", "Pronta", "Entregue", "Cancelada"]
                        idx_status = status_list.index(item['status']) if item['status'] in status_list else 0
                        new_status = c5.selectbox("Status", status_list, index=idx_status)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.form_submit_button("💾 SALVAR ALTERAÇÕES", type="primary", use_container_width=True):
                            run_action("UPDATE clientes SET nome=:n, telefone=:t WHERE id=:id", {"n":new_nome, "t":new_tel, "id":int(item['cid'])})
                            run_action("UPDATE ordens SET modelo=:m, valor=:v, status=:s WHERE id=:id", {"m":new_modelo, "v":new_valor, "s":new_status, "id":id_editor})
                            st.success("✅ Dados Atualizados com Sucesso!")
                            st.rerun()

                st.markdown("#### Zona de Perigo")
                c_del_1, c_del_2 = st.columns([3, 1])
                if c_del_2.button("🗑️ APAGAR ESTA OS", type="secondary", use_container_width=True):
                    run_action("DELETE FROM ordens WHERE id=:id", {"id":id_editor})
                    st.warning(f"OS {id_editor} apagada permanentemente.")
                    st.rerun()
            else:
                st.info("Nenhuma OS encontrada com esse ID.")

    # --- PÁGINA: COMPRA & VENDA ---
    elif nav == "Compra & Venda":
        st.title("💰 Gestão")
        st.info("Funcionalidade de Compra e Venda.")
        df_hist = run_query("SELECT t.id, t.tipo_operacao, c.nome, t.aparelho, t.valor, t.data_operacao FROM transacoes t JOIN clientes c ON t.cliente_id=c.id ORDER BY t.id DESC")
        st.dataframe(df_hist, use_container_width=True)

    # --- PÁGINA: CONFIGURAÇÕES ---
    elif nav == "Configurações":
        st.header("Configurações")
        e = get_empresa_info()
        with st.form("c"):
            n = st.text_input("Nome", e['nome']); c = st.text_input("CNPJ", e['cnpj']); g = st.text_area("Garantia", e['garantia'])
            if st.form_submit_button("Salvar"):
                run_action("UPDATE empresa SET nome=:n, cnpj=:c, garantia=:g WHERE id=1", {"n":n, "c":c, "g":g})
                st.rerun()

if __name__ == "__main__":
    main()
