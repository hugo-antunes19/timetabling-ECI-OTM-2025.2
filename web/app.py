# app.py
import streamlit as st
import time
import json
import pandas as pd
from ortools.linear_solver import pywraplp
from data_loader import carregar_dados
from optimizerMILP import resolver_grade

# --- Constantes do Modelo ---
CAMINHO_DISCIPLINAS = '../attempt1/disciplinas.json'
CAMINHO_OFERTAS = '../attempt1/ofertas.json'
CREDITOS_MAXIMOS_POR_SEMESTRE = 32
CREDITOS_MINIMOS_TOTAIS = {
    "restrita": 4,
    "condicionada": 40,
    "livre": 8
}
TOTAL_CREDITOS_CURSO = 240 

# --- CORREÇÃO: Carregar o JSON completo aqui ---
try:
    with open(CAMINHO_DISCIPLINAS, 'r', encoding='utf-8') as f:
        TODAS_DISCIPLINAS_INFO = {d['id']: d for d in json.load(f)}
except Exception as e:
    st.error(f"ERRO CRÍTICO: Não foi possível ler {CAMINHO_DISCIPLINAS}. {e}")
    st.stop()
# --- FIM DA CORREÇÃO ---


# --- CORREÇÃO: Remover @st.cache_data e passar o input ---
def carregar_dados_filtrados(disciplinas_concluidas_ids):
    """
    Carrega os dados e JÁ FILTRA as disciplinas concluídas,
    imitando o comportamento do data_loader do CP-SAT.
    """
    try:
        # Passa as disciplinas concluídas para o loader
        return carregar_dados(CAMINHO_DISCIPLINAS, CAMINHO_OFERTAS, 
                              disciplinas_concluidas=disciplinas_concluidas_ids)
    except FileNotFoundError as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None
# --- FIM DA CORREÇÃO ---


# --- Função da Grade Horária (Sem mudanças) ---
def criar_grade_semanal(disciplinas_do_semestre):
    dias_semana = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB"]
    slots_horas = [
        "08-10", "10-12", "13-15", "15-17", 
        "17-19", "19-21", "21-23" 
    ]
    slots_presentes = set(slots_horas)
    for d in disciplinas_do_semestre:
        for h in d["horarios"]:
            try:
                partes = h.split("-")
                if len(partes) == 3: slots_presentes.add(f"{partes[1]}-{partes[2]}")
            except Exception: pass 
    slots_index = sorted(list(slots_presentes))
    if not slots_index: slots_index = slots_horas
    df = pd.DataFrame(index=slots_index, columns=dias_semana).fillna("")
    for disciplina in disciplinas_do_semestre:
        nome_disciplina, turma = disciplina["nome"], disciplina["turma"]
        for horario_str in disciplina["horarios"]:
            try:
                partes = horario_str.split("-")
                if len(partes) == 3:
                    dia, slot = partes[0], f"{partes[1]}-{partes[2]}"
                else: raise ValueError("Formato")
                if dia in df.columns and slot in df.index:
                    if df.loc[slot, dia] == "": df.loc[slot, dia] = f"{nome_disciplina} (Turma: {turma})"
                    else: df.loc[slot, dia] += f" / {nome_disciplina} (Turma: {turma})" 
                else: st.warning(f"Horário '{horario_str}' fora da grade.")
            except Exception as e: st.warning(f"Não foi possível parsear horário: '{horario_str}'.")
    return df

# --- Interface da Aplicação ---
st.set_page_config(layout="wide")
st.title("🎓 Otimizador de Grade Horária")
st.write("Selecione as disciplinas que você já concluiu...")

st.header("1. Suas Informações")
# Popula a UI de seleção a partir do JSON completo
obrigatorias_por_periodo, opt_restritas, opt_condicionadas, opt_livres, outras = {}, [], [], [], []
for d_id, d in TODAS_DISCIPLINAS_INFO.items():
    tipo, opcao = d.get("tipo", ""), (f"{d['id']} - {d.get('nome', 'Nome Desconhecido')}", d['id'])
    if "Período" in tipo:
        if tipo not in obrigatorias_por_periodo: obrigatorias_por_periodo[tipo] = []
        obrigatorias_por_periodo[tipo].append(opcao)
    elif "Escolha Restrita" in tipo: opt_restritas.append(opcao)
    elif "Escolha Condicionada" in tipo: opt_condicionadas.append(opcao)
    elif "Livre Escolha" in tipo or d["id"].startswith("ARTIFICIAL"): opt_livres.append(opcao)
    else: outras.append(opcao) 

st.subheader("Disciplinas Concluídas")
grupos_de_selecao = {}
for periodo in sorted(obrigatorias_por_periodo.keys()):
    grupos_de_selecao[f"Obrigatórias - {periodo}"] = obrigatorias_por_periodo[periodo]
grupos_de_selecao["Optativas - Escolha Restrita"] = opt_restritas
grupos_de_selecao["Optativas - Escolha Condicionada"] = opt_condicionadas
grupos_de_selecao["Optativas - Livre Escolha"] = opt_livres
if outras: grupos_de_selecao["Outras (Estágio, TCC, etc.)"] = outras
for titulo_grupo, opcoes_grupo in grupos_de_selecao.items():
    chave_estado = f"select_{titulo_grupo}"
    if chave_estado not in st.session_state: st.session_state[chave_estado] = []
    with st.expander(titulo_grupo):
        col1, col2, _ = st.columns([1, 1, 3])
        if col1.button(f"Selecionar Tudo", key=f"btn_all_{chave_estado}"):
            st.session_state[chave_estado] = opcoes_grupo
            st.rerun() 
        if col2.button(f"Limpar", key=f"btn_clear_{chave_estado}"):
            st.session_state[chave_estado] = []
            st.rerun() 
        st.multiselect(f"Selecione ({titulo_grupo}):", options=opcoes_grupo, format_func=lambda x: x[0], key=chave_estado, label_visibility="collapsed")
all_selected_ids = set()
for key, selected_items in st.session_state.items():
    if key.startswith("select_"):
        for item in selected_items: all_selected_ids.add(item[1]) 
disciplinas_concluidas_ids = list(all_selected_ids)
st.subheader("Próximo Semestre")
semestre_inicio = st.number_input("Qual o NÚMERO do seu próximo semestre?", min_value=1, max_value=14, value=1)
st.warning(f"Otimizador irá considerar que você está começando o **{semestre_inicio}º semestre**.")

# --- Botão para Executar ---
st.header("2. Gerar Grade")
if st.button("Encontrar Grade Otimizada", type="primary"):
    start_time = time.time()
    
    # --- CORREÇÃO: Carrega os dados AQUI, após o input ---
    dados = carregar_dados_filtrados(disciplinas_concluidas_ids)
    if not dados:
        st.error("Falha ao carregar dados. Verifique os logs.")
        st.stop()
    
    with st.spinner("Calculando a melhor rota..."):
        
        # --- CORREÇÃO: Chamada de 7 argumentos ---
        grade, creditos, status, obj_value = resolver_grade(
            dados, 
            TODAS_DISCIPLINAS_INFO, # 1. dados (filtrado)
            CREDITOS_MINIMOS_TOTAIS, # 2. todos_disciplinas_info
            CREDITOS_MAXIMOS_POR_SEMESTRE, # 3. creditos_minimos
            disciplinas_concluidas_ids, # 4. ...
            semestre_inicio,
            TOTAL_CREDITOS_CURSO
        )
    end_time = time.time()
    st.info(f"Cálculo concluído em {end_time - start_time:.2f} segundos.")
    # ... (Resto do código de exibição) ...
    st.header("3. Resultados")
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        semestres_restantes = (int(obj_value) - semestre_inicio) + 1
        st.success("🎉 Solução encontrada!")
        col1, col2 = st.columns(2)
        col1.metric("Número Mínimo de Semestres Restantes", f"{semestres_restantes} Semestres")
        col2.metric("Semestre de Conclusão Previsto", f"{int(obj_value)}º Semestre")
        st.subheader("Grade Horária Sugerida:")
        for s in sorted(grade.keys()):
            st.markdown(f"---")
            st.markdown(f"#### Semestre {s} (Total: {creditos[s]} créditos)")
            disciplinas_do_semestre = grade[s]
            if disciplinas_do_semestre:
                df_grade = criar_grade_semanal(disciplinas_do_semestre)
                st.dataframe(df_grade, use_container_width=True)
                with st.expander("Lista de disciplinas deste semestre"):
                    for d in disciplinas_do_semestre:
                        st.markdown(f"- **{d['nome']}** (Turma: {d['turma']}, Créditos: {d['creditos']})")
            else:
                st.write("Nenhuma disciplina alocada neste semestre.")
    elif status == pywraplp.Solver.INFEASIBLE:
        st.error("Nenhuma solução encontrada: O modelo é infactível.")
    else:
        st.error(f"Nenhuma solução encontrada (status: {status}).")