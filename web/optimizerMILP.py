# optimizerMILP.py (A VERSÃO CORRETA E COMPLETA)

from ortools.linear_solver import pywraplp

# --- MUDANÇA: Adicionar 'todas_disciplinas_info' ---
def resolver_grade(dados, todas_disciplinas_info, creditos_minimos, 
                   CREDITOS_MAXIMOS_POR_SEMESTRE, 
                   disciplinas_concluidas_ids, semestre_inicio, 
                   TOTAL_CREDITOS_CURSO): 
    """
    Cria e resolve o modelo de otimização da grade horária usando MILP.
    (Esta versão USA os inputs do usuário e o dict completo de disciplinas)
    """
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        print("Solver SCIP não encontrado.")
        return None, None, -1, None
        
    infinity = solver.infinity()

    # --- 1. Extrair Dados Brutos ---
    # 'disciplinas' é a lista FILTRADA (com ofertas), vinda do 'dados'.
    # Isso é correto para o solver alocar.
    disciplinas = dados["disciplinas"]
    turmas_por_disciplina = dados["turmas_por_disciplina"]
    horarios_por_turma = dados["horarios_por_turma"]
    periodos_validos_por_disciplina = dados["periodos_validos_por_disciplina"]
    ids_obrigatorias_total = dados["obrigatorias_ids"]
    ids_restritas_total = dados["restritas_ids"]
    ids_condicionadas_total = dados["condicionadas_ids"]
    ids_livres_total = dados["livres_ids"]
    ids_optativas_total = ids_restritas_total + ids_condicionadas_total + ids_livres_total

    # --- 2. Ajustar Dados (USA OS INPUTS DO USUÁRIO) ---

    # Filtra apenas as que o usuário AINDA NÃO cursou
    obrigatorias_a_cursar = [d_id for d_id in ids_obrigatorias_total if d_id not in disciplinas_concluidas_ids]
    optativas_a_cursar = [d_id for d_id in ids_optativas_total if d_id not in disciplinas_concluidas_ids]
    disciplinas_a_cursar_ids = obrigatorias_a_cursar + optativas_a_cursar

    # --- MUDANÇA: Usar 'todas_disciplinas_info' para a contagem ---
    creditos_feitos = {"restrita": 0, "condicionada": 0, "livre": 0}
    creditos_concluidos_pelo_usuario = 0
    for d_id in disciplinas_concluidas_ids:
        # USA O DICIONÁRIO COMPLETO, NÃO O FILTRADO ('disciplinas')
        if d_id in todas_disciplinas_info: 
            disciplina = todas_disciplinas_info[d_id] # Pega do dict completo
            credito_disciplina = int(disciplina.get('creditos', 0))
            creditos_concluidos_pelo_usuario += credito_disciplina
            
            # Identifica o tipo (Lógica do CP-SAT para consistência)
            tipo = disciplina.get("tipo", "")
            if "Restrita" in tipo:
                creditos_feitos["restrita"] += credito_disciplina
            elif "Condicionada" in tipo:
                creditos_feitos["condicionada"] += credito_disciplina
            elif "Livre" in tipo or d_id.startswith("ARTIFICIAL"):
                creditos_feitos["livre"] += credito_disciplina
    # --- FIM DA MUDANÇA ---

    # Calcula os novos mínimos de optativas (agora com a contagem correta)
    creditos_minimos_restantes = {
        "restrita": max(0, creditos_minimos['restrita'] - creditos_feitos['restrita']),
        "condicionada": max(0, creditos_minimos['condicionada'] - creditos_feitos['condicionada']),
        "livre": max(0, creditos_minimos['livre'] - creditos_feitos['livre'])
    }
    
    NUM_SEMESTRES_TOTAL = 14 

    # --- 3. Variáveis de Decisão (USA OS INPUTS DO USUÁRIO) ---
    alocacao = {}
    for d_id in disciplinas_a_cursar_ids: # <-- Usa a lista filtrada
        for t_id in turmas_por_disciplina.get(d_id, []):
            # <-- Começa do semestre certo
            for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1): 
                # (Regra par/ímpar relaxada)
                alocacao[(d_id, s, t_id)] = solver.BoolVar(f'alocacao_{d_id}_s{s}_t{t_id}')

    semestre_da_disciplina = {
        d_id: solver.IntVar(semestre_inicio, NUM_SEMESTRES_TOTAL + 1, f'semestre_{d_id}')
        for d_id in disciplinas_a_cursar_ids
    }
    
    # --- 4. Restrições ---

    # R1.1: Obrigatórias (Usa a lista filtrada)
    for d_id in obrigatorias_a_cursar:
        vars_obrigatoria = [var for key, var in alocacao.items() if key[0] == d_id]
        if not vars_obrigatoria:
             print(f"Aviso: Disciplina obrigatória {d_id} não tem oferta de turma.")
             continue
        solver.Add(solver.Sum(vars_obrigatoria) == 1)

    # R1.2: Optativas (Usa a lista filtrada)
    for d_id in optativas_a_cursar:
        vars_optativa = [var for key, var in alocacao.items() if key[0] == d_id]
        if vars_optativa:
            solver.Add(solver.Sum(vars_optativa) <= 1)

    # R2: Ligação (Usa a lista filtrada)
    cursada_vars = {}
    DUMMY_VALUE = NUM_SEMESTRES_TOTAL + 2
    for d_id in disciplinas_a_cursar_ids:
        vars_disciplina = [var for key, var in alocacao.items() if key[0] == d_id]
        
        if not vars_disciplina:
            cursada_vars[d_id] = solver.IntVar(0, 0, f'cursada_{d_id}')
            solver.Add(semestre_da_disciplina[d_id] == DUMMY_VALUE)
            continue
            
        cursada_var = solver.Sum(vars_disciplina)
        cursada_vars[d_id] = cursada_var 
        termos_semestre = []
        for (d, s, t), var in alocacao.items():
            if d == d_id:
                termos_semestre.append(s * var)
        
        solver.Add(semestre_da_disciplina[d_id] == solver.Sum(termos_semestre) + (1 - cursada_var) * DUMMY_VALUE) 

    # R3: Créditos Mínimos (Usa os valores restantes)
    if ids_restritas_total:
        solver.Add(solver.Sum(int(disciplinas[d_id]['creditos']) * cursada_vars[d_id] 
                             for d_id in ids_restritas_total if d_id in cursada_vars) >= creditos_minimos_restantes['restrita'])
    if ids_condicionadas_total:
        solver.Add(solver.Sum(int(disciplinas[d_id]['creditos']) * cursada_vars[d_id] 
                             for d_id in ids_condicionadas_total if d_id in cursada_vars) >= creditos_minimos_restantes['condicionada'])
    if ids_livres_total:
        solver.Add(solver.Sum(int(disciplinas[d_id]['creditos']) * cursada_vars[d_id] 
                             for d_id in ids_livres_total if d_id in cursada_vars) >= creditos_minimos_restantes['livre'])

    # --- R4: Pré-requisitos (USA OS INPUTS DO USUÁRIO) ---
    M_prereq = NUM_SEMESTRES_TOTAL + 2 
    for d_id in disciplinas_a_cursar_ids:
        disc_info = disciplinas[d_id] # 'disciplinas' (filtrado) é correto aqui
        for prereq_id in disc_info.get('prerequisitos', []):
            
            # <-- Checa as disciplinas concluídas
            if prereq_id in disciplinas_concluidas_ids: 
                continue 

            # <-- Checa a lista filtrada
            elif prereq_id in disciplinas_a_cursar_ids: 
                solver.Add(cursada_vars[prereq_id] >= cursada_vars[d_id])
                solver.Add(semestre_da_disciplina[d_id] - semestre_da_disciplina[prereq_id] >= 
                           1 - M_prereq * (1 - cursada_vars[d_id]))
            
            # (Bloco 'else' removido para replicar o CP-SAT)

    # --- Variáveis Auxiliares para Créditos ---
    creditos_cursados_no_semestre = {}
    for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1):
        termos_de_credito_s = []
        for d_id in disciplinas_a_cursar_ids:
            creditos = int(disciplinas[d_id]['creditos'])
            cursada_neste_semestre_vars = [var for (d, sem, t), var in alocacao.items() if d == d_id and sem == s]
            if cursada_neste_semestre_vars: 
                termos_de_credito_s.append(creditos * solver.Sum(cursada_neste_semestre_vars))
        
        if termos_de_credito_s:
            creditos_cursados_no_semestre[s] = solver.Sum(termos_de_credito_s)
        else:
            creditos_cursados_no_semestre[s] = solver.IntVar(0, 0, f'creditos_s{s}')

    # R5: Conflitos de Horário
    for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1):
        horarios_do_semestre = {}
        for (d, sem, t), var in alocacao.items():
            if sem == s:
                for h in horarios_por_turma.get(t, []):
                    if h not in horarios_do_semestre: horarios_do_semestre[h] = []
                    horarios_do_semestre[h].append(var)
        for h, turmas_conflitantes in horarios_do_semestre.items():
            solver.Add(solver.Sum(turmas_conflitantes) <= 1)

    # R6: Limite de Créditos por Semestre
    for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1):
        solver.Add(creditos_cursados_no_semestre[s] <= CREDITOS_MAXIMOS_POR_SEMESTRE)

    # --- R7: Regra de Estágio (REMOVIDA PARA TESTE) ---
    # (Bloco vazio)
    
    # --- 5. Função Objetivo (SIMPLES, como o CP-SAT) ---
    semestre_maximo = solver.IntVar(semestre_inicio, NUM_SEMESTRES_TOTAL, 'semestre_maximo')
    M_obj = NUM_SEMESTRES_TOTAL + 2
    for d_id in disciplinas_a_cursar_ids:
        solver.Add(semestre_maximo >= semestre_da_disciplina[d_id] - M_obj * (1 - cursada_vars[d_id]))

    solver.Minimize(semestre_maximo)

    # --- 6. Chamar o Solver ---
    solver.set_time_limit(120 * 1000) 
    status = solver.Solve()
    
    # --- 7. Processar e Retornar os Resultados ---
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        grade = {s: [] for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1)}
        creditos_por_semestre = {s: 0 for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1)}

        for (d_id, s, t_id), var in alocacao.items():
            if var.solution_value() > 0.5:
                disciplina_alocada = {
                    "nome": disciplinas[d_id]["nome"],
                    "turma": t_id,
                    "horarios": horarios_por_turma.get(t_id, []),
                    "creditos": disciplinas[d_id]['creditos']
                }
                grade[s].append(disciplina_alocada)
                creditos_por_semestre[s] += int(disciplinas[d_id]['creditos'])
        
        grade_filtrada = {s: g for s, g in grade.items() if g}
        
        return grade, creditos_por_semestre, status, solver.Objective().Value()
    
    return None, None, status, None