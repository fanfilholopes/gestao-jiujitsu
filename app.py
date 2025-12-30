import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
import time
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="SER Jiu-Jítsu - Sistema Integrado", 
    page_icon="🥋", 
    layout="wide"
)

# --- GERENCIAMENTO DE ESTADO ---
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 'login'
if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- CONEXÃO COM O BANCO DE DADOS ---
def get_connection():
    try:
        if "url" in st.secrets["postgres"]:
            conn = psycopg2.connect(st.secrets["postgres"]["url"])
        else:
            conn = psycopg2.connect(
                host=st.secrets["postgres"]["host"],
                database=st.secrets["postgres"]["database"],
                user=st.secrets["postgres"]["user"],
                password=st.secrets["postgres"]["password"],
                port=st.secrets["postgres"]["port"]
            )
        return conn
    except Exception as e:
        st.error(f"Erro detalhado de conexão: {e}")
        return None

# --- FUNÇÃO PARA EXECUTAR COMANDOS (CORRIGIDA) ---
def executar_query(query, params=None, fetch=False):
    conn = get_connection()
    if conn is None:
        return [] if fetch else False
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(query, params)
        
        if fetch:
            resultado = cur.fetchall()
            if "INSERT" in query.upper() or "UPDATE" in query.upper():
                conn.commit()
        else:
            conn.commit()
            resultado = True
            
        cur.close()
        conn.close()
        return resultado
    except Exception as e:
        st.error(f"Erro no banco: {e}")
        return [] if fetch else False

# --- FUNÇÃO CACHEADA PARA DASHBOARD ---
@st.cache_data(ttl=60)
def carregar_dados_dashboard():
    hoje = date.today()
    try:
        # Total Alunos
        res_total = executar_query("SELECT COUNT(*) FROM alunos WHERE status_aluno = 'Ativo';", fetch=True)
        total_alunos = res_total[0][0] if res_total else 0
        
        # Aniversariantes
        niver_mes = executar_query("SELECT nome, EXTRACT(DAY FROM data_nascimento) as dia FROM alunos WHERE EXTRACT(MONTH FROM data_nascimento) = %s ORDER BY dia;", (hoje.month,), fetch=True)
        
        # Dados Gráfico Faixas
        dados_faixa = executar_query("SELECT faixa, COUNT(*) as total FROM alunos WHERE status_aluno = 'Ativo' GROUP BY faixa;", fetch=True)
        
        # Dados Gráfico Frequência
        data_limite = hoje - timedelta(days=7)
        dados_freq = executar_query("""
            SELECT data_aula, COUNT(*) as total 
            FROM presencas 
            WHERE data_aula >= %s 
            GROUP BY data_aula 
            ORDER BY data_aula
        """, (data_limite,), fetch=True)

        return total_alunos, niver_mes, dados_faixa, dados_freq
    except:
        return 0, [], [], []

# --- HELPER: CALCULAR IDADE ---
def calcular_idade(nascimento):
    if not nascimento: return 0
    hoje = date.today()
    return hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))

# --- FUNÇÃO PARA EXIBIR LOGO ---
def mostrar_logo():
    if os.path.exists("logoser.jpg"):
        st.image("logoser.jpg", width=200)
    elif os.path.exists("logo.png"):
        st.image("logo.png", width=200)

# ==========================================
# TELA 1: LOGIN (LAYOUT HORIZONTAL)
# ==========================================
def tela_login():
    st.markdown("""
        <style>
        .block-container {
            padding-top: 3rem;
            padding-bottom: 2rem;
        }
        [data-testid="stImage"] {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
        }
        [data-testid="stImage"] > img {
            max-width: 100%;
            height: auto;
            object-fit: contain;
        }
        .title-container {
            display: flex;
            flex-direction: column;
            justify-content: center;
            height: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 3, 1])
    
    with c2:
        col_img_header, col_text_header = st.columns([1, 3])
        with col_img_header:
            mostrar_logo()
        with col_text_header:
            st.markdown("""
                <div class="title-container">
                    <h1 style='text-align: left; margin-bottom: 0;'>🥋 SER Jiu-Jítsu</h1>
                    <p style='text-align: left; color: grey; margin-top: -5px;'>Sistema de Alta Performance</p>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        tab_prof, tab_aluno = st.tabs(["🔐 Acesso Professor", "🥋 Área do Aluno"])
        
        with tab_prof:
            st.write("") 
            with st.form("form_login"):
                st.markdown("##### Credenciais Administrativas")
                user = st.text_input("Usuário", placeholder="Digite seu usuário")
                password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
                st.markdown("") 
                entrar = st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True)
                
                if entrar:
                    try:
                        if user == st.secrets["admin"]["usuario"] and password == st.secrets["admin"]["senha"]:
                            st.session_state.logado = True
                            st.session_state.pagina_atual = 'sistema'
                            st.rerun()
                        else:
                            st.toast("🚫 Usuário ou senha incorretos.", icon="❌")
                    except KeyError:
                        st.error("Erro: Configure [admin] nos Secrets.")

        with tab_aluno:
            st.write("")
            st.info("Ainda não tem cadastro? Registre-se agora para acompanhar sua graduação e presença.")
            if st.button("📝 Fazer Auto-Cadastro", use_container_width=True):
                st.session_state.pagina_atual = 'cadastro_aluno'
                st.rerun()
            st.markdown("---")
            st.caption("Dúvidas? Procure seu professor no tatame.")

# ==========================================
# TELA 2: AUTO-CADASTRO
# ==========================================
def tela_cadastro_aluno():
    st.button("⬅️ Voltar para Login", on_click=lambda: st.session_state.update({'pagina_atual': 'login'}))
    col_logo1, col_logo2 = st.columns([1, 5])
    with col_logo1: mostrar_logo()
    with col_logo2:
        st.title("Portal do Atleta")
        st.markdown("Bem-vindo à equipe! Preencha sua ficha.")
    
    with st.form("form_auto_cadastro", clear_on_submit=True):
        st.markdown("### 1. Dados Pessoais")
        col1, col2 = st.columns(2)
        nome_auto = col1.text_input("Nome Completo *")
        nasc_auto = col1.date_input("Data de Nascimento", value=date(2000, 1, 1), min_value=date(1920, 1, 1), max_value=date.today(), format="DD/MM/YYYY")
        col_tel, col_resp = st.columns(2)
        tel_auto = col_tel.text_input("WhatsApp (com DDD) *")
        resp_auto = col_resp.text_input("Nome do Responsável (se menor de idade)")
        
        st.divider()
        st.markdown("### 2. Graduação Atual")
        c_faixa, c_graus = st.columns(2)
        faixa_auto = c_faixa.selectbox("Qual sua Faixa?", ["Branca", "Cinza/Branca", "Cinza", "Cinza/Preta", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])
        graus_auto = c_graus.number_input("Quantos Graus na faixa?", 0, 10, 0, step=1)
        c_dt_faixa, c_dt_grau = st.columns(2)
        data_faixa_auto = c_dt_faixa.date_input("Quando pegou essa FAIXA?", value=date.today(), format="DD/MM/YYYY")
        data_grau_auto = c_dt_grau.date_input("Quando pegou o último GRAU? (Se tiver)", value=date.today(), format="DD/MM/YYYY")

        st.divider()
        st.markdown("### 3. Treinos")
        t_auto_db = executar_query("SELECT id, nome_turma FROM turmas;", fetch=True)
        op_t_auto = {t['nome_turma']: t['id'] for t in t_auto_db} if t_auto_db else {}
        turma_auto = st.selectbox("Turma/Horário que irá treinar", list(op_t_auto.keys()) if op_t_auto else ["Nenhuma disponível"])
        
        submitted = st.form_submit_button("✅ Enviar Cadastro", use_container_width=True)
        
        if submitted:
            if nome_auto and tel_auto and turma_auto != "Nenhuma disponível":
                existe = executar_query("SELECT id FROM alunos WHERE nome = %s AND telefone = %s", (nome_auto, tel_auto), fetch=True)
                if existe:
                    st.toast("⚠️ Já existe um aluno com esse Nome e Telefone!", icon="⚠️")
                else:
                    id_t_auto = op_t_auto.get(turma_auto)
                    dt_grau_final = data_grau_auto if graus_auto > 0 else data_faixa_auto
                    q_auto = """INSERT INTO alunos (nome, data_nascimento, faixa, graus, id_turma, nome_responsavel, telefone, status_aluno, data_faixa, data_ultimo_grau) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Ativo', %s, %s) RETURNING id"""
                    novo_id = executar_query(q_auto, (nome_auto, nasc_auto, faixa_auto, graus_auto, id_t_auto, resp_auto, tel_auto, data_faixa_auto, dt_grau_final), fetch=True)[0][0]
                    executar_query("""INSERT INTO historico_graduacao (id_aluno, faixa_nova, graus_nova, data_mudanca, motivo) 
                                      VALUES (%s, %s, %s, %s, 'Cadastro Inicial')""", (novo_id, faixa_auto, graus_auto, dt_grau_final))
                    st.balloons()
                    st.toast(f"Cadastro de {nome_auto} realizado!", icon="✅")
                    time.sleep(3)
                    st.session_state.pagina_atual = 'login'
                    st.rerun()
            else:
                st.toast("Preencha Nome, Telefone e Turma.", icon="🚨")

# ==========================================
# TELA 3: SISTEMA PRINCIPAL
# ==========================================
def sistema_principal():
    with st.sidebar:
        mostrar_logo()
        st.divider()
        st.header("Painel Admin")
        st.write(f"Logado como: **{st.secrets['admin']['usuario'].upper()}**")
        if st.button("🚪 Sair (Logout)", type="primary"):
            st.session_state.logado = False
            st.session_state.pagina_atual = 'login'
            st.rerun()
    
    st.title("🥋 Painel Administrativo")
    
    tab_dash, tab_gestao, tab_chamada, tab_regras = st.tabs([
        "📊 Dashboard", "👥 Gestão Alunos", "📅 Chamada", "⚙️ Configurações"
    ])

    # --- ABA 1: DASHBOARD ---
    with tab_dash:
        st.header("Visão Geral")
        total_alunos, niver_mes, dados_f, dados_freq = carregar_dados_dashboard()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Alunos Ativos", total_alunos)
        
        hoje = date.today()
        aniversariantes_hoje = [n for n in niver_mes if n['dia'] == hoje.day]
        c2.metric("Aniversariantes Hoje", len(aniversariantes_hoje))
        if aniversariantes_hoje: c2.success(f"🎉 {', '.join([n['nome'] for n in aniversariantes_hoje])}")
        
        # Frequência Média (Total últimos 7 dias)
        total_treinos_7dias = sum([d['total'] for d in dados_freq]) if dados_freq else 0
        c3.metric("Treinos na Semana", total_treinos_7dias)

        st.divider()

        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.subheader("🥋 Distribuição por Faixa")
            if dados_f:
                df_faixas = pd.DataFrame(dados_f, columns=['faixa', 'total'])
                fig_donut = px.pie(df_faixas, values='total', names='faixa', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
                fig_donut.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_donut, use_container_width=True)
            else: st.info("Sem dados de faixas.")
        with col_graf2:
            st.subheader("📈 Frequência de Treinos")
            if dados_freq:
                df_freq = pd.DataFrame(dados_freq, columns=['data', 'total'])
                fig_area = px.area(df_freq, x='data', y='total', markers=True, color_discrete_sequence=['#FF4B4B'])
                st.plotly_chart(fig_area, use_container_width=True)
            else: st.info("Sem treinos nos últimos 7 dias.")
        st.divider()
        
        # === ANÁLISE INTELIGENTE DE GRADUAÇÃO ===
        st.subheader("🎓 Sugestões de Graduação")
        if st.button("🔄 Atualizar Análise Agora"):
            st.cache_data.clear()
            st.rerun()
            
        alunos_db = executar_query("SELECT id, nome, data_nascimento, faixa, graus, data_faixa, data_ultimo_grau FROM alunos WHERE status_aluno = 'Ativo'", fetch=True)
        lista_grau = []
        lista_faixa = []
        
        if alunos_db:
            for alu in alunos_db:
                idade = calcular_idade(alu['data_nascimento'])
                dt_grau = alu['data_ultimo_grau'] or hoje
                dt_faixa = alu['data_faixa'] or hoje
                aulas_no_grau = executar_query("SELECT COUNT(*) FROM presencas WHERE id_aluno = %s AND data_aula >= %s", (alu['id'], dt_grau), fetch=True)[0][0]
                meses_no_grau = (hoje - dt_grau).days // 30
                meses_na_faixa = (hoje - dt_faixa).days // 30
                
                # --- LÓGICA KIDS ---
                if idade < 16:
                    if aulas_no_grau >= 8:
                        lista_grau.append({"Nome": alu['nome'], "Faixa": alu['faixa'], "Aulas": aulas_no_grau, "Motivo": "8+ Aulas"})
                    if meses_na_faixa >= 6:
                        lista_faixa.append({"Nome": alu['nome'], "Faixa Atual": alu['faixa'], "Tempo": f"{meses_na_faixa} meses"})
                # --- LÓGICA ADULTOS ---
                else:
                    tempo_grau_ok = False
                    if alu['faixa'] == 'Branca':
                        if meses_no_grau >= 3: tempo_grau_ok = True
                    elif alu['faixa'] == 'Preta':
                        if meses_no_grau >= 36: tempo_grau_ok = True 
                    else: 
                        if meses_no_grau >= 6: tempo_grau_ok = True
                    
                    if tempo_grau_ok and alu['graus'] < 4:
                        lista_grau.append({"Nome": alu['nome'], "Faixa": alu['faixa'], "Tempo Grau": f"{meses_no_grau} meses", "Motivo": "Tempo Mínimo"})

                    if alu['graus'] == 4:
                        tempo_faixa_ok = False
                        if alu['faixa'] == 'Branca': tempo_faixa_ok = True 
                        elif alu['faixa'] == 'Azul' and meses_na_faixa >= 24: tempo_faixa_ok = True
                        elif alu['faixa'] == 'Roxa' and meses_na_faixa >= 18: tempo_faixa_ok = True
                        elif alu['faixa'] == 'Marrom' and meses_na_faixa >= 12: tempo_faixa_ok = True
                        
                        if tempo_faixa_ok:
                            lista_faixa.append({"Nome": alu['nome'], "Faixa Atual": alu['faixa'], "Tempo": f"{meses_na_faixa} meses"})

        c_alert1, c_alert2 = st.columns(2)
        with c_alert1:
            if lista_grau:
                st.info(f"🆙 Aptos para Grau ({len(lista_grau)})")
                st.dataframe(pd.DataFrame(lista_grau), use_container_width=True, hide_index=True)
            else: st.success("Nenhum grau pendente.")
        with c_alert2:
            if lista_faixa:
                st.warning(f"🥋 Aptos para Faixa Nova ({len(lista_faixa)})")
                st.dataframe(pd.DataFrame(lista_faixa), use_container_width=True, hide_index=True)
            else: st.success("Nenhuma troca de faixa pendente.")

    # --- ABA 2: GESTÃO DE ALUNOS ---
    with tab_gestao:
        st.header("Gerenciamento Administrativo")
        op_g = st.radio("Ação:", ["Listar e Editar", "Cadastrar Novo (Manual)"], horizontal=True)
        if op_g == "Cadastrar Novo (Manual)":
            with st.form("cad_novo_admin"):
                c1, c2 = st.columns(2)
                nome = c1.text_input("Nome Completo")
                nasc = c1.date_input("Nascimento", value=date(2010, 1, 1), format="DD/MM/YYYY")
                faixa = c1.selectbox("Faixa", ["Branca", "Cinza/Branca", "Cinza", "Cinza/Preta", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])
                graus = c2.number_input("Graus", 0, 10, 0)
                d_faixa = c2.date_input("Data da Faixa Atual", format="DD/MM/YYYY")
                d_grau = c2.date_input("Data do Último Grau", format="DD/MM/YYYY")
                t_db = executar_query("SELECT id, nome_turma FROM turmas;", fetch=True)
                op_t = {t['nome_turma']: t['id'] for t in t_db} if t_db else {}
                turma = st.selectbox("Turma", list(op_t.keys()) if op_t else ["Nenhuma"])
                resp = st.text_input("Responsável")
                tel = st.text_input("Telefone")
                if st.form_submit_button("Salvar Atleta"):
                    id_t = op_t.get(turma)
                    q = """INSERT INTO alunos (nome, data_nascimento, faixa, graus, data_faixa, data_ultimo_grau, id_turma, nome_responsavel, telefone, status_aluno) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Ativo') RETURNING id"""
                    novo_id = executar_query(q, (nome, nasc, faixa, graus, d_faixa, d_grau, id_t, resp, tel), fetch=True)[0][0]
                    executar_query("""INSERT INTO historico_graduacao (id_aluno, faixa_nova, graus_nova, data_mudanca, motivo) 
                                      VALUES (%s, %s, %s, %s, 'Cadastro Manual')""", (novo_id, faixa, graus, d_grau))
                    st.cache_data.clear()
                    st.toast("Cadastrado com sucesso!", icon="✅")
                    st.rerun()
        else:
            col_busca, col_filtro = st.columns([2, 1])
            busca_nome = col_busca.text_input("🔍 Buscar por Nome:")
            filtro_faixa = col_filtro.multiselect("Filtrar por Faixa:", ["Branca", "Cinza/Branca", "Cinza", "Cinza/Preta", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])
            
            dados = executar_query("SELECT id, nome, data_nascimento, faixa, graus, data_faixa, data_ultimo_grau, nome_responsavel, telefone FROM alunos ORDER BY nome", fetch=True)
            
            if dados:
                df_e = pd.DataFrame(dados, columns=['ID', 'Nome', 'Nascimento', 'Faixa', 'Graus', 'Data Faixa', 'Data Último Grau', 'Responsável', 'Telefone'])
                if busca_nome: df_e = df_e[df_e['Nome'].str.contains(busca_nome, case=False, na=False)]
                if filtro_faixa: df_e = df_e[df_e['Faixa'].isin(filtro_faixa)]
                
                st.data_editor(df_e, use_container_width=True, hide_index=True, key="editor_alunos", disabled=("ID",), column_config={"Nascimento": st.column_config.DateColumn("Nascimento", format="DD/MM/YYYY"), "Data Faixa": st.column_config.DateColumn("Data Faixa", format="DD/MM/YYYY"), "Data Último Grau": st.column_config.DateColumn("Data Último Grau", format="DD/MM/YYYY")})
                
                if st.button("💾 Salvar Alterações da Tabela", type="primary", use_container_width=True):
                    for _, r in df_up.iterrows():
                        q_up = """UPDATE alunos SET nome=%s, data_nascimento=%s, faixa=%s, graus=%s, data_faixa=%s, data_ultimo_grau=%s, nome_responsavel=%s, telefone=%s WHERE id=%s"""
                        executar_query(q_up, (r['Nome'], r['Nascimento'], r['Faixa'], r['Graus'], r['Data Faixa'], r['Data Último Grau'], r['Responsável'], r['Telefone'], r['ID']))
                    st.cache_data.clear()
                    st.toast("Tabela atualizada!", icon="💾")
                    time.sleep(1)
                    st.rerun()
                
                st.divider()
                st.subheader("🎓 Painel de Graduação & Histórico")
                
                mapeamento_alunos = {r['Nome']: r['ID'] for index, r in df_e.iterrows()}
                aluno_selecionado = st.selectbox("Selecione o Aluno para Ações:", [""] + list(mapeamento_alunos.keys()))
                
                if aluno_selecionado:
                    id_alvo = mapeamento_alunos[aluno_selecionado]
                    dados_aluno = executar_query("SELECT faixa, graus FROM alunos WHERE id = %s", (id_alvo,), fetch=True)[0]
                    faixa_atual = dados_aluno['faixa']
                    graus_atual = dados_aluno['graus']

                    # --- FREQUÊNCIA ---
                    total_treinos = executar_query("SELECT COUNT(*) FROM presencas WHERE id_aluno = %s", (id_alvo,), fetch=True)[0][0]
                    hoje = date.today()
                    treinos_mes = executar_query("SELECT COUNT(*) FROM presencas WHERE id_aluno = %s AND EXTRACT(MONTH FROM data_aula) = %s AND EXTRACT(YEAR FROM data_aula) = %s", (id_alvo, hoje.month, hoje.year), fetch=True)[0][0]

                    col_info, col_freq1, col_freq2 = st.columns([2, 1, 1])
                    with col_info:
                        st.info(f"**Atleta:** {aluno_selecionado}\n\n**Faixa:** {faixa_atual} | **Graus:** {graus_atual}")
                    with col_freq1:
                        st.metric("Total Treinos", total_treinos)
                    with col_freq2:
                        st.metric("Treinos Mês", treinos_mes)

                    c_grau, c_promo, c_del = st.columns(3)
                    with c_grau:
                        if st.button(f"➕ Add Grau (+1)", use_container_width=True):
                            novo_grau = graus_atual + 1
                            executar_query("UPDATE alunos SET graus = %s, data_ultimo_grau = CURRENT_DATE WHERE id = %s", (novo_grau, id_alvo))
                            executar_query("""INSERT INTO historico_graduacao (id_aluno, faixa_anterior, graus_anterior, faixa_nova, graus_nova, motivo) VALUES (%s, %s, %s, %s, %s, 'Adição de Grau')""", (id_alvo, faixa_atual, graus_atual, faixa_atual, novo_grau))
                            st.cache_data.clear()
                            st.toast(f"Grau adicionado!", icon="🎉")
                            time.sleep(1)
                            st.rerun()
                    with c_promo:
                        nova_faixa_promo = st.selectbox("Nova Faixa:", ["Cinza/Branca", "Cinza", "Cinza/Preta", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"], label_visibility="collapsed")
                        if st.button("🚀 Promover", use_container_width=True):
                            if nova_faixa_promo == faixa_atual: st.error("Mude a faixa!")
                            else:
                                executar_query("UPDATE alunos SET faixa = %s, graus = 0, data_faixa = CURRENT_DATE, data_ultimo_grau = CURRENT_DATE WHERE id = %s", (nova_faixa_promo, id_alvo))
                                executar_query("""INSERT INTO historico_graduacao (id_aluno, faixa_anterior, graus_anterior, faixa_nova, graus_nova, motivo) VALUES (%s, %s, %s, %s, 0, 'Promoção de Faixa')""", (id_alvo, faixa_atual, graus_atual, nova_faixa_promo))
                                st.cache_data.clear()
                                st.toast(f"Promovido para {nova_faixa_promo}!", icon="🥋")
                                time.sleep(1)
                                st.rerun()
                    with c_del:
                        if st.button("🗑️ Excluir Aluno", type="primary", use_container_width=True):
                            executar_query("DELETE FROM alunos WHERE id = %s", (id_alvo,))
                            st.cache_data.clear()
                            st.toast("Aluno removido.", icon="🗑️")
                            time.sleep(1)
                            st.rerun()
                    
                    st.markdown("---")
                    with st.expander(f"📜 Ver Histórico Completo de {aluno_selecionado}"):
                        hist = executar_query("""SELECT data_mudanca, faixa_anterior, graus_anterior, faixa_nova, graus_nova, motivo FROM historico_graduacao WHERE id_aluno = %s ORDER BY data_mudanca DESC, id DESC""", (id_alvo,), fetch=True)
                        if hist:
                            df_hist = pd.DataFrame(hist, columns=['Data', 'Faixa Ant.', 'Grau Ant.', 'Faixa Nova', 'Grau Novo', 'Motivo'])
                            st.dataframe(df_hist, use_container_width=True, hide_index=True, column_config={"Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY")})
                        else: st.write("Nenhum registro histórico encontrado.")

    # --- ABA 3: CHAMADA ---
    with tab_chamada:
        st.header("Diário de Classe")
        ts = executar_query("SELECT id, nome_turma FROM turmas;", fetch=True)
        if ts:
            op_c = {t['nome_turma']: t['id'] for t in ts}
            sel_t = st.selectbox("Selecione a Turma para Chamada", list(op_c.keys()))
            als = executar_query("SELECT id, nome FROM alunos WHERE id_turma = %s AND status_aluno = 'Ativo'", (op_c[sel_t],), fetch=True)
            if als:
                with st.form("chamada"):
                    pres = []
                    cols = st.columns(3)
                    for i, a in enumerate(als):
                        with cols[i % 3]:
                            if st.checkbox(a['nome'], key=f"p_{a['id']}"): pres.append(a['id'])
                    st.divider()
                    if st.form_submit_button("✅ Registrar Presenças"):
                        for id_a in pres: executar_query("INSERT INTO presencas (id_aluno, data_aula) VALUES (%s, CURRENT_DATE)", (id_a,))
                        st.cache_data.clear()
                        st.toast(f"{len(pres)} presenças registradas!", icon="✅")
            else: st.warning("Não há alunos ativos nesta turma.")
        else: st.warning("Cadastre turmas em Configurações.")

    # --- ABA 4: CONFIGURAÇÕES ---
    with tab_regras:
        st.header("Configurações e Remanejamento")
        c_t1, c_t2 = st.columns(2)
        with c_t1:
            st.subheader("🏫 Gestão de Turmas")
            nt = st.text_input("Nome da Turma (Ex: Kids 19h)")
            if st.button("Criar Turma"):
                if nt:
                    executar_query("INSERT INTO turmas (nome_turma) VALUES (%s)", (nt,))
                    st.rerun()
            lt = executar_query("SELECT id, nome_turma FROM turmas", fetch=True)
            if lt:
                st.table(pd.DataFrame(lt, columns=['ID', 'Nome']))
                mapeamento_turmas = {t['nome_turma']: t['id'] for t in lt}
                turma_para_remover = st.selectbox("Selecione a Turma para remover:", [""] + list(mapeamento_turmas.keys()))
                if st.button("Remover Turma"):
                    if turma_para_remover:
                        executar_query("DELETE FROM turmas WHERE id = %s", (mapeamento_turmas[turma_para_remover],))
                        st.rerun()
        with c_t2:
            st.subheader("🔄 Transferir Aluno de Turma")
            todos = executar_query("SELECT id, nome FROM alunos ORDER BY nome", fetch=True)
            if todos and lt:
                a_sel = st.selectbox("Aluno para transferir:", {a['nome']: a['id'] for a in todos}.keys())
                t_sel = st.selectbox("Nova Turma de destino:", {t['nome_turma']: t['id'] for t in lt}.keys())
                if st.button("Confirmar Transferência"):
                    id_turma_nova = {t['nome_turma']: t['id'] for t in lt}[t_sel]
                    id_aluno_sel = {a['nome']: a['id'] for a in todos}[a_sel]
                    executar_query("UPDATE alunos SET id_turma = %s WHERE id = %s", (id_turma_nova, id_aluno_sel))
                    st.toast(f"{a_sel} transferido para {t_sel}!", icon="🔄")
                    st.rerun()

if st.session_state.pagina_atual == 'login':
    tela_login()
elif st.session_state.pagina_atual == 'cadastro_aluno':
    tela_cadastro_aluno()
elif st.session_state.pagina_atual == 'sistema':
    if st.session_state.logado:
        sistema_principal()
    else:
        st.session_state.pagina_atual = 'login'
        st.rerun()