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

# Ajuste este valor para a realidade do seu currículo (ex: 240)
TOTAL_CREDITOS_CURSO = 240 

# --- MUDANÇA: Carregar o JSON completo aqui ---
try:
    with open(CAMINHO_DISCIPLINAS, 'r', encoding='utf-8') as f:
        TODAS_DISCIPLINAS_INFO = {d['id']: d for d in json.load(f)}
except Exception as e:
    st.error(f"ERRO CRÍTICO: Não foi possível ler {CAMINHO_DISCIPLINAS}. {e}")
    st.stop()
# --- FIM DA MUDANÇA ---


@st.cache_data
def carregar_dados_cached():
    """
    Carrega os dados dos arquivos JSON.
    NOTA: Este loader ainda filtra disciplinas sem oferta,
    o que é CORRETO para o solver (que só pode alocar o que é ofertado).
    A contagem de créditos será feita separadamente.
    """
    try:
        return carregar_dados(CAMINHO_DISCIPLINAS, CAMINHO_OFERTAS)
    except FileNotFoundError as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

# --- Função da Grade Horária (Corrigida para "DIA-HH-HH") ---
def criar_grade_semanal(disciplinas_do_semestre):
    """
    Cria um DataFrame do Pandas formatado como grade horária.
    Assume que os horários estão no formato "DIA-HH-HH" (ex: "SEG-08-10").
    """
    
    # Ajuste esta lista para cobrir todos os seus horários possíveis
    dias_semana = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB"]
    slots_horas = [
        "08-10", "10-12", "13-15", "15-17", 
        "17-19", "19-21", "21-23" # Adapte conforme seus dados
    ]
    
    # Garante que todos os slots de horário reais sejam indexados
    slots_presentes = set(slots_horas)
    for d in disciplinas_do_semestre:
        for h in d["horarios"]:
            try:
                partes = h.split("-")
                if len(partes) == 3:
                    slot = f"{partes[1]}-{partes[2]}"
                    slots_presentes.add(slot)
            except Exception:
                pass 
    
    slots_index = sorted(list(slots_presentes))
    if not slots_index: 
        slots_index = slots_horas
        
    df = pd.DataFrame(index=slots_index, columns=dias_semana).fillna("")

    for disciplina in disciplinas_do_semestre:
        nome_disciplina = disciplina["nome"]
        turma = disciplina["turma"]
        
        for horario_str in disciplina["horarios"]:
            try:
                partes = horario_str.split("-")
                if len(partes) == 3:
                    dia = partes[0]
                    slot = f"{partes[1]}-{partes[2]}"
                else:
                    raise ValueError("Formato de horário inesperado")

                if dia in df.columns and slot in df.index:
                    if df.loc[slot, dia] == "":
                        df.loc[slot, dia] = f"{nome_disciplina} (Turma: {turma})"
                    else:
                        df.loc[slot, dia] += f" / {nome_disciplina} (Turma: {turma})" 
                else:
                    st.warning(f"Horário '{horario_str}' está fora da grade definida (dia='{dia}', slot='{slot}').")
            except Exception as e:
                st.warning(f"Não foi possível parsear o horário: '{horario_str}'. Erro: {e}")

    return df

# --- Interface da Aplicação ---
st.set_page_config(layout="wide")
st.title("🎓 Otimizador de Grade Horária")
st.write("Selecione as disciplinas que você já concluiu e seu próximo semestre para otimizar sua rota de graduação.")

# Carrega os dados (usando o cache)
dados = carregar_dados_cached()
if not dados:
    st.stop()

# --- Entradas do Usuário (com botões Selecionar/Limpar) ---
st.header("1. Suas Informações")

# (O JSON completo já foi carregado em TODAS_DISCIPLINAS_INFO)
obrigatorias_por_periodo = {}
opt_restritas = []
opt_condicionadas = []
opt_livres = []
outras = []

for d_id, d in TODAS_DISCIPLINAS_INFO.items():
    tipo = d.get("tipo", "")
    opcao = (f"{d['id']} - {d.get('nome', 'Nome Desconhecido')}", d['id'])
    
    if "Período" in tipo:
        if tipo not in obrigatorias_por_periodo:
            obrigatorias_por_periodo[tipo] = []
        obrigatorias_por_periodo[tipo].append(opcao)
    elif "Escolha Restrita" in tipo:
        opt_restritas.append(opcao)
    elif "Escolha Condicionada" in tipo:
        opt_condicionadas.append(opcao)
    elif "Livre Escolha" in tipo or d["id"].startswith("ARTIFICIAL"):
        opt_livres.append(opcao)
    else:
        outras.append(opcao) 

st.subheader("Disciplinas Concluídas")
st.write("Marque todas as disciplinas que você já cursou e foi aprovado.")

grupos_de_selecao = {}
for periodo in sorted(obrigatorias_por_periodo.keys()):
    grupos_de_selecao[f"Obrigatórias - {periodo}"] = obrigatorias_por_periodo[periodo]
grupos_de_selecao["Optativas - Escolha Restrita"] = opt_restritas
grupos_de_selecao["Optativas - Escolha Condicionada"] = opt_condicionadas
grupos_de_selecao["Optativas - Livre Escolha"] = opt_livres
if outras:
    grupos_de_selecao["Outras (Estágio, TCC, etc.)"] = outras

for titulo_grupo, opcoes_grupo in grupos_de_selecao.items():
    chave_estado = f"select_{titulo_grupo}"
    if chave_estado not in st.session_state:
        st.session_state[chave_estado] = []
    with st.expander(titulo_grupo):
        col1, col2, col_vazia = st.columns([1, 1, 3])
        with col1:
            if st.button(f"Selecionar Tudo", key=f"btn_all_{chave_estado}"):
                st.session_state[chave_estado] = opcoes_grupo
                st.rerun() 
        with col2:
            if st.button(f"Limpar", key=f"btn_clear_{chave_estado}"):
                st.session_state[chave_estado] = []
                st.rerun() 
        st.multiselect(
            f"Selecione as disciplinas ({titulo_grupo}):",
            options=opcoes_grupo,
            format_func=lambda x: x[0],
            key=chave_estado,
            label_visibility="collapsed"
        )

all_selected_ids = set()
for key, selected_items in st.session_state.items():
    if key.startswith("select_"):
        for item in selected_items:
            all_selected_ids.add(item[1]) 

disciplinas_concluidas_ids = list(all_selected_ids)

st.subheader("Próximo Semestre")
semestre_inicio = st.number_input(
    "Qual o NÚMERO do seu próximo semestre? (Ex: 1, 2, 3...)",
    min_value=1,
    max_value=14,
    value=1
)
st.warning(f"Otimizador irá considerar que você está começando o **{semestre_inicio}º semestre**.")

# --- Botão para Executar ---
st.header("2. Gerar Grade")

if st.button("Encontrar Grade Otimizada", type="primary"):
    start_time = time.time()
    
    with st.spinner("Calculando a melhor rota... O solver MILP está trabalhando. Isso pode levar alguns minutos..."):
        
        # --- MUDANÇA: Passar TODAS_DISCIPLINAS_INFO como novo argumento ---
        grade, creditos, status, obj_value = resolver_grade(
            dados, 
            TODAS_DISCIPLINAS_INFO, # <-- NOVO ARGUMENTO
            CREDITOS_MINIMOS_TOTAIS, 
            CREDITOS_MAXIMOS_POR_SEMESTRE,
            disciplinas_concluidas_ids,
            semestre_inicio,
            TOTAL_CREDITOS_CURSO
        )

    end_time = time.time()
    st.info(f"Cálculo concluído em {end_time - start_time:.2f} segundos.")

    # --- 3. Exibir Resultados ---
    st.header("3. Resultados")

    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        semestres_restantes = (int(obj_value) - semestre_inicio) + 1
        st.success("🎉 Solução encontrada!")
        
        col1, col2 = st.columns(2)
        col1.metric(
            label="Número Mínimo de Semestres Restantes", 
            value=f"{semestres_restantes} Semestres"
        )
        col2.metric(
            label="Semestre de Conclusão Previsto",
            value=f"{int(obj_value)}º Semestre"
        )

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
        st.write("Isso pode acontecer por algumas razões:")
        st.write("* Não há como cumprir os créditos mínimos restantes no tempo limite.")
        st.write("* Os pré-requisitos não podem ser satisfeitos (verifique as disciplinas concluídas).")
        st.write("* O limite de créditos por semestre é muito baixo.")
        st.write("* Não existem turmas/horários que não conflitem.")

    else:
        st.error(f"Nenhuma solução encontrada: O solver parou por outro motivo (status: {status}).")