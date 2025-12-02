import streamlit as st
import pandas as pd
import datetime
import hashlib
import time
from datetime import timedelta
import sqlite3
import os

# Configuração da página
st.set_page_config(
    page_title="SCPE - Sistema de Controle de Projetos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sistema de autenticação
def init_db():
    """Inicializa o banco de dados SQLite"""
    conn = sqlite3.connect('scpe.db')
    c = conn.cursor()
    
    # Verificar se a tabela users existe e tem as colunas corretas
    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    
    # Se a tabela não existe ou não tem as colunas corretas, recriar
    if not columns or 'username' not in columns:
        # Drop tables if they exist
        c.execute("DROP TABLE IF EXISTS messages")
        c.execute("DROP TABLE IF EXISTS tasks")
        c.execute("DROP TABLE IF EXISTS project_members")
        c.execute("DROP TABLE IF EXISTS projects")
        c.execute("DROP TABLE IF EXISTS users")
        
        # Tabela de usuários
        c.execute('''CREATE TABLE users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT UNIQUE,
                      password TEXT,
                      email TEXT,
                      role TEXT,
                      full_name TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        # Tabela de projetos
        c.execute('''CREATE TABLE projects
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT,
                      description TEXT,
                      client TEXT,
                      budget REAL,
                      total_deadline DATE,
                      manager_id INTEGER,
                      status TEXT DEFAULT 'ativo',
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        # Tabela de associação usuários-projetos
        c.execute('''CREATE TABLE project_members
                     (project_id INTEGER,
                      user_id INTEGER,
                      role TEXT,
                      assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      PRIMARY KEY (project_id, user_id))''')
        
        # Tabela de tarefas
        c.execute('''CREATE TABLE tasks
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      project_id INTEGER,
                      description TEXT,
                      start_date DATE,
                      end_date DATE,
                      status TEXT,
                      assigned_to INTEGER,
                      dependency_id INTEGER,
                      hours_worked REAL DEFAULT 0,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        # Tabela de mensagens
        c.execute('''CREATE TABLE messages
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      project_id INTEGER,
                      from_user INTEGER,
                      message TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Criptografa a senha"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password):
    """Autentica o usuário"""
    conn = sqlite3.connect('scpe.db')
    c = conn.cursor()
    hashed_password = hash_password(password)
    
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
              (username, hashed_password))
    user = c.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user[0],
            'username': user[1],
            'role': user[4],
            'full_name': user[5]
        }
    return None

def register_user(username, password, email, role, full_name):
    """Registra um novo usuário"""
    conn = sqlite3.connect('scpe.db')
    c = conn.cursor()
    hashed_password = hash_password(password)
    
    try:
        c.execute("INSERT INTO users (username, password, email, role, full_name) VALUES (?, ?, ?, ?, ?)",
                  (username, hashed_password, email, role, full_name))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

# Funções de gerenciamento de dados
def get_projects(user_id=None):
    """Obtém projetos do banco de dados"""
    conn = sqlite3.connect('scpe.db')
    
    if user_id:
        query = """SELECT p.*, u.full_name as manager_name 
                   FROM projects p 
                   LEFT JOIN users u ON p.manager_id = u.id
                   WHERE p.manager_id = ? OR p.id IN (
                       SELECT project_id FROM project_members WHERE user_id = ?
                   )"""
        df = pd.read_sql_query(query, conn, params=(user_id, user_id))
    else:
        query = """SELECT p.*, u.full_name as manager_name 
                   FROM projects p 
                   LEFT JOIN users u ON p.manager_id = u.id"""
        df = pd.read_sql_query(query, conn)
    
    conn.close()
    return df

def get_project_members(project_id):
    """Obtém membros de um projeto - VERSÃO CORRIGIDA"""
    conn = sqlite3.connect('scpe.db')
    
    try:
        # Query corrigida - mais robusta e clara
        query = """
        SELECT 
            u.id,
            u.full_name, 
            u.role as user_role,
            pm.role as project_role
        FROM project_members pm
        JOIN users u ON pm.user_id = u.id
        WHERE pm.project_id = ?
        ORDER BY u.full_name
        """
        
        df = pd.read_sql_query(query, conn, params=(project_id,))
        return df
        
    except Exception as e:
        st.error(f"Erro ao buscar membros do projeto: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def is_user_in_project(project_id, user_id):
    """Verifica se um usuário já está no projeto"""
    conn = sqlite3.connect('scpe.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ?", 
              (project_id, user_id))
    result = c.fetchone() is not None
    conn.close()
    return result

def get_tasks(project_id=None):
    """Obtém tarefas do banco de dados"""
    conn = sqlite3.connect('scpe.db')
    
    if project_id:
        query = """SELECT t.*, u.full_name as assigned_name, p.name as project_name
                   FROM tasks t
                   LEFT JOIN users u ON t.assigned_to = u.id
                   LEFT JOIN projects p ON t.project_id = p.id
                   WHERE t.project_id = ?"""
        df = pd.read_sql_query(query, conn, params=(project_id,))
    else:
        query = """SELECT t.*, u.full_name as assigned_name, p.name as project_name
                   FROM tasks t
                   LEFT JOIN users u ON t.assigned_to = u.id
                   LEFT JOIN projects p ON t.project_id = p.id"""
        df = pd.read_sql_query(query, conn)
    
    conn.close()
    return df

def get_users():
    """Obtém todos os usuários"""
    conn = sqlite3.connect('scpe.db')
    df = pd.read_sql_query("SELECT id, username, full_name, role FROM users", conn)
    conn.close()
    return df

def get_user_projects(user_id):
    """Obtém projetos de um usuário específico"""
    conn = sqlite3.connect('scpe.db')
    query = """SELECT p.*, u.full_name as manager_name 
               FROM projects p 
               LEFT JOIN users u ON p.manager_id = u.id
               WHERE p.id IN (
                   SELECT project_id FROM project_members WHERE user_id = ?
               ) OR p.manager_id = ?"""
    df = pd.read_sql_query(query, conn, params=(user_id, user_id))
    conn.close()
    return df
# show

def debug_database_state():
    """Debug completo do estado do banco de dados"""
    conn = sqlite3.connect('scpe.db')
    
    st.write("### 🔍 DIAGNÓSTICO DO BANCO DE DADOS")
    
    # 1. Verificar todas as tabelas
    st.write("**1. Todas as tabelas no banco:**")
    tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
    st.write(tables)
    
    # 2. Verificar estrutura de project_members
    st.write("**2. Estrutura de project_members:**")
    try:
        structure = pd.read_sql_query("PRAGMA table_info(project_members)", conn)
        st.write(structure)
    except:
        st.error("❌ Tabela project_members não existe!")
    
    # 3. Verificar todos os dados em project_members
    st.write("**3. Todos os dados em project_members:**")
    try:
        all_data = pd.read_sql_query("SELECT * FROM project_members", conn)
        st.write(all_data)
    except Exception as e:
        st.error(f"❌ Erro ao acessar project_members: {e}")
    
    # 4. Verificar usuários
    st.write("**4. Usuários no sistema:**")
    users = pd.read_sql_query("SELECT id, full_name FROM users", conn)
    st.write(users)
    
    # 5. Verificar projetos
    st.write("**5. Projetos no sistema:**")
    projects = pd.read_sql_query("SELECT id, name FROM projects", conn)
    st.write(projects)
    
    conn.close()

def emergency_recreate_project_members():
    """RECRIA COMPLETAMENTE a tabela project_members"""
    st.write("### 🚨 RECRIAÇÃO DE EMERGÊNCIA - project_members")
    
    conn = sqlite3.connect('scpe.db')
    c = conn.cursor()
    
    try:
        # 1. Criar tabela temporária para backup
        c.execute("DROP TABLE IF EXISTS project_members_backup")
        c.execute("CREATE TABLE project_members_backup AS SELECT * FROM project_members")
        
        # 2. Dropar e recriar a tabela principal
        c.execute("DROP TABLE IF EXISTS project_members")
        c.execute('''CREATE TABLE project_members
                     (project_id INTEGER,
                      user_id INTEGER,
                      role TEXT,
                      assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      PRIMARY KEY (project_id, user_id))''')
        
        # 3. Restaurar dados do backup
        c.execute("INSERT INTO project_members SELECT * FROM project_members_backup")
        
        # 4. Limpar tabela temporária
        c.execute("DROP TABLE IF EXISTS project_members_backup")
        
        conn.commit()
        
        # 5. Verificar resultado
        c.execute("SELECT COUNT(*) FROM project_members")
        new_count = c.fetchone()[0]
        
        st.success(f"✅ **RECRIAÇÃO BEM-SUCEDIDA!**")
        st.success(f"✅ Tabela project_members recriada com {new_count} registros")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Erro na recriação: {e}")
        # Tentativa alternativa mais simples
        try:
            c.execute("DROP TABLE IF EXISTS project_members")
            c.execute('''CREATE TABLE project_members
                         (project_id INTEGER,
                          user_id INTEGER,
                          role TEXT,
                          assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          PRIMARY KEY (project_id, user_id))''')
            conn.commit()
            st.success("✅ Tabela recriada (vazia)")
            return True
        except Exception as e2:
            st.error(f"❌ Falha crítica: {e2}")
            return False
    finally:
        conn.close()

# Interface principal
def main():
    # Inicializar banco de dados
    init_db()
    
    # Sistema de autenticação
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if st.session_state.user is None:
        show_login_page()
    else:
        show_main_application()

def show_login_page():
    """Página de login/registro"""
    st.title("📊 SCPE - Sistema de Controle de Projetos")
    
    tab1, tab2 = st.tabs(["Login", "Registrar"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.user = user
                        st.success(f"Bem-vindo, {user['full_name']}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha inválidos")
                else:
                    st.error("Preencha todos os campos")
    
    with tab2:
        with st.form("register_form"):
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Nome completo*")
                username = st.text_input("Usuário*")
                password = st.text_input("Senha*", type="password")
            with col2:
                email = st.text_input("E-mail*")
                role = st.selectbox("Cargo*", ["membro", "gerente"])
            
            submit = st.form_submit_button("Registrar")
            
            if submit:
                if all([username, password, email, full_name]):
                    if register_user(username, password, email, role, full_name):
                        st.success("Usuário registrado com sucesso! Faça login.")
                    else:
                        st.error("Erro ao registrar usuário. Nome de usuário pode já existir.")
                else:
                    st.error("Preencha todos os campos obrigatórios (*)")

def show_main_application():
    """Aplicação principal após login"""
    st.sidebar.title(f"👋 Olá, {st.session_state.user['full_name']}")
    st.sidebar.write(f"**Cargo:** {st.session_state.user['role']}")
    
    # Menu lateral
    menu_options = [
        "📈 Dashboard",
        "📋 Projetos", 
        "✅ Tarefas",
        "👥 Equipes",
        "💬 Comunicação",
        "📊 Relatórios"
    ]
    
    if st.session_state.user['role'] == 'gerente':
        menu_options.append("⚙️ Administração")
    
    choice = st.sidebar.selectbox("Navegação", menu_options)
    
    # Logout
    if st.sidebar.button("🚪 Sair"):
        st.session_state.user = None
        st.rerun()
    
    # Navegação entre páginas
    if choice == "📈 Dashboard":
        show_dashboard()
    elif choice == "📋 Projetos":
        show_projects()
    elif choice == "✅ Tarefas":
        show_tasks()
    elif choice == "👥 Equipes":
        show_teams()
    elif choice == "💬 Comunicação":
        show_communication()
    elif choice == "📊 Relatórios":
        show_reports()
    elif choice == "⚙️ Administração" and st.session_state.user['role'] == 'gerente':
        show_admin()

def show_dashboard():
    """Dashboard principal"""
    st.title("📈 Dashboard")
    
    # Obter dados
    projects = get_projects(st.session_state.user['id'])
    tasks = get_tasks()
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_projects = len(projects)
        st.metric("Total de Projetos", total_projects)
    
    with col2:
        active_projects = len(projects[projects['status'] == 'ativo'])
        st.metric("Projetos Ativos", active_projects)
    
    with col3:
        total_tasks = len(tasks)
        st.metric("Total de Tarefas", total_tasks)
    
    with col4:
        completed_tasks = len(tasks[tasks['status'] == 'concluída'])
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        st.metric("Taxa de Conclusão", f"{completion_rate:.1f}%")
    
    # Gráficos e visualizações
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Status dos Projetos")
        if not projects.empty:
            status_counts = projects['status'].value_counts()
            st.bar_chart(status_counts)
        else:
            st.info("Nenhum projeto cadastrado")
    
    with col2:
        st.subheader("Status das Tarefas")
        if not tasks.empty:
            task_status_counts = tasks['status'].value_counts()
            st.bar_chart(task_status_counts)
        else:
            st.info("Nenhuma tarefa cadastrada")
    
    # Tarefas próximas do prazo
    st.subheader("📅 Tarefas Próximas do Prazo")
    if not tasks.empty:
        tasks['end_date'] = pd.to_datetime(tasks['end_date'])
        upcoming_tasks = tasks[
            (tasks['status'] != 'concluída') & 
            (tasks['end_date'] <= datetime.datetime.now() + timedelta(days=7))
        ]
        
        if not upcoming_tasks.empty:
            for _, task in upcoming_tasks.iterrows():
                days_left = (task['end_date'] - datetime.datetime.now()).days
                st.warning(
                    f"**{task['project_name']}**: {task['description']} - "
                    f"Vence em {days_left} dias - Responsável: {task['assigned_name']}"
                )
        else:
            st.success("Nenhuma tarefa próxima do prazo!")
    else:
        st.info("Nenhuma tarefa cadastrada")

def show_projects():
    """Gerenciamento de projetos"""
    st.title("📋 Gerenciamento de Projetos")
    
    if st.session_state.user['role'] == 'gerente':
        # Formulário para adicionar novo projeto
        with st.expander("➕ Adicionar Novo Projeto"):
            with st.form("project_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    name = st.text_input("Nome do Projeto*")
                    description = st.text_area("Descrição")
                    client = st.text_input("Cliente*")
                
                with col2:
                    budget = st.number_input("Orçamento (R$)", min_value=0.0, format="%.2f")
                    total_deadline = st.date_input("Prazo Final*")
                
                submit = st.form_submit_button("Criar Projeto")
                
                if submit:
                    if name and client and total_deadline:
                        conn = sqlite3.connect('scpe.db')
                        c = conn.cursor()
                        c.execute("""INSERT INTO projects 
                                    (name, description, client, budget, total_deadline, manager_id) 
                                    VALUES (?, ?, ?, ?, ?, ?)""",
                                (name, description, client, budget, total_deadline, st.session_state.user['id']))
                        conn.commit()
                        conn.close()
                        st.success("Projeto criado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Preencha os campos obrigatórios (*)")
    
    # Lista de projetos
    st.subheader("📂 Projetos")
    projects = get_projects(st.session_state.user['id'])
    
    if not projects.empty:
        for _, project in projects.iterrows():
            with st.expander(f"**{project['name']}** - {project['client']}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Descrição:** {project['description']}")
                    st.write(f"**Gerente:** {project['manager_name']}")
                    st.write(f"**Status:** {project['status']}")
                
                with col2:
                    st.write(f"**Orçamento:** R$ {project['budget']:,.2f}")
                    st.write(f"**Prazo:** {project['total_deadline']}")
                    st.write(f"**Criado em:** {project['created_at']}")
                
                with col3:
                    # Estatísticas do projeto
                    project_tasks = get_tasks(project['id'])
                    total_tasks = len(project_tasks)
                    completed_tasks = len(project_tasks[project_tasks['status'] == 'concluída'])
                    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                    
                    st.write(f"**Progresso:** {completion_rate:.1f}%")
                    st.progress(completion_rate / 100)
                    
                    # Ações do projeto
                    if st.session_state.user['role'] == 'gerente':
                        if st.button(f"Gerenciar Equipe", key=f"team_{project['id']}"):
                            st.session_state.manage_team_project_id = project['id']
                            st.rerun()
    
    # Gerenciar equipe se um projeto foi selecionado
    if 'manage_team_project_id' in st.session_state:
        manage_project_team(st.session_state.manage_team_project_id)

def manage_project_team(project_id):
    """Gerenciar equipe do projeto"""
    st.subheader("👥 Gerenciar Equipe do Projeto")
    
    # Obter informações do projeto
    projects = get_projects()
    project = projects[projects['id'] == project_id].iloc[0]
    st.write(f"**Projeto:** {project['name']} (ID: {project_id})")
    
    users = get_users()
    
    # DIAGNÓSTICO
    st.write("---")
    debug_database_state()
    
    # SOLUÇÃO DE EMERGÊNCIA
    st.write("---")
    st.write("### 🚨 SOLUÇÃO DE EMERGÊNCIA")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 RECRIAR TABELA COMPLETA", type="primary"):
            if emergency_recreate_project_members():
                time.sleep(2)
                st.rerun()
    
    with col2:
        if st.button("🧹 LIMPAR E RECRIAR"):
            conn = sqlite3.connect('scpe.db')
            c = conn.cursor()
            c.execute("DROP TABLE IF EXISTS project_members")
            c.execute('''CREATE TABLE project_members
                         (project_id INTEGER,
                          user_id INTEGER,
                          role TEXT,
                          assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          PRIMARY KEY (project_id, user_id))''')
            conn.commit()
            conn.close()
            st.success("✅ Tabela limpa e recriada do zero!")
            st.rerun()
    
    # ADICIONAR MEMBRO
    st.write("---")
    st.write("### ➕ Adicionar Membro à Equipe")
    
    with st.form("add_member_form"):
        user_to_add = st.selectbox("Selecionar Usuário", users['full_name'].tolist())
        role = st.selectbox("Função no Projeto", ["Desenvolvedor", "Designer", "Analista", "Testador"])
        
        if st.form_submit_button("🎯 ADICIONAR MEMBRO"):
            user_id = users[users['full_name'] == user_to_add]['id'].iloc[0]
            
            try:
                conn = sqlite3.connect('scpe.db')
                c = conn.cursor()
                
                # Inserção direta
                c.execute(
                    "INSERT INTO project_members (project_id, user_id, role) VALUES (?, ?, ?)",
                    (project_id, user_id, role)
                )
                
                conn.commit()
                
                # Verificação imediata
                c.execute("SELECT * FROM project_members WHERE project_id = ? AND user_id = ?", 
                         (project_id, user_id))
                result = c.fetchone()
                
                conn.close()
                
                if result:
                    st.success(f"✅ **SUCESSO!** {user_to_add} adicionado à equipe!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("❌ **FALHA:** Inserção não funcionou!")
                    
            except sqlite3.IntegrityError:
                st.error(f"❌ {user_to_add} já é membro deste projeto!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
    
    # VERIFICAÇÃO DOS MEMBROS
    st.write("---")
    st.write("### 👥 Membros da Equipe")
    
    # Busca direta do banco
    conn = sqlite3.connect('scpe.db')
    try:
        direct_query = "SELECT * FROM project_members WHERE project_id = ?"
        members_data = pd.read_sql_query(direct_query, conn, params=(project_id,))
        
        if not members_data.empty:
            st.success(f"🎉 **MEMBROS ENCONTRADOS:** {len(members_data)}")
            
            # Buscar nomes dos usuários
            user_ids = members_data['user_id'].tolist()
            users_query = f"SELECT id, full_name FROM users WHERE id IN ({','.join(['?']*len(user_ids))})"
            users_info = pd.read_sql_query(users_query, conn, params=user_ids)
            
            # Juntar informações
            members_display = members_data.merge(users_info, left_on='user_id', right_on='id')
            
            for _, member in members_display.iterrows():
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.write(f"**{member['full_name']}**")
                
                with col2:
                    st.write(f"Função: {member['role']}")
                
                with col3:
                    if st.button("Remover", key=f"remove_{member['user_id']}"):
                        conn2 = sqlite3.connect('scpe.db')
                        c2 = conn2.cursor()
                        c2.execute("DELETE FROM project_members WHERE project_id = ? AND user_id = ?",
                                 (project_id, member['user_id']))
                        conn2.commit()
                        conn2.close()
                        st.success(f"✅ {member['full_name']} removido!")
                        time.sleep(2)
                        st.rerun()
        else:
            st.info("📭 Nenhum membro encontrado")
            
    except Exception as e:
        st.error(f"❌ Erro na verificação: {str(e)}")
    finally:
        conn.close()
    
    # BOTÃO PARA VOLTAR
    st.write("---")
    if st.button("← Voltar para Projetos"):
        if 'manage_team_project_id' in st.session_state:
            del st.session_state.manage_team_project_id
        st.rerun()

def show_teams():
    """Gerenciamento de equipes - VERSÃO CORRIGIDA"""
    st.title("👥 Gerenciamento de Equipes")
    
    # Obter projetos onde o usuário atual é membro
    user_projects = get_user_projects(st.session_state.user['id'])
    
    if not user_projects.empty:
        st.subheader("📋 Meus Projetos e Equipes")
        
        for _, project in user_projects.iterrows():
            with st.expander(f"🏢 {project['name']} - Equipe Completa"):
                # Obter todos os membros do projeto usando a função corrigida
                members = get_project_members(project['id'])
                
                if not members.empty:
                    st.write(f"**Total de membros:** {len(members)}")
                    
                    # Exibir informações do gerente
                    st.write("### 👑 Gerente do Projeto")
                    st.write(f"**{project['manager_name']}** (Gerente)")
                    
                    # Exibir outros membros da equipe
                    other_members = members[members['full_name'] != project['manager_name']]
                    
                    if not other_members.empty:
                        st.write("### 👥 Membros da Equipe")
                        for _, member in other_members.iterrows():
                            col1, col2, col3 = st.columns([3, 2, 2])
                            
                            with col1:
                                st.write(f"**{member['full_name']}**")
                            
                            with col2:
                                st.write(f"Cargo: {member['user_role']}")
                            
                            with col3:
                                st.write(f"Função: {member['project_role']}")
                    else:
                        st.info("Não há outros membros na equipe além do gerente")
                else:
                    st.info("Nenhum membro na equipe deste projeto")
                    
                    # DEBUG: Mostrar por que não está encontrando membros
                    st.write("---")
                    st.write("**🔍 DEBUG:** Verificando dados no banco...")
                    
                    conn = sqlite3.connect('scpe.db')
                    try:
                        # Verificar se há membros na tabela project_members
                        check_query = "SELECT * FROM project_members WHERE project_id = ?"
                        check_data = pd.read_sql_query(check_query, conn, params=(project['id'],))
                        
                        if not check_data.empty:
                            st.write("**Dados encontrados em project_members:**")
                            st.write(check_data)
                            
                            # Verificar usuários correspondentes
                            user_ids = check_data['user_id'].tolist()
                            if user_ids:
                                users_query = f"SELECT id, full_name FROM users WHERE id IN ({','.join(['?']*len(user_ids))})"
                                users_data = pd.read_sql_query(users_query, conn, params=user_ids)
                                st.write("**Usuários correspondentes:**")
                                st.write(users_data)
                        else:
                            st.write("**Nenhum dado encontrado em project_members para este projeto**")
                    except Exception as e:
                        st.error(f"Erro no debug: {e}")
                    finally:
                        conn.close()
    else:
        st.info("Você não está em nenhum projeto como membro da equipe")

def show_tasks():
    """Gerenciamento de tarefas"""
    st.title("✅ Gerenciamento de Tarefas")
    
    # Formulário para adicionar tarefa
    with st.expander("➕ Adicionar Nova Tarefa"):
        projects = get_projects(st.session_state.user['id'])
        
        if not projects.empty:
            with st.form("task_form"):
                # Selecionar projeto
                project_options = {row['name']: row['id'] for _, row in projects.iterrows()}
                selected_project_name = st.selectbox("Projeto*", list(project_options.keys()))
                project_id = project_options[selected_project_name]
                
                description = st.text_input("Descrição da Tarefa*")
                
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Data de Início*")
                with col2:
                    end_date = st.date_input("Data de Término*")
                
                status = st.selectbox("Status*", ["pendente", "em andamento", "concluída"])
                hours_worked = st.number_input("Horas Trabalhadas", min_value=0.0, value=0.0, step=0.5)
                
                # Usar o usuário atual como responsável
                assigned_to = st.session_state.user['id']
                
                if st.form_submit_button("🎯 Criar Tarefa"):
                    if not all([description, start_date, end_date]):
                        st.error("❌ Preencha todos os campos obrigatórios")
                    elif start_date > end_date:
                        st.error("❌ Data de início não pode ser depois do término")
                    else:
                        try:
                            conn = sqlite3.connect('scpe.db')
                            c = conn.cursor()
                            c.execute("""INSERT INTO tasks 
                                        (project_id, description, start_date, end_date, status, assigned_to, hours_worked)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                    (project_id, description, start_date, end_date, status, assigned_to, hours_worked))
                            conn.commit()
                            conn.close()
                            st.success("✅ Tarefa criada com sucesso!")
                            time.sleep(2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao criar tarefa: {str(e)}")
        else:
            st.warning("⚠️ Você precisa estar em um projeto para criar tarefas")
    
    # Lista de tarefas
    st.subheader("📝 Lista de Tarefas")
    tasks = get_tasks()
    
    if not tasks.empty:
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox("Filtrar por Status", 
                                       ["Todos", "pendente", "em andamento", "concluída"])
        
        with col2:
            project_filter = st.selectbox("Filtrar por Projeto",
                                        ["Todos"] + tasks['project_name'].unique().tolist())
        
        with col3:
            user_filter = st.selectbox("Filtrar por Responsável",
                                     ["Todos"] + tasks['assigned_name'].unique().tolist())
        
        # Aplicar filtros
        filtered_tasks = tasks.copy()
        
        if status_filter != "Todos":
            filtered_tasks = filtered_tasks[filtered_tasks['status'] == status_filter]
        
        if project_filter != "Todos":
            filtered_tasks = filtered_tasks[filtered_tasks['project_name'] == project_filter]
        
        if user_filter != "Todos":
            filtered_tasks = filtered_tasks[filtered_tasks['assigned_name'] == user_filter]
        
        # Exibir tarefas
        st.write(f"**Total de tarefas encontradas:** {len(filtered_tasks)}")
        
        for _, task in filtered_tasks.iterrows():
            status_color = {
                "pendente": "🔴",
                "em andamento": "🟡", 
                "concluída": "🟢"
            }
            
            with st.expander(f"{status_color[task['status']]} {task['description']} - {task['project_name']}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Projeto:** {task['project_name']}")
                    st.write(f"**Responsável:** {task['assigned_name']}")
                    st.write(f"**Status:** {task['status']}")
                
                with col2:
                    st.write(f"**Início:** {task['start_date']}")
                    st.write(f"**Término:** {task['end_date']}")
                    st.write(f"**Horas Trabalhadas:** {task['hours_worked']}")
                
                with col3:
                    # Atualizar status
                    new_status = st.selectbox("Atualizar Status", 
                                            ["pendente", "em andamento", "concluída"],
                                            index=["pendente", "em andamento", "concluída"].index(task['status']),
                                            key=f"status_{task['id']}")
                    
                    new_hours = st.number_input("Horas Trabalhadas", 
                                              value=float(task['hours_worked']),
                                              key=f"hours_{task['id']}")
                    
                    if st.button("Atualizar", key=f"update_{task['id']}"):
                        try:
                            conn = sqlite3.connect('scpe.db')
                            c = conn.cursor()
                            c.execute("UPDATE tasks SET status = ?, hours_worked = ? WHERE id = ?",
                                     (new_status, new_hours, task['id']))
                            conn.commit()
                            conn.close()
                            st.success("✅ Tarefa atualizada!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao atualizar tarefa: {str(e)}")
    else:
        st.info("📭 Nenhuma tarefa encontrada")

def show_communication():
    """Sistema de comunicação"""
    st.title("💬 Comunicação")
    
    projects = get_projects(st.session_state.user['id'])
    
    if not projects.empty:
        project_options = {row['name']: row['id'] for _, row in projects.iterrows()}
        selected_project_name = st.selectbox("Selecionar Projeto", list(project_options.keys()))
        selected_project = project_options[selected_project_name]
        
        # Enviar mensagem
        with st.form("message_form"):
            message = st.text_area("Mensagem")
            if st.form_submit_button("Enviar Mensagem"):
                if message:
                    conn = sqlite3.connect('scpe.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO messages (project_id, from_user, message) VALUES (?, ?, ?)",
                             (selected_project, st.session_state.user['id'], message))
                    conn.commit()
                    conn.close()
                    st.success("Mensagem enviada!")
                    st.rerun()
                else:
                    st.error("Digite uma mensagem")
        
        # Histórico de mensagens
        st.subheader("📨 Histórico de Mensagens")
        conn = sqlite3.connect('scpe.db')
        query = """SELECT m.*, u.full_name as from_user_name, p.name as project_name
                   FROM messages m
                   JOIN users u ON m.from_user = u.id
                   JOIN projects p ON m.project_id = p.id
                   WHERE m.project_id = ?
                   ORDER BY m.created_at DESC"""
        messages = pd.read_sql_query(query, conn, params=(selected_project,))
        conn.close()
        
        if not messages.empty:
            for _, msg in messages.iterrows():
                st.write(f"**{msg['from_user_name']}** ({msg['created_at']}):")
                st.write(f"{msg['message']}")
                st.divider()
        else:
            st.info("Nenhuma mensagem neste projeto")
    else:
        st.info("Você não está em nenhum projeto")

def show_reports():
    """Relatórios e análises"""
    st.title("📊 Relatórios e Análises")
    
    projects = get_projects(st.session_state.user['id'])
    
    if not projects.empty:
        project_options = {row['name']: row['id'] for _, row in projects.iterrows()}
        selected_project_name = st.selectbox("Selecionar Projeto para Relatório", list(project_options.keys()))
        selected_project = project_options[selected_project_name]
        
        # Estatísticas do projeto
        st.subheader("📈 Estatísticas do Projeto")
        
        tasks = get_tasks(selected_project)
        members = get_project_members(selected_project)
        project = projects[projects['id'] == selected_project].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_tasks = len(tasks)
            st.metric("Total de Tarefas", total_tasks)
        
        with col2:
            completed_tasks = len(tasks[tasks['status'] == 'concluída'])
            st.metric("Tarefas Concluídas", completed_tasks)
        
        with col3:
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            st.metric("Taxa de Conclusão", f"{completion_rate:.1f}%")
        
        with col4:
            total_hours = tasks['hours_worked'].sum()
            st.metric("Total de Horas", f"{total_hours:.1f}")
        
        # Gráfico de status das tarefas
        st.subheader("📊 Distribuição de Status das Tarefas")
        if not tasks.empty:
            status_counts = tasks['status'].value_counts()
            st.bar_chart(status_counts)
        else:
            st.info("Nenhuma tarefa para exibir")
        
        # Tarefas por membro
        st.subheader("👥 Tarefas por Membro da Equipe")
        if not tasks.empty and not members.empty:
            member_tasks = []
            for _, member in members.iterrows():
                member_task_count = len(tasks[tasks['assigned_to'] == member['id']])
                member_completed = len(tasks[(tasks['assigned_to'] == member['id']) & 
                                           (tasks['status'] == 'concluída')])
                member_tasks.append({
                    'Membro': member['full_name'],
                    'Total Tarefas': member_task_count,
                    'Tarefas Concluídas': member_completed
                })
            
            member_df = pd.DataFrame(member_tasks)
            st.dataframe(member_df, use_container_width=True)
        
        # Exportar relatório
        st.subheader("📤 Exportar Relatório")
        if st.button("Gerar Relatório em CSV"):
            # Criar relatório consolidado
            report_data = {
                'Projeto': [project['name']],
                'Cliente': [project['client']],
                'Orçamento': [project['budget']],
                'Prazo': [project['total_deadline']],
                'Total Tarefas': [total_tasks],
                'Tarefas Concluídas': [completed_tasks],
                'Taxa Conclusão': [completion_rate],
                'Total Horas': [total_hours]
            }
            
            report_df = pd.DataFrame(report_data)
            csv = report_df.to_csv(index=False)
            
            st.download_button(
                label="📥 Baixar Relatório CSV",
                data=csv,
                file_name=f"relatorio_{project['name']}.csv",
                mime="text/csv"
            )
    else:
        st.info("Você não está em nenhum projeto")

def show_admin():
    """Painel administrativo para gerentes"""
    st.title("⚙️ Painel Administrativo")
    
    tab1, tab2, tab3 = st.tabs(["Usuários", "Todos os Projetos", "Estatísticas Gerais"])
    
    with tab1:
        st.subheader("👥 Gerenciamento de Usuários")
        users = get_users()
        
        if not users.empty:
            st.dataframe(users, use_container_width=True)
        else:
            st.info("Nenhum usuário cadastrado")
    
    with tab2:
        st.subheader("📋 Todos os Projetos")
        all_projects = get_projects()  # Sem filtro de usuário
        
        if not all_projects.empty:
            st.dataframe(all_projects, use_container_width=True)
        else:
            st.info("Nenhum projeto cadastrado")
    
    with tab3:
        st.subheader("📈 Estatísticas Gerais")
        
        users = get_users()
        projects = get_projects()
        tasks = get_tasks()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Usuários", len(users))
            st.metric("Gerentes", len(users[users['role'] == 'gerente']))
            st.metric("Membros", len(users[users['role'] == 'membro']))
        
        with col2:
            st.metric("Total de Projetos", len(projects))
            st.metric("Projetos Ativos", len(projects[projects['status'] == 'ativo']))
            st.metric("Orçamento Total", f"R$ {projects['budget'].sum():,.2f}")
        
        with col3:
            st.metric("Total de Tarefas", len(tasks))
            st.metric("Tarefas Concluídas", len(tasks[tasks['status'] == 'concluída']))
            overall_completion = (len(tasks[tasks['status'] == 'concluída']) / len(tasks) * 100) if len(tasks) > 0 else 0
            st.metric("Média Conclusão", f"{overall_completion:.1f}%")

if __name__ == "__main__":
    main()