import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import date
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="SER Jiu-Jítsu - Sistema Integrado", 
    page_icon="🥋", 
    layout="wide"
)

# --- GERENCIAMENTO DE ESTADO (MEMÓRIA DE NAVEGAÇÃO) ---
# Define onde o usuário começa (login) e se está logado
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 'login'
if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- CONEXÃO COM O BANCO DE DADOS ---
def get_connection():
    try:
        # Tenta conectar usando a URL completa configurada nos Secrets
        if "url" in st.secrets["postgres"]:
            conn = psycopg2.connect(st.secrets["postgres"]["url"])
        else:
            # Fallback para configuração antiga
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

# --- FUNÇÃO PARA EXECUTAR COMANDOS NO BANCO ---
def executar_query(query, params=None, fetch=False):
    conn = get_connection()
    if conn is None:
        st.error("Erro de conexão: Verifique se o PostgreSQL está ligado.")
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
        st.error(f"Erro na execução do banco: {e}")
        return [] if fetch else False

# ==========================================
# TELA 1: LOGIN (PORTA DE ENTRADA)
# ==========================================
def tela_login():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>🥋 SER Jiu-Jítsu Team</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Sistema de Gestão Profissional</p>", unsafe_allow_html=True)
        st.divider()
        
        # Área de Login do Professor
        with st.form("form_login"):
            st.markdown("### 🔒 Acesso do Professor/Admin")
            user = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if entrar:
                # Verifica nos Secrets se o admin confere
                try:
                    if user == st.secrets["admin"]["usuario"] and password == st.secrets["admin"]["senha"]:
                        st.session_state.logado = True
                        st.session_state.pagina_atual = 'sistema'
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                except KeyError:
                    st.error("Erro: Configure [admin] usuario e senha nos Secrets do Streamlit.")

        st.markdown("---")
        
        # Área de Acesso do Aluno
        st.info("É aluno novo? Faça seu cadastro por aqui.")
        if st.button("📝 Fazer Auto-Cadastro (Aluno)", use_container_width=True):
            st.session_state.pagina_atual = 'cadastro_aluno'
            st.rerun()

# ==========================================
# TELA 2: AUTO-CADASTRO (PÚBLICA PARA ALUNOS)
# ==========================================
def tela_cadastro_aluno():
    st.button("⬅️ Voltar para Login", on_click=lambda: st.session_state.update({'pagina_atual': 'login'}))
    
    st.title("📱 Portal do Atleta - Auto-Cadastro")
    st.markdown("Preencha seus dados com atenção. Bem-vindo à equipe!")
    
    with st.form("form_auto_cadastro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome_auto = col1.text_input("Nome Completo *")
        nasc_auto = col1.date_input("Data de Nascimento", value=date(2000, 1, 1))
        
        # Correção visual: inputs alinhados
        col_tel, col_resp = st.columns(2)
        tel_auto = col_tel.text_input("WhatsApp (com DDD) *")
        resp_auto = col_resp.text_input("Nome do Responsável (se menor de idade)")
        
        col3, col4 = st.columns(2)
        faixa_auto = col3.selectbox("Faixa Atual", ["Branca", "Cinza/Branca", "Cinza", "Cinza/Preta", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])
        graus_auto = col4.number_input("Graus na Faixa Atual", 0, 10, 0)
        
        # Busca turmas no banco
        t_auto_db = executar_query("SELECT id, nome_turma FROM turmas;", fetch=True)
        op_t_auto = {t['nome_turma']: t['id'] for t in t_auto_db} if t_auto_db else {}
        turma_auto = st.selectbox("Turma/Horário que irá treinar", list(op_t_auto.keys()) if op_t_auto else ["Nenhuma disponível"])
        
        submitted = st.form_submit_button("✅ Enviar Cadastro", use_container_width=True)
        
        if submitted:
            if nome_auto and tel_auto and turma_auto != "Nenhuma disponível":
                id_t_auto = op_t_auto.get(turma_auto)
                q_auto = """INSERT INTO alunos (nome, data_nascimento, faixa, graus, id_turma, nome_responsavel, telefone, status_aluno, data_faixa, data_ultimo_grau) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Ativo', CURRENT_DATE, CURRENT_DATE)"""
                executar_query(q_auto, (nome_auto, nasc_auto, faixa_auto, graus_auto, id_t_auto, resp_auto, tel_auto))
                st.balloons()
                st.success(f"OSS! Cadastro de {nome_auto} realizado com sucesso! Bem-vindo à SER Jiu-Jítsu.")
                time.sleep(3) # Espera 3 segundos para ler
                st.session_state.pagina_atual = 'login' # Volta pro login
                st.rerun()
            else:
                st.error("Erro: Nome, Telefone e Turma são obrigatórios.")

# ==========================================
# TELA 3: SISTEMA PRINCIPAL (RESTRITA AO ADMIN)
# ==========================================
def sistema_principal():
    # --- SIDEBAR (MENU LATERAL) ---
    with st.sidebar:
        st.header("Painel Admin")
        st.write(f"Logado como: **{st.secrets['admin']['usuario'].upper()}**")
        if st.button("🚪 Sair (Logout)", type="primary"):
            st.session_state.logado = False
            st.session_state.pagina_atual = 'login'
            st.rerun()
    
    st.title("🥋 Painel Administrativo SER Jiu-Jítsu")
    
    # --- NAVEGAÇÃO INTERNA DO SISTEMA ---
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
            
            niver_hoje = executar_query(
                "SELECT nome FROM alunos WHERE EXTRACT(MONTH FROM data_nascimento) = %s AND EXTRACT(DAY FROM data_nascimento) = %s;",
                (hoje.month, hoje.day), fetch=True
            )
        except:
            total_alunos = 0
            niver_hoje = []
            st.warning("Tabelas não encontradas. Verifique as configurações.")

        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Total de Atletas Ativos", total_alunos)
        col_m2.metric("Aniversariantes de Hoje", len(niver_hoje) if niver_hoje else 0)

        st.divider()

        # Alertas de Graduação
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
                anos_grau = (hoje - dt_grau).days // 365

                if alu['faixa'] in ["Branca", "Cinza/Branca", "Cinza", "Cinza/Preta", "Amarela", "Laranja", "Verde"]:
                    if alu['aulas'] >= 8 and meses_faixa >= 6:
                        lista_apto_exame.append({"Nome": alu['nome'], "Faixa": alu['faixa'], "Aulas": alu['aulas']})
                elif alu['faixa'] in ["Azul", "Roxa", "Marrom"]:
                    if meses_grau >= 6:
                        lista_apto_grau.append({"Nome": alu['nome'], "Faixa": alu['faixa'], "Graus Atual": alu['graus']})
                elif alu['faixa'] == "Preta":
                    if (alu['graus'] <= 3 and anos_grau >= 3) or (alu['graus'] >= 4 and anos_grau >= 5):
                        lista_apto_grau.append({"Nome": alu['nome'], "Faixa": alu['faixa'], "Graus Atual": alu['graus']})

        if lista_apto_exame or lista_apto_grau:
            st.subheader("🚨 Alunos Aptos para Graduação")
            if lista_apto_exame:
                st.warning(f"Exame de Faixa: {len(lista_apto_exame)} aluno(s)")
                st.dataframe(pd.DataFrame(lista_apto_exame), use_container_width=True, hide_index=True)
            if lista_apto_grau:
                st.info(f"Novos Graus: {len(lista_apto_grau)} aluno(s)")
                st.dataframe(pd.DataFrame(lista_apto_grau), use_container_width=True, hide_index=True)
        else:
            st.success("Todos os alunos estão com a graduação em dia!")

        st.divider()
        
        # Gráficos e Nivers
        c_niver, c_graf = st.columns([1, 2])
        with c_niver:
            st.subheader("🎂 Aniversariantes")
            if niver_hoje: st.balloons()
            niver_mes = executar_query(
                "SELECT nome, EXTRACT(DAY FROM data_nascimento) as dia FROM alunos WHERE EXTRACT(MONTH FROM data_nascimento) = %s ORDER BY dia;",
                (hoje.month,), fetch=True
            )
            if niver_mes:
                for n in niver_mes: st.write(f"Dia {int(n['dia'])}: {n['nome']}")
            else:
                st.write("Nenhum neste mês.")
        
        with c_graf:
            st.subheader("📊 Distribuição por Faixas")
            dados_f = executar_query("SELECT faixa, COUNT(*) as total FROM alunos GROUP BY faixa;", fetch=True)
            if dados_f:
                df_g = pd.DataFrame(dados_f, columns=['faixa', 'total'])
                ordem_faixas = ["Branca", "Cinza/Branca", "Cinza", "Cinza/Preta", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
                df_g['faixa'] = pd.Categorical(df_g['faixa'], categories=ordem_faixas, ordered=True)
                df_g = df_g.sort_values('faixa')
                st.bar_chart(df_g.set_index('faixa'))

    # --- ABA 2: GESTÃO DE ALUNOS ---
    with tab_gestao:
        st.header("Gerenciamento Administrativo")
        op_g = st.radio("Ação:", ["Listar e Editar", "Cadastrar Novo (Manual)"], horizontal=True)
        
        if op_g == "Cadastrar Novo (Manual)":
            with st.form("cad_novo_admin"):
                c1, c2 = st.columns(2)
                nome = c1.text_input("Nome Completo")
                nasc = c1.date_input("Nascimento", value=date(2010, 1, 1))
                faixa = c1.selectbox("Faixa", ["Branca", "Cinza/Branca", "Cinza", "Cinza/Preta", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])
                graus = c2.number_input("Graus", 0, 10, 0)
                d_faixa = c2.date_input("Data da Faixa Atual")
                d_grau = c2.date_input("Data do Último Grau")
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
            dados = executar_query("SELECT id, nome, faixa, graus, data_faixa, data_ultimo_grau, nome_responsavel, telefone FROM alunos ORDER BY nome", fetch=True)
            if dados:
                df_e = pd.DataFrame(dados, columns=['ID', 'Nome', 'Faixa', 'Graus', 'Data Faixa', 'Data Último Grau', 'Responsável', 'Telefone'])
                df_up = st.data_editor(df_e, use_container_width=True, hide_index=True, key="editor_alunos")
                
                if st.button("💾 Salvar Alterações da Tabela"):
                    for _, r in df_up.iterrows():
                        q_up = """UPDATE alunos SET nome=%s, faixa=%s, graus=%s, data_faixa=%s, data_ultimo_grau=%s, nome_responsavel=%s, telefone=%s WHERE id=%s"""
                        executar_query(q_up, (r['Nome'], r['Faixa'], r['Graus'], r['Data Faixa'], r['Data Último Grau'], r['Responsável'], r['Telefone'], r['ID']))
                    st.success("Tabela atualizada!")
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

# ==========================================
# ROTEADOR DE NAVEGAÇÃO (CÉREBRO DO APP)
# ==========================================
# Aqui decidimos qual tela mostrar baseado no estado atual
if st.session_state.pagina_atual == 'login':
    tela_login()
elif st.session_state.pagina_atual == 'cadastro_aluno':
    tela_cadastro_aluno()
elif st.session_state.pagina_atual == 'sistema':
    # Segurança extra: se não estiver logado, chuta pro login
    if st.session_state.logado:
        sistema_principal()
    else:
        st.session_state.pagina_atual = 'login'
        st.rerun()