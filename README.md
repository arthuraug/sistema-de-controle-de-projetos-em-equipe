# 🗂️ Sistema de Controle de Projetos em Equipe

Autores: Arthur Augusto e Euclides Benício
📌 Descrição do Projeto

Este repositório contém o desenvolvimento de um Sistema de Controle de Projetos em Equipe, criado como parte de uma atividade acadêmica.
O objetivo do sistema é permitir que usuários (gestores e membros) gerenciem projetos, tarefas, equipes, comunicação interna e geração de relatórios dentro de um ambiente simples e intuitivo.

Inclui também toda a modelagem UML, como:

Diagrama de Caso de Uso
Diagrama de Classes
Diagrama de Estados
Diagrama de Atividades
Diagrama de sequência

Além de uma interface protótipo construída com Streamlit para simulação das funcionalidades principais.

🎯 Funcionalidades do Sistema

👤 Usuários
Login e autenticação
Perfis de Gerente e Membro
Atribuições baseadas em papéis

📁 Projetos
Criar, editar e finalizar projetos
Atribuir membros
Visão geral no Dashboard
Controle de progresso

📌 Tarefas
Criar tarefas
Atualizar status
Associar tarefa ao responsável
Gerar métricas de conclusão

💬 Comunicação
Envio de mensagens internas
Histórico simples por projeto

📊 Relatórios
Geração de relatórios gerais do projeto
Resumo de progresso
Indicadores de produtividade

🏗️ Modelagem UML Incluída

📘 Diagrama de Caso de Uso
Representa todas as funcionalidades centrais e os atores do sistema.

📗 Diagrama de Classes
Inclui classes como:
Usuário
Gerente
Membro
Projeto
Tarefa
Mensagem
Relatório
Sistema
Com associações, cardinalidades e principais métodos.

📙 Diagrama de Estados
Modela o ciclo de vida de:
Tarefa — Criando → Em andamento → Concluindo → Finalizada

Sessão de usuário — Autenticando → Carregando painel → Manipulando Projeto → Saindo

📕 Diagrama de Atividades
Fluxos principais do sistema, como:
Processo de login
Processo de criação de projeto
Atualização de tarefa

🛠️ Tecnologias Utilizadas
Python 3.x
Streamlit (interface protótipo)
Pandas (manipulação simples de dados)
SQLite (persistência inicial para protótipo)
Draw.io  (diagramas UML)
