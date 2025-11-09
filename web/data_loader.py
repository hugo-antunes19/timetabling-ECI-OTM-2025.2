# data_loader.py
import json

def carregar_dados(caminho_disciplinas, caminho_ofertas):
    """
    Carrega os dados dos arquivos JSON, categoriza as disciplinas e realiza o pré-processamento.
    Retorna um dicionário contendo todas as estruturas de dados necessárias.
    """
    with open(caminho_disciplinas, 'r', encoding='utf-8') as f:
        disciplinas_data = json.load(f)
    with open(caminho_ofertas, 'r', encoding='utf-8') as f:
        ofertas_data = json.load(f)

    # --- MUDANÇA AQUI: Categorizar disciplinas antes de filtrar ---
    obrigatorias_ids = []
    restritas_ids = []
    condicionadas_ids = []
    livres_ids = []

    for d in disciplinas_data:
        tipo = d.get("tipo", "")
        # Considera disciplinas de Períodos e Estágio/TCC como obrigatórias
        if "Período" in tipo:
            obrigatorias_ids.append(d["id"])
        elif "Escolha Restrita" in tipo:
            restritas_ids.append(d["id"])
        elif "Escolha Condicionada" in tipo:
            condicionadas_ids.append(d["id"])
        # As disciplinas "ARTIFICIAL" que você criou caem aqui
        elif "Livre Escolha" in tipo or d["id"].startswith("ARTIFICIAL"):
            livres_ids.append(d["id"])

    # Filtra as disciplinas para considerar apenas aquelas com ofertas
    disciplinas_ofertadas_ids = {o['disciplina_id'] for o in ofertas_data}
    disciplinas_filtradas = [d for d in disciplinas_data if d['id'] in disciplinas_ofertadas_ids]
    disciplinas = {d['id']: d for d in disciplinas_filtradas}
    print(f"Considerando {len(disciplinas)} disciplinas com ofertas disponíveis...")

    # Mapeia turmas, horários e períodos
    turmas_por_disciplina = {d_id: [] for d_id in disciplinas}
    horarios_por_turma = {}
    periodos_validos_por_disciplina = {}

    for oferta in ofertas_data:
        d_id = oferta['disciplina_id']
        t_id = oferta['turma_id']
        
        if d_id in turmas_por_disciplina:
            turmas_por_disciplina[d_id].append(t_id)
        
        horarios_por_turma[t_id] = oferta.get('horario', [])

        if 'periodo' in oferta and oferta['periodo']:
            periodos = {int(p.strip()) for p in oferta['periodo'].split(',')}
            if d_id not in periodos_validos_por_disciplina:
                periodos_validos_por_disciplina[d_id] = set()
            periodos_validos_por_disciplina[d_id].update(periodos)
    
    return {
        "disciplinas": disciplinas,
        "turmas_por_disciplina": turmas_por_disciplina,
        "horarios_por_turma": horarios_por_turma,
        "periodos_validos_por_disciplina": periodos_validos_por_disciplina,
        # --- NOVO: Retorna as listas de IDs categorizados ---
        "obrigatorias_ids": [d_id for d_id in obrigatorias_ids if d_id in disciplinas],
        "restritas_ids": [d_id for d_id in restritas_ids if d_id in disciplinas],
        "condicionadas_ids": [d_id for d_id in condicionadas_ids if d_id in disciplinas],
        "livres_ids": [d_id for d_id in livres_ids if d_id in disciplinas]
    }