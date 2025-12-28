import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import date
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
        else:
            conn.commit()
            resultado = True
        cur.close()
        conn.close()
        return resultado
    except Exception as e:
        st.error(f"Erro no banco: {e}")
        return [] if fetch else False

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
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        col_img1, col_img2, col_img3 = st.columns([1,2,1])
        with col_img2:
            mostrar_logo()
            
        st.markdown("<h1 style='text-align: center;'>🥋 SER Jiu-Jítsu Team</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Sistema de Gestão Profissional</p>", unsafe_allow_html=True)
        st.divider()
        
        with st.form("form_login"):
            st.markdown("### 🔒 Acesso do Professor/Admin")
            user = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if entrar:
                try:
                    if user == st.secrets["admin"]["usuario"] and password == st.secrets["admin"]["senha"]:
                        st.session_state.logado = True
                        st.session_state.pagina_atual = 'sistema'
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                except KeyError:
                    st.error("Erro: Configure [admin] nos Secrets.")

        st.markdown("---")
        st.info("É aluno novo? Faça seu cadastro por aqui.")
        if st.button("📝 Fazer Auto-Cadastro (Aluno)", use_container_width=True):
            st.session_state.pagina_atual = 'cadastro_aluno'
            st.rerun()

# ==========================================
# TELA 2: AUTO-CADASTRO
# ==========================================
def tela_cadastro_aluno():
    st.button("⬅️ Voltar para Login", on_click=lambda: st.session_state.update({'pagina_atual': 'login'}))
    
    col_logo1, col_logo2 = st.columns([1, 5])
    with col_logo1:
        mostrar_logo()
    with col_logo2:
        st.title("Portal do Atleta")
        st.markdown("Bem-vindo à equipe! Preencha sua ficha.")
    
    with st.form("form_auto_cadastro", clear_on_submit=True):
        st.markdown("### 1. Dados Pessoais")
        col1, col2 = st.columns(2)
        nome_auto = col1.text_input("Nome Completo *")
        
        nasc_auto = col1.date_input("Data de Nascimento", 
                                    value=date(2000, 1, 1), 
                                    min_value=date(1920, 1, 1), 
                                    max_value=date.today(),
                                    format="DD/MM/YYYY")
        
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
                    st.error("⚠️ Atenção: Já existe um aluno cadastrado com esse Nome e Telefone!")
                else:
                    id_t_auto = op_t_auto.get(turma_auto)
                    dt_grau_final = data_grau_auto if graus_auto > 0 else data_faixa_auto

                    q_auto = """INSERT INTO alunos (nome, data_nascimento, faixa, graus, id_turma, nome_responsavel, telefone, status_aluno, data_faixa, data_ultimo_grau) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Ativo', %s, %s)"""
                    
                    executar_query(q_auto, (nome_auto, nasc_auto, faixa_auto, graus_auto, id_t_auto, resp_auto, tel_auto, data_faixa_auto, dt_grau_final))
                    
                    st.balloons()
                    st.success(f"OSS! Cadastro de {nome_auto} realizado com sucesso!")
                    time.sleep(3)
                    st.session_state.pagina_atual = 'login'
                    st.rerun()
            else:
                st.error("Erro: Nome, Telefone e Turma são obrigatórios.")

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
        hoje = date.today()
        try:
            res_total = executar_query("SELECT COUNT(*) FROM alunos WHERE status_aluno = 'Ativo';", fetch=True)
            total_alunos = res_total[0][0] if res_total else 0
            niver_hoje = executar_query("SELECT nome FROM alunos WHERE EXTRACT(MONTH FROM data_nascimento) = %s AND EXTRACT(DAY FROM data_nascimento) = %s;", (hoje.month, hoje.day), fetch=True)
        except:
            total_alunos = 0
            niver_hoje = []
            st.warning("Tabelas não encontradas.")

        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Total de Atletas Ativos", total_alunos)
        col_m2.metric("Aniversariantes de Hoje", len(niver_hoje) if niver_hoje else 0)
        
        st.divider()

        # === GRÁFICOS E TABELA DE RESUMO (RESTAURADOS) ===
        col_graf, col_tab = st.columns([2, 1])
        
        with col_graf:
            st.subheader("📊 Distribuição por Faixas")
            dados_f = executar_query("SELECT faixa, COUNT(*) as total FROM alunos GROUP BY faixa;", fetch=True)
            if dados_f:
                df_g = pd.DataFrame(dados_f, columns=['faixa', 'total'])
                ordem_faixas = ["Branca", "Cinza/Branca", "Cinza", "Cinza/Preta", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
                df_g['faixa'] = pd.Categorical(df_g['faixa'], categories=ordem_faixas, ordered=True)
                df_g = df_g.sort_values('faixa')
                st.bar_chart(df_g.set_index('faixa'))
            else:
                st.info("Sem dados para exibir o gráfico.")

        with col_tab:
            st.subheader("📋 Resumo Numérico")
            if dados_f:
                # Mostra a mesma informação do gráfico, mas em tabela
                st.dataframe(df_g[['faixa', 'total']].style.hide(axis="index"), use_container_width=True)

        st.divider()

        # === ALERTAS DE GRADUAÇÃO ===
        st.subheader("🎓 Análise de Graduação")
        alunos_analise = executar_query("""
            SELECT a.id, a.nome, a.faixa, a.graus, a.data_faixa, a.data_ultimo_grau, 
            (SELECT COUNT(*) FROM presencas WHERE id_aluno = a.id) as aulas
            FROM alunos a WHERE a.status_aluno = 'Ativo'
        """, fetch=True)

        lista_apto_exame = []
        lista_apto_grau = []

        if alunos_analise:
            for alu in alunos_analise:
                dt_faixa = alu['data_faixa'] or hoje
                dt_grau = alu['data_ultimo_grau'] or dt_faixa
                meses_faixa = (hoje - dt_faixa).days // 30
                meses_grau = (hoje - dt_grau).days // 30
                
                # Regras Simplificadas
                if alu['faixa'] in ["Branca", "Cinza/Branca", "Cinza", "Cinza/Preta", "Amarela", "Laranja", "Verde"]:
                    if alu['aulas'] >= 8 and meses_faixa >= 6:
                        lista_apto_exame.append({"Nome": alu['nome'], "Faixa": alu['faixa'], "Aulas": alu['aulas']})
                elif alu['faixa'] in ["Azul", "Roxa", "Marrom"]:
                    if meses_grau >= 6:
                        lista_apto_grau.append({"Nome": alu['nome'], "Faixa": alu['faixa'], "Graus Atual": alu['graus']})

        if lista_apto_exame or lista_apto_grau:
            if lista_apto_exame:
                st.warning(f"🚨 Exame de Faixa: {len(lista_apto_exame)} aluno(s)")
                st.dataframe(pd.DataFrame(lista_apto_exame), use_container_width=True, hide_index=True)
            if lista_apto_grau:
                st.info(f"🆙 Novos Graus: {len(lista_apto_grau)} aluno(s)")
                st.dataframe(pd.DataFrame(lista_apto_grau), use_container_width=True, hide_index=True)
        else:
            st.success("✅ Todos os alunos estão com a graduação em dia!")

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
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Ativo')"""
                    executar_query(q, (nome, nasc, faixa, graus, d_faixa, d_grau, id_t, resp, tel))
                    st.success("Cadastrado com sucesso!")
                    st.rerun()
        else:
            dados = executar_query("SELECT id, nome, data_nascimento, faixa, graus, data_faixa, data_ultimo_grau, nome_responsavel, telefone FROM alunos ORDER BY nome", fetch=True)
            if dados:
                df_e = pd.DataFrame(dados, columns=['ID', 'Nome', 'Nascimento', 'Faixa', 'Graus', 'Data Faixa', 'Data Último Grau', 'Responsável', 'Telefone'])
                df_up = st.data_editor(
                    df_e, 
                    use_container_width=True, 
                    hide_index=True, 
                    key="editor_alunos",
                    column_config={
                        "Nascimento": st.column_config.DateColumn("Nascimento", format="DD/MM/YYYY"),
                        "Data Faixa": st.column_config.DateColumn("Data Faixa", format="DD/MM/YYYY"),
                        "Data Último Grau": st.column_config.DateColumn("Data Último Grau", format="DD/MM/YYYY")
                    }
                )
                if st.button("💾 Salvar Alterações da Tabela"):
                    for _, r in df_up.iterrows():
                        q_up = """UPDATE alunos SET nome=%s, data_nascimento=%s, faixa=%s, graus=%s, data_faixa=%s, data_ultimo_grau=%s, nome_responsavel=%s, telefone=%s WHERE id=%s"""
                        executar_query(q_up, (r['Nome'], r['Nascimento'], r['Faixa'], r['Graus'], r['Data Faixa'], r['Data Último Grau'], r['Responsável'], r['Telefone'], r['ID']))
                    st.success("Tabela atualizada com sucesso!")
                    time.sleep(1)
                    st.rerun()

                st.divider()
                st.subheader("⚡ Ações Rápidas")
                c_alu, c_grau, c_del = st.columns([2, 1, 1])
                mapeamento_alunos = {r['Nome']: r['ID'] for index, r in df_e.iterrows()}
                aluno_selecionado = c_alu.selectbox("Selecione o Aluno:", list(mapeamento_alunos.keys()))
                if aluno_selecionado:
                    id_alvo = mapeamento_alunos[aluno_selecionado]
                    if c_grau.button(f"➕ Add Grau"):
                        executar_query("UPDATE alunos SET graus = graus + 1, data_ultimo_grau = CURRENT_DATE WHERE id = %s", (id_alvo,))
                        st.success(f"Grau adicionado para {aluno_selecionado}!")
                        st.rerun()
                    if c_del.button(f"❌ Excluir", type="primary"):
                        executar_query("DELETE FROM alunos WHERE id = %s", (id_alvo,))
                        st.warning(f"Aluno {aluno_selecionado} removido!")
                        st.rerun()

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
                        for id_a in pres: executar_query("INSERT INTO presencas (id_aluno) VALUES (%s)", (id_a,))
                        st.success(f"{len(pres)} presenças registradas com sucesso!")
            else: st.warning("Não há alunos ativos nesta turma.")
        else:
            st.warning("Cadastre turmas em Configurações.")

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
                    st.success(f"{a_sel} transferido para {t_sel}!")
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