# optimizerMILP.py

from ortools.linear_solver import pywraplp

def resolver_grade(dados, creditos_minimos, CREDITOS_MAXIMOS_POR_SEMESTRE, 
                   disciplinas_concluidas_ids, semestre_inicio):
    """
    Cria e resolve o modelo de otimização da grade horária usando MILP.
    (Modificado para aceitar disciplinas concluídas e semestre inicial)
    """
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        print("Solver SCIP não encontrado.")
        return None, None, -1, None
        
    infinity = solver.infinity()

    # --- 1. Extrair Dados Brutos ---
    disciplinas = dados["disciplinas"]
    turmas_por_disciplina = dados["turmas_por_disciplina"]
    horarios_por_turma = dados["horarios_por_turma"]
    periodos_validos_por_disciplina = dados["periodos_validos_por_disciplina"]

    # --- 2. Ajustar Dados com base nas Entradas do Usuário ---

    # A. Definir quais IDs de disciplina o solver deve considerar
    ids_obrigatorias_total = dados["obrigatorias_ids"]
    ids_restritas_total = dados["restritas_ids"]
    ids_condicionadas_total = dados["condicionadas_ids"]
    ids_livres_total = dados["livres_ids"]
    ids_optativas_total = ids_restritas_total + ids_condicionadas_total + ids_livres_total

    # Filtra apenas as que o usuário AINDA NÃO cursou
    obrigatorias_a_cursar = [d_id for d_id in ids_obrigatorias_total if d_id not in disciplinas_concluidas_ids]
    optativas_a_cursar = [d_id for d_id in ids_optativas_total if d_id not in disciplinas_concluidas_ids]
    disciplinas_a_cursar_ids = obrigatorias_a_cursar + optativas_a_cursar

    # B. Ajustar Créditos Mínimos
    # Calcula quantos créditos o usuário JÁ FEZ em cada categoria
    creditos_feitos = {"restrita": 0, "condicionada": 0, "livre": 0}
    for d_id in disciplinas_concluidas_ids:
        if d_id in disciplinas: # Garante que a disciplina concluída está nos dados
            if d_id in ids_restritas_total:
                creditos_feitos["restrita"] += int(disciplinas[d_id]['creditos'])
            elif d_id in ids_condicionadas_total:
                creditos_feitos["condicionada"] += int(disciplinas[d_id]['creditos'])
            elif d_id in ids_livres_total:
                creditos_feitos["livre"] += int(disciplinas[d_id]['creditos'])

    # Calcula os novos mínimos, garantindo que não sejam negativos
    creditos_minimos_restantes = {
        "restrita": max(0, creditos_minimos['restrita'] - creditos_feitos['restrita']),
        "condicionada": max(0, creditos_minimos['condicionada'] - creditos_feitos['condicionada']),
        "livre": max(0, creditos_minimos['livre'] - creditos_feitos['livre'])
    }
    
    # C. Definir o horizonte de semestres
    # Vamos assumir um máximo de 14 semestres totais para dar folga
    NUM_SEMESTRES_TOTAL = 14 

    # --- 3. Variáveis de Decisão ---
    alocacao = {}
    for d_id in disciplinas_a_cursar_ids:
        periodos_validos = periodos_validos_por_disciplina.get(d_id, {1, 2})
        oferta_em_impar = 1 in periodos_validos
        oferta_em_par = 2 in periodos_validos

        for t_id in turmas_por_disciplina.get(d_id, []):
            # Otimização: O solver só precisa variar do semestre inicial em diante
            for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1):
                is_semestre_impar = (s % 2 != 0)
                if (is_semestre_impar and oferta_em_impar) or (not is_semestre_impar and oferta_em_par):
                    alocacao[(d_id, s, t_id)] = solver.BoolVar(f'alocacao_{d_id}_s{s}_t{t_id}')

    semestre_da_disciplina = {
        d_id: solver.IntVar(semestre_inicio, NUM_SEMESTRES_TOTAL + 1, f'semestre_{d_id}')
        for d_id in disciplinas_a_cursar_ids
    }
    
    # --- 4. Restrições ---

    # R1.1: Obrigatórias (Exatamente uma vez, *das restantes*)
    for d_id in obrigatorias_a_cursar:
        vars_obrigatoria = [var for key, var in alocacao.items() if key[0] == d_id]
        solver.Add(solver.Sum(vars_obrigatoria) == 1)

    # R1.2: Optativas (No máximo uma vez, *das restantes*)
    for d_id in optativas_a_cursar:
        vars_optativa = [var for key, var in alocacao.items() if key[0] == d_id]
        solver.Add(solver.Sum(vars_optativa) <= 1)

    # R2: Ligação (Linearizada)
    cursada_vars = {}
    for d_id in disciplinas_a_cursar_ids:
        cursada_var = solver.Sum([var for key, var in alocacao.items() if key[0] == d_id])
        cursada_vars[d_id] = cursada_var 

        termos_semestre = []
        for (d, s, t), var in alocacao.items():
            if d == d_id:
                termos_semestre.append(s * var)
        
        # O valor "dummy" deve estar fora do range total
        solver.Add(semestre_da_disciplina[d_id] == solver.Sum(termos_semestre) + (1 - cursada_var) * (NUM_SEMESTRES_TOTAL + 2)) 

    # R3: Créditos Mínimos (Usando os *restantes*)
    if ids_restritas_total: # Usamos os IDs totais para filtrar as variáveis
        solver.Add(solver.Sum(int(disciplinas[d_id]['creditos']) * cursada_vars[d_id] 
                             for d_id in ids_restritas_total if d_id in cursada_vars) >= creditos_minimos_restantes['restrita'])
    if ids_condicionadas_total:
        solver.Add(solver.Sum(int(disciplinas[d_id]['creditos']) * cursada_vars[d_id] 
                             for d_id in ids_condicionadas_total if d_id in cursada_vars) >= creditos_minimos_restantes['condicionada'])
    if ids_livres_total:
        solver.Add(solver.Sum(int(disciplinas[d_id]['creditos']) * cursada_vars[d_id] 
                             for d_id in ids_livres_total if d_id in cursada_vars) >= creditos_minimos_restantes['livre'])

    # --- R4: Pré-requisitos (MODIFICADA) ---
    M_prereq = NUM_SEMESTRES_TOTAL + 2 

    for d_id in disciplinas_a_cursar_ids:
        disc_info = disciplinas[d_id]
        for prereq_id in disc_info.get('prerequisitos', []):
            
            # Caso 1: O pré-requisito JÁ FOI CONCLUÍDO pelo usuário
            if prereq_id in disciplinas_concluidas_ids:
                continue # Nenhuma restrição necessária, pré-requisito satisfeito

            # Caso 2: O pré-requisito AINDA PRECISA SER CURSADO
            elif prereq_id in disciplinas_a_cursar_ids:
                # R4.1: REGRA DE IMPLICAÇÃO (Se cursar D, tem que cursar PRÉ)
                solver.Add(cursada_vars[prereq_id] >= cursada_vars[d_id])

                # R4.2: REGRA DE ORDENAÇÃO (Big-M)
                solver.Add(semestre_da_disciplina[d_id] - semestre_da_disciplina[prereq_id] >= 
                           1 - M_prereq * (1 - cursada_vars[d_id]))
            
            # Caso 3: O pré-requisito não foi concluído e não está disponível (ex: não ofertado)
            # A disciplina d_id não poderá ser cursada (R4.1 vai falhar), o que está correto.

    # R5: Conflitos de Horário (Linear)
    for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1):
        horarios_do_semestre = {}
        for (d, sem, t), var in alocacao.items():
            if sem == s:
                for h in horarios_por_turma.get(t, []):
                    if h not in horarios_do_semestre: horarios_do_semestre[h] = []
                    horarios_do_semestre[h].append(var)
        for h, turmas_conflitantes in horarios_do_semestre.items():
            solver.Add(solver.Sum(turmas_conflitantes) <= 1)

    # R6: Limite de Créditos por Semestre (Linear)
    for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1):
        termos_de_credito = []
        for d_id in disciplinas_a_cursar_ids:
            creditos = int(disciplinas[d_id]['creditos'])
            cursada_neste_semestre_vars = [var for (d, sem, t), var in alocacao.items() if d == d_id and sem == s]
            if cursada_neste_semestre_vars: 
                termos_de_credito.append(creditos * solver.Sum(cursada_neste_semestre_vars))
        if termos_de_credito: 
            solver.Add(solver.Sum(termos_de_credito) <= CREDITOS_MAXIMOS_POR_SEMESTRE)

    # R7: Regras Específicas (Linear)
    id_estagio = "EEWU00"
    if id_estagio in semestre_da_disciplina:
        # A restrição original (>= 6) está mantida. 
        # Se semestre_inicio for 7, a var semestre_da_disciplina[id_estagio] já começa em 7.
        solver.Add(semestre_da_disciplina[id_estagio] >= 6)
    
    # --- 5. Função Objetivo (Corrigida) ---
    # Minimizar o semestre máximo de TODAS as disciplinas CURSADAS (a partir do semestre_inicio)
    
    semestre_maximo = solver.IntVar(semestre_inicio, NUM_SEMESTRES_TOTAL, 'semestre_maximo')
    M_obj = NUM_SEMESTRES_TOTAL + 2

    for d_id in disciplinas_a_cursar_ids:
        solver.Add(semestre_maximo >= semestre_da_disciplina[d_id] - M_obj * (1 - cursada_vars[d_id]))

    solver.Minimize(semestre_maximo)

    # --- 6. Chamar o Solver ---
    solver.set_time_limit(120 * 1000) # 2 minutos de timeout
    status = solver.Solve()
    
    # --- 7. Processar e Retornar os Resultados ---
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        # Inicializa a grade SOMENTE para os semestres relevantes
        grade = {s: [] for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1)}
        creditos_por_semestre = {s: 0 for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1)}

        for (d_id, s, t_id), var in alocacao.items():
            if var.solution_value() > 0.5:
                
                # --- MUDANÇA AQUI ---
                # Em vez de formatar uma string, retornamos os dados estruturados
                disciplina_alocada = {
                    "nome": disciplinas[d_id]["nome"],
                    "turma": t_id,
                    "horarios": horarios_por_turma.get(t_id, []),
                    "creditos": disciplinas[d_id]['creditos']
                }
                grade[s].append(disciplina_alocada)
                # --- FIM DA MUDANÇA ---
                
                creditos_por_semestre[s] += int(disciplinas[d_id]['creditos'])
        
        # Filtra semestres vazios do resultado final
        grade_filtrada = {s: g for s, g in grade.items() if g}
        
        return grade_filtrada, creditos_por_semestre, status, solver.Objective().Value()
    
    return None, None, status, None