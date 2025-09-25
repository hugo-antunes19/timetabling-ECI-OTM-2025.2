import json
from ortools.sat.python import cp_model
import time

def gerar_grade_otimizada():
    start_time = time.time()

    # --- 1. Carregar os Dados ---
    with open('./attempt1/disciplinas.json', 'r') as f:
        disciplinas_data = json.load(f)
    with open('./attempt1/ofertas.json', 'r') as f:
        ofertas_data = json.load(f)

    # Parâmetros do modelo
    NUM_SEMESTRES = 10
    CREDITOS_MAXIMOS_POR_SEMESTRE = 32

    # --- Pré-processamento dos Dados ---
    disciplinas_ofertadas_ids = {o['disciplina_id'] for o in ofertas_data}
    disciplinas_filtradas = [d for d in disciplinas_data if d['id'] in disciplinas_ofertadas_ids]
    disciplinas = {d['id']: d for d in disciplinas_filtradas}
    print(f"Considerando {len(disciplinas)} disciplinas com ofertas disponíveis...")

    turmas_por_disciplina = {d_id: [] for d_id in disciplinas}
    for oferta in ofertas_data:
        if oferta['disciplina_id'] in turmas_por_disciplina:
            turmas_por_disciplina[oferta['disciplina_id']].append(oferta['turma_id'])
            
    horarios_por_turma = {o['turma_id']: o['horario'] for o in ofertas_data}

    # --- NOVO: Mapear os períodos válidos para cada disciplina ---
    periodos_validos_por_disciplina = {}
    for oferta in ofertas_data:
        d_id = oferta['disciplina_id']
        # Converte a string "1, 2" para uma lista de inteiros [1, 2]
        if 'periodo' in oferta and oferta['periodo']:
            periodos = {int(p.strip()) for p in oferta['periodo'].split(',')}
            if d_id not in periodos_validos_por_disciplina:
                periodos_validos_por_disciplina[d_id] = set()
            # Usamos um set para unir os períodos caso uma disciplina tenha múltiplas ofertas
            periodos_validos_por_disciplina[d_id].update(periodos)

    # --- 2. Criar o Modelo ---
    model = cp_model.CpModel()

    # --- 3. Criar as Variáveis de Decisão ---
    alocacao = {}
    for d_id in disciplinas:
        periodos_validos = periodos_validos_por_disciplina.get(d_id, {1, 2}) # Se não especificado, assume ambos
        oferta_em_impar = 1 in periodos_validos
        oferta_em_par = 2 in periodos_validos

        for t_id in turmas_por_disciplina[d_id]:
            for s in range(1, NUM_SEMESTRES + 1):
                is_semestre_impar = (s % 2 != 0)
                
                # --- LÓGICA MODIFICADA AQUI ---
                # Só cria a variável se o semestre for compatível com o período de oferta
                if (is_semestre_impar and oferta_em_impar) or (not is_semestre_impar and oferta_em_par):
                    alocacao[(d_id, s, t_id)] = model.NewBoolVar(f'alocacao_{d_id}_s{s}_t{t_id}')

    semestre_da_disciplina = {
        d_id: model.NewIntVar(1, NUM_SEMESTRES, f'semestre_{d_id}')
        for d_id in disciplinas
    }

    # --- 4. Adicionar as Restrições ---

    # R1: Cada disciplina (filtrada) deve ser cursada exatamente uma vez.
    for d_id in disciplinas:
        turmas_validas = [var for key, var in alocacao.items() if key[0] == d_id]
        model.AddExactlyOne(turmas_validas)

    # R2 (Ligação): Ligar a variável 'semestre_da_disciplina' com as variáveis de alocação.
    for d_id in disciplinas:
        for s in range(1, NUM_SEMESTRES + 1):
            turmas_no_semestre_s = [alocacao[key] for key in alocacao if key[0] == d_id and key[1] == s]
            cursada_em_s = model.NewBoolVar(f'{d_id}_cursada_em_s{s}')

            # Se não houver turmas válidas para este semestre, a disciplina não pode ser cursada nele
            if not turmas_no_semestre_s:
                model.Add(cursada_em_s == 0)
            else:
                model.Add(sum(turmas_no_semestre_s) == 1).OnlyEnforceIf(cursada_em_s)
                model.Add(sum(turmas_no_semestre_s) == 0).OnlyEnforceIf(cursada_em_s.Not())

            model.Add(semestre_da_disciplina[d_id] == s).OnlyEnforceIf(cursada_em_s)
            model.Add(semestre_da_disciplina[d_id] != s).OnlyEnforceIf(cursada_em_s.Not())

    # R3 (Pré-requisitos): O semestre da disciplina deve ser maior que o do pré-requisito.
    for d_id, disc_info in disciplinas.items():
        for prereq_id in disc_info.get('prerequisitos', []):
            if prereq_id in semestre_da_disciplina:
                model.Add(semestre_da_disciplina[d_id] > semestre_da_disciplina[prereq_id])

    # R4: Sem conflitos de horário no mesmo semestre.
    for s in range(1, NUM_SEMESTRES + 1):
        horarios_do_semestre = {}
        for d_id in disciplinas:
            for t_id in turmas_por_disciplina[d_id]:
                if (d_id, s, t_id) in alocacao:
                    for h in horarios_por_turma[t_id]:
                        if h not in horarios_do_semestre:
                            horarios_do_semestre[h] = []
                        horarios_do_semestre[h].append(alocacao[(d_id, s, t_id)])
        for h, turmas_conflitantes in horarios_do_semestre.items():
            model.AddAtMostOne(turmas_conflitantes)

    # R5: Limite de Créditos por Semestre.
    for s in range(1, NUM_SEMESTRES + 1):
        termos_de_credito = []
        for d_id, disc_info in disciplinas.items():
            creditos = int(disc_info['creditos'])
            cursada_neste_semestre_vars = [
                alocacao[key] for key in alocacao if key[0] == d_id and key[1] == s
            ]
            if cursada_neste_semestre_vars:
                 termos_de_credito.append(creditos * sum(cursada_neste_semestre_vars))
        
        if termos_de_credito:
            model.Add(sum(termos_de_credito) <= CREDITOS_MAXIMOS_POR_SEMESTRE)

    # --- 5. Definir a Função Objetivo ---
    semestre_maximo = model.NewIntVar(1, NUM_SEMESTRES, 'semestre_maximo')
    model.AddMaxEquality(semestre_maximo, [sem for sem in semestre_da_disciplina.values()])
    model.Minimize(semestre_maximo)

    # --- 6. Chamar o Solver ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0
    status = solver.Solve(model)

    # --- 7. Exibir os Resultados ---
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f'\nSolução encontrada em {time.time() - start_time:.2f} segundos.')
        print(f'Número mínimo de semestres: {solver.ObjectiveValue()}')
        
        grade = {s: [] for s in range(1, int(solver.ObjectiveValue()) + 1)}
        creditos_por_semestre = {s: 0 for s in range(1, int(solver.ObjectiveValue()) + 1)}

        for (d_id, s, t_id), var in alocacao.items():
            if solver.Value(var):
                horarios = horarios_por_turma.get(t_id, [])
                horarios_str = ", ".join(horarios)
                string_disciplina = f'{disciplinas[d_id]["nome"]} (Turma: {t_id}) --- Horários: [{horarios_str}]'
                grade[s].append(string_disciplina)
                creditos_por_semestre[s] += disciplinas[d_id]['creditos']
        
        for s, disciplinas_semestre in sorted(grade.items()):
            if disciplinas_semestre:
                print(f'\n--- Semestre {s} (Créditos: {creditos_por_semestre[s]}) ---')
                for d_str in sorted(disciplinas_semestre):
                    print(f'  - {d_str}')
    elif status == cp_model.INFEASIBLE:
        print('Nenhuma solução encontrada: O modelo é infactível. A restrição de período pode ter tornado o problema impossível.')
    else:
        print('Nenhuma solução encontrada: O solver parou por outro motivo (ex: tempo limite).')


if __name__ == '__main__':
    gerar_grade_otimizada()