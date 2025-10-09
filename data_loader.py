# data_loader.py
import json

def carregar_dados(caminho_disciplinas, caminho_ofertas):
    """
    Carrega os dados dos arquivos JSON e realiza o pré-processamento.
    Retorna um dicionário contendo todas as estruturas de dados necessárias.
    """
    with open(caminho_disciplinas, 'r', encoding='utf-8') as f:
        disciplinas_data = json.load(f)
    with open(caminho_ofertas, 'r', encoding='utf-8') as f:
        ofertas_data = json.load(f)

    # Filtra as disciplinas para considerar apenas aquelas com ofertas
    disciplinas_ofertadas_ids = {o['disciplina_id'] for o in ofertas_data}
    disciplinas_filtradas = [d for d in disciplinas_data if d['id'] in disciplinas_ofertadas_ids]
    disciplinas = {d['id']: d for d in disciplinas_filtradas}
    print(f"Considerando {len(disciplinas)} disciplinas com ofertas disponíveis...")

    # Mapeia turmas para cada disciplina
    turmas_por_disciplina = {d_id: [] for d_id in disciplinas}
    for oferta in ofertas_data:
        if oferta['disciplina_id'] in turmas_por_disciplina:
            turmas_por_disciplina[oferta['disciplina_id']].append(oferta['turma_id'])
            
    # Mapeia turma para seus horários
    horarios_por_turma = {o['turma_id']: o['horario'] for o in ofertas_data}

    # Mapeia disciplina para seus períodos de oferta válidos
    periodos_validos_por_disciplina = {}
    for oferta in ofertas_data:
        d_id = oferta['disciplina_id']
        if 'periodo' in oferta and oferta['periodo']:
            periodos = {int(p.strip()) for p in oferta['periodo'].split(',')}
            if d_id not in periodos_validos_por_disciplina:
                periodos_validos_por_disciplina[d_id] = set()
            periodos_validos_por_disciplina[d_id].update(periodos)
    
    return {
        "disciplinas": disciplinas,
        "turmas_por_disciplina": turmas_por_disciplina,
        "horarios_por_turma": horarios_por_turma,
        "periodos_validos_por_disciplina": periodos_validos_por_disciplina
    }