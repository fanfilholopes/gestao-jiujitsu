import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import date, datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="SER Jiu-Jítsu - Gestão Profissional", 
    page_icon="🥋", 
    layout="wide"
)

# --- CONEXÃO COM O BANCO DE DADOS ---
def get_connection():
    try:
        # Tenta conectar usando a URL completa configurada nos Secrets
        # Essa é a forma mais robusta para o Supabase no Streamlit Cloud
        if "url" in st.secrets["postgres"]:
            conn = psycopg2.connect(st.secrets["postgres"]["url"])
        else:
            # Fallback caso a pessoa tenha configurado do jeito antigo (host, user, etc)
            conn = psycopg2.connect(
                host=st.secrets["postgres"]["host"],
                database=st.secrets["postgres"]["database"],
                user=st.secrets["postgres"]["user"],
                password=st.secrets["postgres"]["password"],
                port=st.secrets["postgres"]["port"]
            )
        return conn
    except Exception as e:
        # Mostra o erro real na tela para facilitar o debug
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

# --- TÍTULO ---
st.title("🥋 Sistema de Gestão SER Jiu-Jítsu Team")

# --- NAVEGAÇÃO POR ABAS ---
tab_dash, tab_gestao, tab_chamada, tab_auto, tab_regras = st.tabs([
    "📊 Dashboard", "👥 Gestão", "📅 Chamada", "📱 Auto-Cadastro", "⚙️ Configurações"
])

# --- TELA 1: DASHBOARD ---
with tab_dash:
    st.header("Visão Geral")
    hoje = date.today()
    
    # Verifica se a tabela existe antes de contar (evita erro no primeiro load)
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
        st.warning("As tabelas ainda não foram encontradas. Vá em Configurações para iniciar.")

    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Total de Atletas Ativos", total_alunos)
    col_m2.metric("Aniversariantes de Hoje", len(niver_hoje) if niver_hoje else 0)

    st.divider()

    # --- LÓGICA DE ALERTAS ---
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
    
    c_niver, c_graf = st.columns([1, 2])
    with c_niver:
        st.subheader("🎂 Aniversariantes do Mês")
        if niver_hoje: st.balloons()
        niver_mes = executar_query(
            "SELECT nome, EXTRACT(DAY FROM data_nascimento) as dia FROM alunos WHERE EXTRACT(MONTH FROM data_nascimento) = %s ORDER BY dia;",
            (hoje.month,), fetch=True
        )
        if niver_mes:
            for n in niver_mes: st.write(f"Dia {int(n['dia'])}: {n['nome']}")
    
    with c_graf:
        st.subheader("📊 Distribuição por Faixas")
        dados_f = executar_query("SELECT faixa, COUNT(*) as total FROM alunos GROUP BY faixa;", fetch=True)
        if dados_f:
            df_g = pd.DataFrame(dados_f, columns=['faixa', 'total'])
            ordem_faixas = ["Branca", "Cinza/Branca", "Cinza", "Cinza/Preta", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
            df_g['faixa'] = pd.Categorical(df_g['faixa'], categories=ordem_faixas, ordered=True)
            df_g = df_g.sort_values('faixa')
            st.bar_chart(df_g.set_index('faixa'))

# --- TELA 2: GESTÃO DE ALUNOS ---
with tab_gestao:
    st.header("Gerenciamento Administrativo")
    op_g = st.radio("Ação:", ["Listar e Editar", "Cadastrar Novo"], horizontal=True)
    
    if op_g == "Cadastrar Novo":
        with st.form("cad_novo"):
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
            df_up = st.data_editor(df_e, use_container_width=True, hide_index=True)
            
            if st.button("💾 Salvar Alterações da Tabela"):
                for _, r in df_up.iterrows():
                    q_up = """UPDATE alunos SET nome=%s, faixa=%s, graus=%s, data_faixa=%s, data_ultimo_grau=%s, nome_responsavel=%s, telefone=%s WHERE id=%s"""
                    executar_query(q_up, (r['Nome'], r['Faixa'], r['Graus'], r['Data Faixa'], r['Data Último Grau'], r['Responsável'], r['Telefone'], r['ID']))
                st.success("Atualizado!")
                st.rerun()

            st.divider()
            st.subheader("⚡ Ações Rápidas")
            c_alu, c_grau, c_del = st.columns([2, 1, 1])
            mapeamento_alunos = {r['Nome']: r['ID'] for index, r in df_e.iterrows()}
            aluno_selecionado = c_alu.selectbox("Selecione o Aluno para Ação Rápida:", list(mapeamento_alunos.keys()))
            
            if aluno_selecionado:
                id_alvo = mapeamento_alunos[aluno_selecionado]
                if c_grau.button(f"➕ Add Grau em {aluno_selecionado}"):
                    executar_query("UPDATE alunos SET graus = graus + 1, data_ultimo_grau = CURRENT_DATE WHERE id = %s", (id_alvo,))
                    st.success(f"Grau adicionado para {aluno_selecionado}!")
                    st.rerun()
                if c_del.button(f"❌ Excluir {aluno_selecionado}", type="primary"):
                    executar_query("DELETE FROM alunos WHERE id = %s", (id_alvo,))
                    st.warning(f"Aluno {aluno_selecionado} removido!")
                    st.rerun()

# --- TELA 3: CHAMADA ---
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
                for a in als:
                    if st.checkbox(a['nome'], key=f"p_{a['id']}"): pres.append(a['id'])
                if st.form_submit_button("Registrar Presenças"):
                    for id_a in pres: executar_query("INSERT INTO presencas (id_aluno) VALUES (%s)", (id_a,))
                    st.success("Presenças registradas com sucesso!")
        else: st.warning("Não há alunos ativos nesta turma.")

# --- TELA 4: AUTO-CADASTRO (PARA O ALUNO) ---
with tab_auto:
    st.header("📱 Portal do Atleta - Auto-Cadastro")
    st.info("Formulário simplificado para novos alunos preencherem via celular/tablet.")
    
    with st.form("form_auto_cadastro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome_auto = col1.text_input("Nome Completo")
        nasc_auto = col1.date_input("Data de Nascimento", value=date(2000, 1, 1))
        faixa_auto = col1.selectbox("Faixa Atual", ["Branca", "Cinza/Branca", "Cinza", "Cinza/Preta", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])
        
        graus_auto = col2.number_input("Graus na Faixa Atual", 0, 10, 0)
        tel_auto = col2.text_input("WhatsApp (com DDD)")
        resp_auto = col2.text_input("Nome do Responsável (se menor de idade)")
        
        t_auto_db = executar_query("SELECT id, nome_turma FROM turmas;", fetch=True)
        op_t_auto = {t['nome_turma']: t['id'] for t in t_auto_db} if t_auto_db else {}
        turma_auto = st.selectbox("Turma/Horário que irá treinar", list(op_t_auto.keys()) if op_t_auto else ["Nenhuma disponível"])
        
        if st.form_submit_button("Enviar Cadastro"):
            if nome_auto and turma_auto != "Nenhuma disponível":
                id_t_auto = op_t_auto.get(turma_auto)
                q_auto = """INSERT INTO alunos (nome, data_nascimento, faixa, graus, id_turma, nome_responsavel, telefone, status_aluno, data_faixa, data_ultimo_grau) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Ativo', CURRENT_DATE, CURRENT_DATE)"""
                executar_query(q_auto, (nome_auto, nasc_auto, faixa_auto, graus_auto, id_t_auto, resp_auto, tel_auto))
                st.success("OSS! Cadastro realizado. Bem-vindo à SER Jiu-Jítsu Team!")
            else:
                st.error("Erro: Nome e Turma são campos obrigatórios.")

# --- TELA 5: CONFIGURAÇÕES ---
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