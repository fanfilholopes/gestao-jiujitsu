import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timedelta
import time
import os
import re
import urllib.parse
import pytz

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="SER Jiu-Jítsu - Sistema Integrado", 
    page_icon="logoser.jpg", 
    layout="wide"
)

# --- GERENCIAMENTO DE ESTADO ---
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 'login'
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'aluno_id' not in st.session_state:
    st.session_state.aluno_id = None

# --- FUNÇÃO DE DATA/HORA BRASIL ---
def data_hora_brasil():
    fuso = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(fuso)
    return agora.date(), agora.time()

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

# --- FUNÇÃO PARA EXECUTAR COMANDOS ---
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
    hoje, _ = data_hora_brasil()
    try:
        res_total = executar_query("SELECT COUNT(*) FROM alunos WHERE status_aluno = 'Ativo';", fetch=True)
        total_alunos = res_total[0][0] if res_total else 0
        niver_mes = executar_query("SELECT nome, EXTRACT(DAY FROM data_nascimento) as dia FROM alunos WHERE EXTRACT(MONTH FROM data_nascimento) = %s ORDER BY dia;", (hoje.month,), fetch=True)
        dados_faixa = executar_query("SELECT faixa, COUNT(*) as total FROM alunos WHERE status_aluno = 'Ativo' GROUP BY faixa;", fetch=True)
        data_limite = hoje - timedelta(days=7)
        dados_freq = executar_query("SELECT data_aula, COUNT(*) as total FROM presencas WHERE data_aula >= %s GROUP BY data_aula ORDER BY data_aula", (data_limite,), fetch=True)
        return total_alunos, niver_mes, dados_faixa, dados_freq
    except:
        return 0, [], [], []

# --- HELPER: CALCULAR IDADE ---
def calcular_idade(nascimento):
    if not nascimento: return 0
    hoje, _ = data_hora_brasil()
    return hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))

# --- HELPER: LIMPAR TELEFONE ---
def limpar_telefone(telefone):
    if not telefone: return ""
    return re.sub(r'\D', '', str(telefone))

# --- HELPER: EXPORTAR CSV ---
def converter_df_para_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- FUNÇÃO PARA EXIBIR LOGO ---
def mostrar_logo():
    if os.path.exists("logoser.jpg"):
        st.image("logoser.jpg", width=200)
    elif os.path.exists("logo.png"):
        st.image("logo.png", width=200)

# ==========================================
# TELA 1: LOGIN
# ==========================================
def tela_login():
    st.markdown("""
        <style>
        .block-container { padding-top: 3rem; padding-bottom: 2rem; }
        [data-testid="stImage"] { display: flex; align-items: center; justify-content: center; height: 100%; }
        [data-testid="stImage"] > img { max-width: 100%; height: auto; object-fit: contain; }
        .title-container { display: flex; flex-direction: column; justify-content: center; height: 100%; }
        </style>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 3, 1])
    
    with c2:
        col_img_header, col_text_header = st.columns([1, 3])
        with col_img_header: mostrar_logo()
        with col_text_header:
            st.markdown("""<div class="title-container"><h1 style='text-align: left; margin-bottom: 0;'>🥋 SER Jiu-Jítsu - FamilyFit</h1><p style='text-align: left; color: grey; margin-top: -5px;'>Sistema de Gestão de Turmas</p></div>""", unsafe_allow_html=True)
        
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
                        else: st.toast("🚫 Usuário ou senha incorretos.", icon="❌")
                    except KeyError: st.error("Erro: Configure [admin] nos Secrets.")

        with tab_aluno:
            st.write("")
            opcao_aluno = st.radio("Selecione:", ["Já sou aluno", "Quero me cadastrar"], horizontal=True)
            
            if opcao_aluno == "Já sou aluno":
                with st.form("login_aluno"):
                    tel_input = st.text_input("Seu WhatsApp (igual ao cadastro)", placeholder="Ex: 85999999999")
                    if st.form_submit_button("Acessar Meu Painel", use_container_width=True):
                        tel_limpo = limpar_telefone(tel_input)
                        aluno = executar_query("SELECT id, nome FROM alunos WHERE telefone = %s", (tel_limpo,), fetch=True)
                        if aluno:
                            st.session_state.aluno_id = aluno[0]['id']
                            st.session_state.aluno_nome = aluno[0]['nome']
                            st.session_state.pagina_atual = 'area_aluno'
                            st.rerun()
                        else:
                            st.error("Telefone não encontrado. Faça seu cadastro primeiro.")
            else:
                st.info("Preencha sua ficha para entrar no time.")
                if st.button("📝 Ir para Ficha de Cadastro", use_container_width=True):
                    st.session_state.pagina_atual = 'cadastro_aluno'
                    st.rerun()
            
            st.markdown("---")
            st.caption("Dúvidas? Procure seu professor no tatame.")

# ==========================================
# TELA: ÁREA RESTRITA DO ALUNO
# ==========================================
def tela_area_aluno():
    col_logo, col_sair = st.columns([4, 1])
    with col_logo:
        st.subheader(f"Bem-vindo, {st.session_state.aluno_nome}! 🥋")
    with col_sair:
        if st.button("Sair"):
            st.session_state.aluno_id = None
            st.session_state.pagina_atual = 'login'
            st.rerun()
            
    id_a = st.session_state.aluno_id
    
    # --- MURAL DE AVISOS ---
    avisos = executar_query("SELECT titulo, mensagem, data_postagem FROM mural_avisos WHERE ativo = TRUE ORDER BY id DESC LIMIT 1", fetch=True)
    if avisos:
        aviso = avisos[0]
        st.warning(f"📢 **{aviso['titulo']}**\n\n{aviso['mensagem']}", icon="⚠️")

    dados = executar_query("SELECT * FROM alunos WHERE id = %s", (id_a,), fetch=True)[0]
    
    # --- CHECK-IN ---
    st.markdown("### 📍 Check-in de Treino")
    hoje_br, hora_br = data_hora_brasil()
    
    presenca_hoje = executar_query("SELECT id FROM presencas WHERE id_aluno = %s AND data_aula = %s", (id_a, hoje_br), fetch=True)
    checkin_pendente = executar_query("SELECT id, hora_checkin FROM checkins WHERE id_aluno = %s AND data_checkin = %s", (id_a, hoje_br), fetch=True)
    
    if presenca_hoje:
        st.success("✅ Presença CONFIRMADA no treino de hoje! Bom descanso.")
    elif checkin_pendente:
        hora_formatada = checkin_pendente[0]['hora_checkin'].strftime('%H:%M')
        st.info(f"⏳ Check-in feito às {hora_formatada}. Aguardando professor.")
    else:
        if st.button("💪 Fazer Check-in Agora", type="primary", use_container_width=True):
            executar_query("INSERT INTO checkins (id_aluno, data_checkin, hora_checkin) VALUES (%s, %s, %s)", (id_a, hoje_br, hora_br))
            st.balloons()
            st.toast("Check-in enviado!", icon="📨")
            time.sleep(2)
            st.rerun()
            
    st.divider()

    # --- ESTATÍSTICAS ---
    total_treinos = executar_query("SELECT COUNT(*) FROM presencas WHERE id_aluno = %s", (id_a,), fetch=True)[0][0]
    treinos_mes = executar_query("SELECT COUNT(*) FROM presencas WHERE id_aluno = %s AND EXTRACT(MONTH FROM data_aula) = %s", (id_a, hoje_br.month), fetch=True)[0][0]
    
    meta_treinos = 100 
    xp = min(total_treinos / meta_treinos, 1.0)
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("Faixa Atual", dados['faixa'], f"{dados['graus']}º Grau")
    col_kpi2.metric("Total Treinos", total_treinos)
    col_kpi3.metric("Treinos no Mês", treinos_mes, "+1" if presenca_hoje else "0")
    
    st.write(f"**Nível de Experiência (XP)**")
    st.progress(xp, text=f"{total_treinos} aulas totais")
    st.caption("A consistência leva à perfeição. Continue treinando!")
    
    st.divider()
    
    # --- RANKING DOS CASCA-GROSSAS (SEPARADO POR ABAS NO ALUNO) ---
    st.subheader("🏆 Ranking do Mês (Top 5)")
    
    # Query Base
    q_base = """
        SELECT a.nome, COUNT(p.id) as total 
        FROM presencas p 
        JOIN alunos a ON p.id_aluno = a.id 
        WHERE EXTRACT(MONTH FROM p.data_aula) = EXTRACT(MONTH FROM CURRENT_DATE)
        AND EXTRACT(YEAR FROM p.data_aula) = EXTRACT(YEAR FROM CURRENT_DATE)
    """
    
    tab_rank_adulto, tab_rank_kids = st.tabs(["🦍 Adultos", "🦁 Kids"])
    
    with tab_rank_adulto:
        q_adulto = q_base + " AND a.data_nascimento <= CURRENT_DATE - INTERVAL '16 years' GROUP BY a.nome ORDER BY total DESC LIMIT 5"
        rank_ad = executar_query(q_adulto, fetch=True)
        if rank_ad:
            for i, r in enumerate(rank_ad, start=1):
                nome_limpo = r['nome'].strip()
                if r['nome'] == st.session_state.aluno_nome:
                    st.success(f"**#{i} {nome_limpo}** - {r['total']} treinos (VOCÊ!)")
                else:
                    st.write(f"#{i} **{nome_limpo}** - {r['total']} treinos")
        else:
            st.info("Ranking Adulto vazio.")

    with tab_rank_kids:
        q_kids = q_base + " AND a.data_nascimento > CURRENT_DATE - INTERVAL '16 years' GROUP BY a.nome ORDER BY total DESC LIMIT 5"
        rank_kd = executar_query(q_kids, fetch=True)
        if rank_kd:
            for i, r in enumerate(rank_kd, start=1):
                nome_limpo = r['nome'].strip()
                if r['nome'] == st.session_state.aluno_nome:
                    st.success(f"**#{i} {nome_limpo}** - {r['total']} treinos (VOCÊ!)")
                else:
                    st.write(f"#{i} **{nome_limpo}** - {r['total']} treinos")
        else:
            st.info("Ranking Kids vazio.")

    st.divider()
    
    with st.expander("📜 Ver meu Histórico de Graduação"):
        hist = executar_query("SELECT data_mudanca, faixa_nova, graus_nova, motivo FROM historico_graduacao WHERE id_aluno = %s ORDER BY data_mudanca DESC", (id_a,), fetch=True)
        if hist:
            for item in hist:
                st.write(f"**{item['data_mudanca'].strftime('%d/%m/%Y')}** - {item['motivo']} | Faixa: `{item['faixa_nova']}`")
        else:
            st.write("Sem histórico.")

# ==========================================
# TELA 2: AUTO-CADASTRO
# ==========================================
def tela_cadastro_aluno():
    st.button("⬅️ Voltar", on_click=lambda: st.session_state.update({'pagina_atual': 'login'}))
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
        tel_auto = col_tel.text_input("WhatsApp (Somente números, Ex: 85222223333) *")
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
                tel_limpo = limpar_telefone(tel_auto)
                existe = executar_query("SELECT id FROM alunos WHERE telefone = %s", (tel_limpo,), fetch=True)
                
                if existe:
                    st.toast("⚠️ Já existe um atleta cadastrado com este WhatsApp!", icon="🚨")
                    st.warning("Se você já tem cadastro, vá na tela de login e use este número.")
                else:
                    id_t_auto = op_t_auto.get(turma_auto)
                    dt_grau_final = data_grau_auto if graus_auto > 0 else data_faixa_auto
                    q_auto = """INSERT INTO alunos (nome, data_nascimento, faixa, graus, id_turma, nome_responsavel, telefone, status_aluno, data_faixa, data_ultimo_grau) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Ativo', %s, %s) RETURNING id"""
                    novo_id = executar_query(q_auto, (nome_auto, nasc_auto, faixa_auto, graus_auto, id_t_auto, resp_auto, tel_limpo, data_faixa_auto, dt_grau_final), fetch=True)[0][0]
                    executar_query("""INSERT INTO historico_graduacao (id_aluno, faixa_nova, graus_nova, data_mudanca, motivo) 
                                      VALUES (%s, %s, %s, %s, 'Cadastro Inicial')""", (novo_id, faixa_auto, graus_auto, dt_grau_final))
                    st.balloons()
                    st.toast(f"Cadastro de {nome_auto} realizado!", icon="✅")
                    time.sleep(3)
                    st.session_state.pagina_atual = 'login'
                    st.rerun()
            else: st.toast("Preencha Nome, Telefone e Turma.", icon="🚨")

# ==========================================
# TELA 3: SISTEMA PRINCIPAL (ADMIN)
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
    
    # --- ÁREA DE NOTIFICAÇÕES (USANDO FUSO CORRIGIDO E TRIM NOS NOMES) ---
    hoje_br, _ = data_hora_brasil()
    
    pendentes = executar_query("""
        SELECT c.id, c.hora_checkin, c.data_checkin, a.nome, a.id as id_aluno 
        FROM checkins c 
        JOIN alunos a ON c.id_aluno = a.id 
        ORDER BY c.data_checkin DESC, c.hora_checkin DESC
    """, fetch=True)
    
    if pendentes:
        st.info(f"🔔 **{len(pendentes)}** Aluno(s) pedindo check-in agora!")
        with st.expander("Ver Pedidos de Check-in", expanded=True):
            for p in pendentes:
                col_nome, col_btn_ok, col_btn_no = st.columns([3, 1, 1])
                with col_nome:
                    hora_formatada = p['hora_checkin'].strftime('%H:%M')
                    data_str = ""
                    if p['data_checkin'] != hoje_br:
                        data_str = f" ({p['data_checkin'].strftime('%d/%m')})"
                    # .strip() remove espaços extras
                    st.write(f"**{p['nome'].strip()}** às {hora_formatada}{data_str}")
                
                with col_btn_ok:
                    if st.button("✅ Aprovar", key=f"ok_{p['id']}"):
                        executar_query("INSERT INTO presencas (id_aluno, data_aula) VALUES (%s, %s)", (p['id_aluno'], p['data_checkin']))
                        executar_query("DELETE FROM checkins WHERE id = %s", (p['id'],))
                        st.toast(f"{p['nome'].strip()} confirmado!", icon="✅")
                        time.sleep(1)
                        st.rerun()
                with col_btn_no:
                    if st.button("❌ Rejeitar", key=f"no_{p['id']}"):
                        executar_query("DELETE FROM checkins WHERE id = %s", (p['id'],))
                        st.toast("Pedido rejeitado.", icon="🗑️")
                        time.sleep(1)
                        st.rerun()
        st.divider()

    tab_dash, tab_gestao, tab_chamada, tab_msg, tab_regras = st.tabs([
        "📊 Dashboard", "👥 Gestão Alunos", "📅 Chamada", "📢 Comunicação", "⚙️ Configurações"
    ])

    # --- ABA 1: DASHBOARD ---
    with tab_dash:
        st.header("Visão Geral")
        total_alunos, niver_mes, dados_f, dados_freq = carregar_dados_dashboard()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Alunos Ativos", total_alunos)
        
        aniversariantes_hoje = [n for n in niver_mes if n['dia'] == hoje_br.day]
        c2.metric("Aniversariantes Hoje", len(aniversariantes_hoje))
        if aniversariantes_hoje: c2.success(f"🎉 {', '.join([n['nome'].strip() for n in aniversariantes_hoje])}")
        
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
        
        # === RANKING DE ASSIDUIDADE SEPARADO (NOVIDADE) ===
        st.subheader("🏆 Ranking dos Casca-Grossas (Este Mês)")
        
        q_base = """
            SELECT a.nome, COUNT(p.id) as total 
            FROM presencas p 
            JOIN alunos a ON p.id_aluno = a.id 
            WHERE EXTRACT(MONTH FROM p.data_aula) = EXTRACT(MONTH FROM CURRENT_DATE)
            AND EXTRACT(YEAR FROM p.data_aula) = EXTRACT(YEAR FROM CURRENT_DATE)
        """
        
        col_r_adulto, col_r_kids = st.columns(2)
        
        # --- RANKING ADULTOS (> 16 ANOS) ---
        with col_r_adulto:
            st.markdown("### 🦍 Adultos")
            q_adulto = q_base + " AND a.data_nascimento <= CURRENT_DATE - INTERVAL '16 years' GROUP BY a.nome ORDER BY total DESC LIMIT 5"
            rank_ad = executar_query(q_adulto, fetch=True)
            
            if rank_ad:
                c_ad = rank_ad[0]
                st.info(f"🥇 **{c_ad['nome'].strip()}** ({c_ad['total']} treinos)")
                for i, r in enumerate(rank_ad[1:], start=2):
                    st.write(f"**{i}º** {r['nome'].strip()} - {r['total']}")
            else:
                st.info("Sem treinos de adultos este mês.")

        # --- RANKING KIDS (<= 16 ANOS) ---
        with col_r_kids:
            st.markdown("### 🦁 Kids")
            q_kids = q_base + " AND a.data_nascimento > CURRENT_DATE - INTERVAL '16 years' GROUP BY a.nome ORDER BY total DESC LIMIT 5"
            rank_kd = executar_query(q_kids, fetch=True)
            
            if rank_kd:
                c_kd = rank_kd[0]
                st.info(f"🥇 **{c_kd['nome'].strip()}** ({c_kd['total']} treinos)")
                for i, r in enumerate(rank_kd[1:], start=2):
                    st.write(f"**{i}º** {r['nome'].strip()} - {r['total']}")
            else:
                st.info("Sem treinos kids este mês.")
            
        st.divider()
        
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
                
                if alu['graus'] == 0:
                    dt_grau = alu['data_faixa'] or hoje_br
                else:
                    dt_grau = alu['data_ultimo_grau'] or hoje_br
                
                dt_faixa = alu['data_faixa'] or hoje_br
                
                aulas_no_grau = executar_query("SELECT COUNT(*) FROM presencas WHERE id_aluno = %s AND data_aula >= %s", (alu['id'], dt_grau), fetch=True)[0][0]
                meses_no_grau = (hoje_br - dt_grau).days // 30
                meses_na_faixa = (hoje_br - dt_faixa).days // 30
                
                if idade < 16:
                    if aulas_no_grau >= 8: lista_grau.append({"Nome": alu['nome'], "Faixa": alu['faixa'], "Aulas": aulas_no_grau, "Motivo": "8+ Aulas"})
                    if meses_na_faixa >= 6: lista_faixa.append({"Nome": alu['nome'], "Faixa Atual": alu['faixa'], "Tempo Total": f"{meses_na_faixa} m", "Status": "✅ Apto (Padrão)"})
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
                        tempo_total_necessario = {'Branca': 0, 'Azul': 24, 'Roxa': 18, 'Marrom': 12, 'Preta': 0}
                        minimo_meses = tempo_total_necessario.get(alu['faixa'], 999)
                        carencia_grau_necessaria = 3 if alu['faixa'] == 'Branca' else 6
                        
                        if meses_na_faixa >= minimo_meses:
                            status_final = ""
                            if meses_no_grau >= carencia_grau_necessaria:
                                status_final = "✅ Apto (Padrão)"
                            else:
                                status_final = "⚠️ Indicação (Tempo Total)"
                                
                            lista_faixa.append({
                                "Nome": alu['nome'], 
                                "Faixa Atual": alu['faixa'], 
                                "Tempo Total": f"{meses_na_faixa} m", 
                                "Status": status_final
                            })

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
                
                # AQUI ESTÁ A CORREÇÃO DA DATA (MIN_VALUE 1920)
                nasc = c1.date_input("Nascimento", value=date(2000, 1, 1), min_value=date(1920, 1, 1), max_value=date.today(), format="DD/MM/YYYY")
                
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
                    tel_limpo = limpar_telefone(tel)
                    aluno_existente = executar_query("SELECT nome FROM alunos WHERE telefone = %s", (tel_limpo,), fetch=True)
                    
                    if aluno_existente:
                        st.error(f"❌ Erro: O número {tel} já está cadastrado para o aluno: {aluno_existente[0]['nome']}")
                    else:
                        id_t = op_t.get(turma)
                        q = """INSERT INTO alunos (nome, data_nascimento, faixa, graus, id_turma, nome_responsavel, telefone, status_aluno, data_faixa, data_ultimo_grau) 
                               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Ativo', %s, %s) RETURNING id"""
                        novo_id = executar_query(q, (nome, nasc, faixa, graus, id_t, resp, tel_limpo, d_faixa, d_grau), fetch=True)[0][0]
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
                
                df_up = st.data_editor(df_e, use_container_width=True, hide_index=True, key="editor_alunos", disabled=("ID",), column_config={"Nascimento": st.column_config.DateColumn("Nascimento", format="DD/MM/YYYY"), "Data Faixa": st.column_config.DateColumn("Data Faixa", format="DD/MM/YYYY"), "Data Último Grau": st.column_config.DateColumn("Data Último Grau", format="DD/MM/YYYY")})
                
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
                    total_treinos = executar_query("SELECT COUNT(*) FROM presencas WHERE id_aluno = %s", (id_alvo,), fetch=True)[0][0]
                    hoje_br, _ = data_hora_brasil()
                    treinos_mes = executar_query("SELECT COUNT(*) FROM presencas WHERE id_aluno = %s AND EXTRACT(MONTH FROM data_aula) = %s AND EXTRACT(YEAR FROM data_aula) = %s", (id_alvo, hoje_br.month, hoje_br.year), fetch=True)[0][0]

                    col_info, col_freq1, col_freq2 = st.columns([2, 1, 1])
                    with col_info: st.info(f"**Atleta:** {aluno_selecionado}\n\n**Faixa:** {faixa_atual} | **Graus:** {graus_atual}")
                    with col_freq1: st.metric("Total Treinos", total_treinos)
                    with col_freq2: st.metric("Treinos Mês", treinos_mes)

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
                    hoje_br, _ = data_hora_brasil()
                    data_aula_manual = st.date_input("📅 Data da Aula", value=hoje_br)
                    st.write("Marque quem estava presente:")
                    pres = []
                    cols = st.columns(3)
                    for i, a in enumerate(als):
                        with cols[i % 3]:
                            if st.checkbox(a['nome'], key=f"p_{a['id']}"): pres.append(a['id'])
                    st.divider()
                    if st.form_submit_button("✅ Registrar Presenças"):
                        for id_a in pres: 
                            executar_query("INSERT INTO presencas (id_aluno, data_aula) VALUES (%s, %s)", (id_a, data_aula_manual))
                        st.cache_data.clear()
                        st.toast(f"{len(pres)} presenças registradas para {data_aula_manual.strftime('%d/%m')}!", icon="✅")
            else: st.warning("Não há alunos ativos nesta turma.")
            
            st.divider()
            st.subheader("🔎 Consultar Presenças Anteriores")
            col_data_hist, col_resumo_hist = st.columns([1, 2])
            with col_data_hist:
                hoje_br, _ = data_hora_brasil()
                data_busca = st.date_input("Ver presença do dia:", value=hoje_br, key="hist_busca")
            q_hist = """
                SELECT a.nome, to_char(p.data_aula, 'DD/MM/YYYY') as data
                FROM presencas p 
                JOIN alunos a ON p.id_aluno = a.id 
                WHERE p.data_aula = %s AND a.id_turma = %s
                ORDER BY a.nome
            """
            hist_presenca = executar_query(q_hist, (data_busca, op_c[sel_t]), fetch=True)
            with col_resumo_hist:
                if hist_presenca:
                    st.success(f"✅ Total: {len(hist_presenca)} alunos presentes.")
                    df_hist_p = pd.DataFrame(hist_presenca, columns=['Aluno', 'Data'])
                    st.dataframe(df_hist_p, use_container_width=True, hide_index=True)
                else: st.info("📭 Ninguém marcado nesta data para esta turma.")
        else: st.warning("Cadastre turmas em Configurações.")

    # --- ABA NOVA: COMUNICAÇÃO (HÍBRIDA) ---
    with tab_msg:
        st.header("📢 Central de Comunicação")
        
        tab_zap, tab_mural = st.tabs(["💬 WhatsApp Individual", "📌 Mural de Avisos"])
        
        # --- SUB-ABA: WHATSAPP ---
        with tab_zap:
            st.markdown("Envie mensagens rápidas para seus alunos.")
            lista_completa = executar_query("SELECT id, nome, telefone FROM alunos ORDER BY nome", fetch=True)
            if lista_completa:
                mapa_msg = {a['nome']: a for a in lista_completa}
                aluno_msg = st.selectbox("Enviar mensagem para:", list(mapa_msg.keys()))
                
                if aluno_msg:
                    dados_msg = mapa_msg[aluno_msg]
                    telefone_msg = dados_msg['telefone']
                    
                    tipo_msg = st.selectbox("Motivo da Mensagem:", [
                        "Ausência (Sumido)",
                        "Cobrança de Mensalidade",
                        "Parabéns (Aniversário)",
                        "Aviso de Graduação",
                        "Personalizada"
                    ])
                    
                    texto_base = ""
                    if tipo_msg == "Ausência (Sumido)":
                        texto_base = f"Fala {aluno_msg}, tudo bem? 🥋\n\nSentimos sua falta nos treinos essa semana! Tá tudo certo? Bora voltar pro tatame!"
                    elif tipo_msg == "Cobrança de Mensalidade":
                        texto_base = f"Olá {aluno_msg}, tudo bem? 🥋\n\nPassando pra lembrar sobre a mensalidade deste mês. Quando puder, me dá um alô!"
                    elif tipo_msg == "Parabéns (Aniversário)":
                        texto_base = f"Parabéns, {aluno_msg}! 🎉🥋\n\nMuitos anos de vida e muito Jiu-Jitsu pra você! Oss!"
                    elif tipo_msg == "Aviso de Graduação":
                        texto_base = f"Grande {aluno_msg}! 🥋\n\nTenho boas notícias sobre sua graduação. Não falte ao próximo treino!"
                    
                    txt_final = st.text_area("Texto da Mensagem (pode editar):", value=texto_base, height=150)
                    
                    if telefone_msg:
                        texto_encoded = urllib.parse.quote(txt_final)
                        link_wa = f"https://wa.me/55{telefone_msg}?text={texto_encoded}"
                        st.link_button(f"🚀 Enviar WhatsApp para {aluno_msg}", link_wa, type="primary")
                    else:
                        st.error("Este aluno não tem telefone cadastrado.")

        # --- SUB-ABA: MURAL ---
        with tab_mural:
            st.markdown("Poste avisos que aparecerão para **todos os alunos** ao fazerem login.")
            
            with st.form("novo_aviso"):
                tit_aviso = st.text_input("Título do Aviso (Ex: Seminário)")
                msg_aviso = st.text_area("Mensagem Completa")
                if st.form_submit_button("📌 Publicar no Mural"):
                    executar_query("INSERT INTO mural_avisos (titulo, mensagem) VALUES (%s, %s)", (tit_aviso, msg_aviso))
                    st.success("Aviso publicado!")
                    time.sleep(1)
                    st.rerun()
            
            st.divider()
            st.subheader("Avisos Ativos")
            avisos_ativos = executar_query("SELECT id, titulo, mensagem, data_postagem FROM mural_avisos WHERE ativo = TRUE ORDER BY id DESC", fetch=True)
            if avisos_ativos:
                for av in avisos_ativos:
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.info(f"**{av['titulo']}** ({av['data_postagem']})\n\n{av['mensagem']}")
                    with c2:
                        if st.button("🗑️ Apagar", key=f"del_av_{av['id']}"):
                            executar_query("UPDATE mural_avisos SET ativo = FALSE WHERE id = %s", (av['id'],))
                            st.rerun()
            else:
                st.write("Nenhum aviso ativo no momento.")

    # --- ABA 5: CONFIGURAÇÕES ---
    with tab_regras:
        st.header("Configurações e Backup")
        st.subheader("💾 Backup e Dados")
        st.markdown("Baixe a lista completa de alunos para ter um backup seguro no seu computador.")
        todos_alunos = executar_query("SELECT * FROM alunos", fetch=True)
        if todos_alunos:
            df_export = pd.DataFrame(todos_alunos)
            csv = converter_df_para_csv(df_export)
            st.download_button(label="📥 Baixar Planilha Completa (Excel/CSV)", data=csv, file_name=f"backup_alunos_{date.today()}.csv", mime="text/csv", type="primary")
        st.divider()
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

# --- CONTROLADOR DE FLUXO ---
if st.session_state.pagina_atual == 'login':
    tela_login()
elif st.session_state.pagina_atual == 'cadastro_aluno':
    tela_cadastro_aluno()
elif st.session_state.pagina_atual == 'area_aluno':
    tela_area_aluno()
elif st.session_state.pagina_atual == 'sistema':
    if st.session_state.logado:
        sistema_principal()
    else:
        st.session_state.pagina_atual = 'login'
        st.rerun()