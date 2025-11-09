# data_loader.py
import json

# --- MUDANÇA PRINCIPAL: Adiciona o parâmetro 'disciplinas_concluidas=[]' ---
def carregar_dados(caminho_disciplinas, caminho_ofertas, disciplinas_concluidas=[]):
    """
    Carrega os dados dos arquivos JSON, categoriza as disciplinas, realiza o pré-processamento
    e remove as disciplinas já concluídas.
    Retorna um dicionário contendo todas as estruturas de dados necessárias.
    """
    with open(caminho_disciplinas, 'r', encoding='utf-8') as f:
        disciplinas_data = json.load(f)
    with open(caminho_ofertas, 'r', encoding='utf-8') as f:
        ofertas_data = json.load(f)

    # --- LÓGICA DE PRÉ-FILTRAGEM (DO CP-SAT) ---
    # Remove disciplinas concluídas da lista de dados
    # Também remove os pré-requisitos que já foram satisfeitos
    disciplinas_data_filtrado = []
    for d in disciplinas_data:
        if d['id'] not in disciplinas_concluidas:
            # Remove pré-requisitos que o aluno já cumpriu
            d['prerequisitos'] = [p for p in d.get('prerequisitos', []) if p not in disciplinas_concluidas]
            disciplinas_data_filtrado.append(d)

    # Continua a função usando a lista filtrada
    disciplinas_data = disciplinas_data_filtrado
    # --- FIM DA LÓGICA DE PRÉ-FILTRAGEM ---

    obrigatorias_ids = []
    restritas_ids = []
    condicionadas_ids = []
    livres_ids = []

    for d in disciplinas_data:
        tipo = d.get("tipo", "")
        if "Período" in tipo:
            obrigatorias_ids.append(d["id"])
        elif "Escolha Restrita" in tipo:
            restritas_ids.append(d["id"])
        elif "Escolha Condicionada" in tipo:
            condicionadas_ids.append(d["id"])
        elif "Livre Escolha" in tipo or d["id"].startswith("ARTIFICIAL"):
            livres_ids.append(d["id"])

    # Filtra disciplinas que não têm oferta (o solver não pode alocá-las)
    disciplinas_ofertadas_ids = {o['disciplina_id'] for o in ofertas_data}
    disciplinas_filtradas = [d for d in disciplinas_data if d['id'] in disciplinas_ofertadas_ids]
    disciplinas = {d['id']: d for d in disciplinas_filtradas}
    print(f"Considerando {len(disciplinas)} disciplinas com ofertas disponíveis (após filtro de concluídas)...")

    turmas_por_disciplina = {d_id: [] for d_id in disciplinas}
    horarios_por_turma = {}
    periodos_validos_por_disciplina = {}

    for oferta in ofertas_data:
        d_id = oferta['disciplina_id']
        t_id = oferta['turma_id']
        
        # Adiciona apenas se a disciplina ainda estiver na lista filtrada
        if d_id in turmas_por_disciplina: 
            turmas_por_disciplina[d_id].append(t_id)
            horarios_por_turma[t_id] = oferta.get('horario', [])

            if 'periodo' in oferta and oferta['periodo']:
                periodos = {int(p.strip()) for p in oferta['periodo'].split(',') if p.strip()}
                if d_id not in periodos_validos_por_disciplina:
                    periodos_validos_por_disciplina[d_id] = set()
                periodos_validos_por_disciplina[d_id].update(periodos)
    
    return {
        "disciplinas": disciplinas,
        "turmas_por_disciplina": turmas_por_disciplina,
        "horarios_por_turma": horarios_por_turma,
        "periodos_validos_por_disciplina": periodos_validos_por_disciplina,
        "obrigatorias_ids": [d_id for d_id in obrigatorias_ids if d_id in disciplinas],
        "restritas_ids": [d_id for d_id in restritas_ids if d_id in disciplinas],
        "condicionadas_ids": [d_id for d_id in condicionadas_ids if d_id in disciplinas],
        "livres_ids": [d_id for d_id in livres_ids if d_id in disciplinas]
    }