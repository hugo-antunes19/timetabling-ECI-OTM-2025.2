# optimizerMILP.py

from ortools.linear_solver import pywraplp

def resolver_grade(dados, creditos_minimos, NUM_SEMESTRES, CREDITOS_MAXIMOS_POR_SEMESTRE):
    """
    Cria e resolve o modelo de otimização da grade horária usando MILP.
    (Com a lógica de pré-requisitos R4 correta)
    """
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        print("Solver SCIP não encontrado.")
        return None, None, -1, None
        
    infinity = solver.infinity()

    # Extrai os dados
    disciplinas = dados["disciplinas"]
    turmas_por_disciplina = dados["turmas_por_disciplina"]
    horarios_por_turma = dados["horarios_por_turma"]
    periodos_validos_por_disciplina = dados["periodos_validos_por_disciplina"]
    obrigatorias_ids = dados["obrigatorias_ids"]
    restritas_ids = dados["restritas_ids"]
    condicionadas_ids = dados["condicionadas_ids"]
    livres_ids = dados["livres_ids"]
    ids_optativas = restritas_ids + condicionadas_ids + livres_ids

    # --- 3. Variáveis de Decisão ---
    alocacao = {}
    for d_id in disciplinas:
        periodos_validos = periodos_validos_por_disciplina.get(d_id, {1, 2})
        oferta_em_impar = 1 in periodos_validos
        oferta_em_par = 2 in periodos_validos

        for t_id in turmas_por_disciplina.get(d_id, []):
            for s in range(1, NUM_SEMESTRES + 1):
                is_semestre_impar = (s % 2 != 0)
                if (is_semestre_impar and oferta_em_impar) or (not is_semestre_impar and oferta_em_par):
                    alocacao[(d_id, s, t_id)] = solver.BoolVar(f'alocacao_{d_id}_s{s}_t{t_id}')

    semestre_da_disciplina = {
        d_id: solver.IntVar(1, NUM_SEMESTRES + 1, f'semestre_{d_id}')
        for d_id in disciplinas
    }
    
    cursada_vars = {}

    # --- 4. Restrições ---

    # R1.1: Obrigatórias (Exatamente uma vez)
    for d_id in obrigatorias_ids:
        vars_obrigatoria = [var for key, var in alocacao.items() if key[0] == d_id]
        solver.Add(solver.Sum(vars_obrigatoria) == 1)

    # R1.2: Optativas (No máximo uma vez)
    for d_id in ids_optativas:
        vars_optativa = [var for key, var in alocacao.items() if key[0] == d_id]
        solver.Add(solver.Sum(vars_optativa) <= 1)

    # R2: Ligação (Linearizada)
    for d_id in disciplinas:
        cursada_var = solver.Sum([var for key, var in alocacao.items() if key[0] == d_id])
        cursada_vars[d_id] = cursada_var 

        termos_semestre = []
        for (d, s, t), var in alocacao.items():
            if d == d_id:
                termos_semestre.append(s * var)
        
        solver.Add(semestre_da_disciplina[d_id] == solver.Sum(termos_semestre) + (1 - cursada_var) * (NUM_SEMESTRES + 1))

    # R3: Créditos Mínimos (Linear)
    if restritas_ids:
        solver.Add(solver.Sum(int(disciplinas[d_id]['creditos']) * cursada_vars[d_id] for d_id in restritas_ids) >= creditos_minimos['restrita'])
    if condicionadas_ids:
        solver.Add(solver.Sum(int(disciplinas[d_id]['creditos']) * cursada_vars[d_id] for d_id in condicionadas_ids) >= creditos_minimos['condicionada'])
    if livres_ids:
        solver.Add(solver.Sum(int(disciplinas[d_id]['creditos']) * cursada_vars[d_id] for d_id in livres_ids) >= creditos_minimos['livre'])

    # --- R4: Pré-requisitos (CORRIGIDA DE ACORDO COM SUA REGRA) ---
    M_prereq = NUM_SEMESTRES + 1 

    for d_id, disc_info in disciplinas.items():
        for prereq_id in disc_info.get('prerequisitos', []):
            if prereq_id in semestre_da_disciplina:
                
                # R4.1: REGRA DE IMPLICAÇÃO
                # Se cursar 'd_id', TEM que cursar 'prereq_id'.
                # (cursada[pre] >= cursada[d])
                solver.Add(cursada_vars[prereq_id] >= cursada_vars[d_id])

                # R4.2: REGRA DE ORDENAÇÃO (Big-M)
                # Se cursar 'd_id', o semestre de 'd_id' deve ser maior que o de 'prereq_id'.
                # (semestre[d] - semestre[pre] >= 1 - M*(1-cursada[d]))
                solver.Add(semestre_da_disciplina[d_id] - semestre_da_disciplina[prereq_id] >= 
                           1 - M_prereq * (1 - cursada_vars[d_id]))


    # R5: Conflitos de Horário (Linear)
    for s in range(1, NUM_SEMESTRES + 1):
        horarios_do_semestre = {}
        for (d, sem, t), var in alocacao.items():
            if sem == s:
                for h in horarios_por_turma.get(t, []):
                    if h not in horarios_do_semestre: horarios_do_semestre[h] = []
                    horarios_do_semestre[h].append(var)
        for h, turmas_conflitantes in horarios_do_semestre.items():
            solver.Add(solver.Sum(turmas_conflitantes) <= 1)

    # R6: Limite de Créditos por Semestre (Linear)
    for s in range(1, NUM_SEMESTRES + 1):
        termos_de_credito = []
        for d_id in disciplinas:
            creditos = int(disciplinas[d_id]['creditos'])
            cursada_neste_semestre_vars = [var for (d, sem, t), var in alocacao.items() if d == d_id and sem == s]
            if cursada_neste_semestre_vars: 
                termos_de_credito.append(creditos * solver.Sum(cursada_neste_semestre_vars))
        if termos_de_credito: 
            solver.Add(solver.Sum(termos_de_credito) <= CREDITOS_MAXIMOS_POR_SEMESTRE)

    # R7: Regras Específicas (Linear)
    id_estagio = "EEWU00"
    if id_estagio in semestre_da_disciplina:
        solver.Add(semestre_da_disciplina[id_estagio] >= 6)
    
    # --- 5. Função Objetivo (Corrigida) ---
    # Minimizar o semestre máximo de TODAS as disciplinas CURSADAS
    
    semestre_maximo = solver.IntVar(1, NUM_SEMESTRES, 'semestre_maximo')
    M_obj = NUM_SEMESTRES + 1 

    for d_id in disciplinas:
        # Forma linear: semestre_maximo >= semestre[d] - M * (1 - cursada[d])
        solver.Add(semestre_maximo >= semestre_da_disciplina[d_id] - M_obj * (1 - cursada_vars[d_id]))

    solver.Minimize(semestre_maximo)

    # --- 6. Chamar o Solver ---
    solver.set_time_limit(120 * 1000) 
    status = solver.Solve()
    
    # --- 7. Processar e Retornar os Resultados ---
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        grade = {s: [] for s in range(1, NUM_SEMESTRES + 1)}
        creditos_por_semestre = {s: 0 for s in range(1, NUM_SEMESTRES + 1)}

        for (d_id, s, t_id), var in alocacao.items():
            if var.solution_value() > 0.5:
                string_disciplina = f'{disciplinas[d_id]["nome"]} (Turma: {t_id}) --- Horários: [{", ".join(horarios_por_turma.get(t_id, []))}]'
                grade[s].append(string_disciplina)
                creditos_por_semestre[s] += disciplinas[d_id]['creditos']
        
        return grade, creditos_por_semestre, status, solver.Objective().Value()
    
    return None, None, status, None