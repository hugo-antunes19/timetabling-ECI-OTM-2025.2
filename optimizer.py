# optimizer.py
from ortools.sat.python import cp_model

def resolver_grade(dados, creditos_minimos, NUM_SEMESTRES, CREDITOS_MAXIMOS_POR_SEMESTRE):
    """
    Cria e resolve o modelo de otimização da grade horária.
    Retorna os resultados da otimização.
    """
    model = cp_model.CpModel()

    # Extrai as estruturas de dados do dicionário 'dados'
    disciplinas = dados["disciplinas"]
    turmas_por_disciplina = dados["turmas_por_disciplina"]
    horarios_por_turma = dados["horarios_por_turma"]
    periodos_validos_por_disciplina = dados["periodos_validos_por_disciplina"]
    
    obrigatorias_ids = dados["obrigatorias_ids"]
    restritas_ids = dados["restritas_ids"]
    condicionadas_ids = dados["condicionadas_ids"]
    livres_ids = dados["livres_ids"]
    
    ids_optativas = restritas_ids + condicionadas_ids + livres_ids

    # --- 3. Criar as Variáveis de Decisão ---
    alocacao = {}
    for d_id in disciplinas:
        periodos_validos = periodos_validos_por_disciplina.get(d_id, {1, 2})
        oferta_em_impar = 1 in periodos_validos
        oferta_em_par = 2 in periodos_validos

        for t_id in turmas_por_disciplina.get(d_id, []):
            for s in range(1, NUM_SEMESTRES + 1):
                is_semestre_impar = (s % 2 != 0)
                if (is_semestre_impar and oferta_em_impar) or (not is_semestre_impar and oferta_em_par):
                    alocacao[(d_id, s, t_id)] = model.NewBoolVar(f'alocacao_{d_id}_s{s}_t{t_id}')

    semestre_da_disciplina = {
        d_id: model.NewIntVar(1, NUM_SEMESTRES + 1, f'semestre_{d_id}') # +1 para disciplinas não cursadas
        for d_id in disciplinas
    }

    # --- MUDANÇA AQUI: Dicionário para guardar as variáveis 'cursada' ---
    cursada_vars = {}

    # --- 4. Adicionar as Restrições ---

    # R1.1: Disciplinas OBRIGATÓRIAS devem ser cursadas EXATAMENTE uma vez.
    for d_id in obrigatorias_ids:
        model.AddExactlyOne([var for key, var in alocacao.items() if key[0] == d_id])

    # R1.2: Disciplinas OPTATIVAS podem ser cursadas NO MÁXIMO uma vez.
    for d_id in ids_optativas:
        model.AddAtMostOne([var for key, var in alocacao.items() if key[0] == d_id])

    # R2 (Ligação): Ligar 'semestre_da_disciplina' com 'alocacao'.
    for d_id in disciplinas:
        cursada = model.NewBoolVar(f'cursada_{d_id}')
        cursada_vars[d_id] = cursada # --- MUDANÇA AQUI: Armazena a variável ---

        model.Add(sum(var for key, var in alocacao.items() if key[0] == d_id) == 1).OnlyEnforceIf(cursada)
        model.Add(sum(var for key, var in alocacao.items() if key[0] == d_id) == 0).OnlyEnforceIf(cursada.Not())
        
        for s in range(1, NUM_SEMESTRES + 1):
            cursada_em_s = model.NewBoolVar(f'{d_id}_cursada_em_s{s}')
            turmas_no_s = [var for key, var in alocacao.items() if key[0] == d_id and key[1] == s]
            if not turmas_no_s: model.Add(cursada_em_s == 0)
            else: 
                model.Add(sum(turmas_no_s) >= 1).OnlyEnforceIf(cursada_em_s)
                model.Add(sum(turmas_no_s) == 0).OnlyEnforceIf(cursada_em_s.Not())
            model.Add(semestre_da_disciplina[d_id] == s).OnlyEnforceIf(cursada_em_s)
        
        model.Add(semestre_da_disciplina[d_id] == NUM_SEMESTRES + 1).OnlyEnforceIf(cursada.Not())

    # R3: NOVAS RESTRIÇÕES DE CRÉDITOS MÍNIMOS POR CATEGORIA
    termos_creditos_restritas = []
    for d_id in restritas_ids:
        cred = int(disciplinas[d_id]['creditos'])
        cursada = cursada_vars[d_id] # --- MUDANÇA AQUI: Acessa a variável pelo dicionário ---
        termos_creditos_restritas.append(cred * cursada)
    if termos_creditos_restritas:
        model.Add(sum(termos_creditos_restritas) >= creditos_minimos['restrita'])

    termos_creditos_condicionadas = []
    for d_id in condicionadas_ids:
        cred = int(disciplinas[d_id]['creditos'])
        cursada = cursada_vars[d_id] # --- MUDANÇA AQUI: Acessa a variável pelo dicionário ---
        termos_creditos_condicionadas.append(cred * cursada)
    if termos_creditos_condicionadas:
        model.Add(sum(termos_creditos_condicionadas) >= creditos_minimos['condicionada'])

    termos_creditos_livres = []
    for d_id in livres_ids:
        cred = int(disciplinas[d_id]['creditos'])
        cursada = cursada_vars[d_id] # --- MUDANÇA AQUI: Acessa a variável pelo dicionário ---
        termos_creditos_livres.append(cred * cursada)
    if termos_creditos_livres:
        model.Add(sum(termos_creditos_livres) >= creditos_minimos['livre'])

    # Demais restrições (R4, R5, R6)
    for d_id, disc_info in disciplinas.items():
        for prereq_id in disc_info.get('prerequisitos', []):
            if prereq_id in semestre_da_disciplina:
                model.Add(semestre_da_disciplina[d_id] > semestre_da_disciplina[prereq_id])

    for s in range(1, NUM_SEMESTRES + 1):
        horarios_do_semestre = {}
        for (d, sem, t), var in alocacao.items():
            if sem == s:
                for h in horarios_por_turma.get(t, []):
                    if h not in horarios_do_semestre: horarios_do_semestre[h] = []
                    horarios_do_semestre[h].append(var)
        for h, turmas_conflitantes in horarios_do_semestre.items():
            model.AddAtMostOne(turmas_conflitantes)

    for s in range(1, NUM_SEMESTRES + 1):
        termos_de_credito = []
        for d_id in disciplinas:
            creditos = int(disciplinas[d_id]['creditos'])
            cursada_neste_semestre_vars = [var for (d, sem, t), var in alocacao.items() if d == d_id and sem == s]
            if cursada_neste_semestre_vars: termos_de_credito.append(creditos * sum(cursada_neste_semestre_vars))
        if termos_de_credito: model.Add(sum(termos_de_credito) <= CREDITOS_MAXIMOS_POR_SEMESTRE)

    # --- R7 (NOVA RESTRIÇÃO): Regras específicas de disciplinas ---
    # O Estágio Obrigatório (EEWU00) só pode ser cursado a partir do 6º semestre.
    id_estagio = "EEWU00"
    if id_estagio in semestre_da_disciplina:
        model.Add(semestre_da_disciplina[id_estagio] >= 6)
    
    # --- 5. Definir a Função Objetivo ---
    semestre_maximo = model.NewIntVar(1, NUM_SEMESTRES + 1, 'semestre_maximo')
    model.AddMaxEquality(semestre_maximo, list(semestre_da_disciplina.values()))
    model.Minimize(semestre_maximo)

    # --- 6. Chamar o Solver ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 120.0
    status = solver.Solve(model)
    
    # --- 7. Processar e Retornar os Resultados ---
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        grade = {s: [] for s in range(1, NUM_SEMESTRES + 1)}
        creditos_por_semestre = {s: 0 for s in range(1, NUM_SEMESTRES + 1)}

        for (d_id, s, t_id), var in alocacao.items():
            if solver.Value(var):
                string_disciplina = f'{disciplinas[d_id]["nome"]} (Turma: {t_id}) --- Horários: [{", ".join(horarios_por_turma.get(t_id, []))}]'
                grade[s].append(string_disciplina)
                creditos_por_semestre[s] += disciplinas[d_id]['creditos']
        
        return grade, creditos_por_semestre, status, solver.ObjectiveValue()
    
    return None, None, status, None