# optimizerMILP.py

from ortools.linear_solver import pywraplp

def resolver_grade(dados, creditos_minimos, CREDITOS_MAXIMOS_POR_SEMESTRE, 
                   disciplinas_concluidas_ids, semestre_inicio, 
                   TOTAL_CREDITOS_CURSO): # <<< NOVO PARÂMETRO
    """
    Cria e resolve o modelo de otimização da grade horária usando MILP.
    (Com a nova regra de estágio baseada em créditos)
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
    ids_obrigatorias_total = dados["obrigatorias_ids"]
    ids_restritas_total = dados["restritas_ids"]
    ids_condicionadas_total = dados["condicionadas_ids"]
    ids_livres_total = dados["livres_ids"]
    ids_optativas_total = ids_restritas_total + ids_condicionadas_total + ids_livres_total

    # --- 2. Ajustar Dados com base nas Entradas do Usuário ---

    # Filtra apenas as que o usuário AINDA NÃO cursou
    obrigatorias_a_cursar = [d_id for d_id in ids_obrigatorias_total if d_id not in disciplinas_concluidas_ids]
    optativas_a_cursar = [d_id for d_id in ids_optativas_total if d_id not in disciplinas_concluidas_ids]
    disciplinas_a_cursar_ids = obrigatorias_a_cursar + optativas_a_cursar

    # Calcula quantos créditos o usuário JÁ FEZ
    creditos_feitos = {"restrita": 0, "condicionada": 0, "livre": 0}
    creditos_concluidos_pelo_usuario = 0
    for d_id in disciplinas_concluidas_ids:
        if d_id in disciplinas: # Garante que a disciplina é conhecida pelo modelo
            credito_disciplina = int(disciplinas[d_id]['creditos'])
            creditos_concluidos_pelo_usuario += credito_disciplina
            if d_id in ids_restritas_total:
                creditos_feitos["restrita"] += credito_disciplina
            elif d_id in ids_condicionadas_total:
                creditos_feitos["condicionada"] += credito_disciplina
            elif d_id in ids_livres_total:
                creditos_feitos["livre"] += credito_disciplina

    # Calcula os novos mínimos de optativas, garantindo que não sejam negativos
    creditos_minimos_restantes = {
        "restrita": max(0, creditos_minimos['restrita'] - creditos_feitos['restrita']),
        "condicionada": max(0, creditos_minimos['condicionada'] - creditos_feitos['condicionada']),
        "livre": max(0, creditos_minimos['livre'] - creditos_feitos['livre'])
    }
    
    # Define o mínimo de créditos para poder cursar o estágio
    CREDITOS_MINIMOS_ESTAGIO = TOTAL_CREDITOS_CURSO / 2.0
    
    # Define o horizonte de semestres
    NUM_SEMESTRES_TOTAL = 14 

    # --- 3. Variáveis de Decisão ---
    alocacao = {}
    for d_id in disciplinas_a_cursar_ids:
        # --- MUDANÇA (TESTE 1): Relaxar a regra Par/Ímpar ---
        # Ignora a lógica de 'periodos_validos', 'oferta_em_impar', etc.
        # Permite que qualquer disciplina seja cursada em qualquer semestre,
        # desde que exista uma turma.

        for t_id in turmas_por_disciplina.get(d_id, []):
            for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1):
                # Aloca a variável sem checar a paridade do semestre
                alocacao[(d_id, s, t_id)] = solver.BoolVar(f'alocacao_{d_id}_s{s}_t{t_id}')

    semestre_da_disciplina = {
        d_id: solver.IntVar(semestre_inicio, NUM_SEMESTRES_TOTAL + 1, f'semestre_{d_id}')
        for d_id in disciplinas_a_cursar_ids
    }
    
    # --- 4. Restrições ---

    # R1.1: Obrigatórias (Exatamente uma vez, *das restantes*)
    for d_id in obrigatorias_a_cursar:
        vars_obrigatoria = [var for key, var in alocacao.items() if key[0] == d_id]
        if not vars_obrigatoria:
             print(f"Aviso: Disciplina obrigatória {d_id} não tem oferta de turma.")
             continue
        solver.Add(solver.Sum(vars_obrigatoria) == 1)

    # R1.2: Optativas (No máximo uma vez, *das restantes*)
    for d_id in optativas_a_cursar:
        vars_optativa = [var for key, var in alocacao.items() if key[0] == d_id]
        if vars_optativa: # Só adiciona restrição se houver oferta
            solver.Add(solver.Sum(vars_optativa) <= 1)

    # R2: Ligação (Linearizada)
    cursada_vars = {}
    DUMMY_VALUE = NUM_SEMESTRES_TOTAL + 2 # Valor "dummy"
    for d_id in disciplinas_a_cursar_ids:
        vars_disciplina = [var for key, var in alocacao.items() if key[0] == d_id]
        
        if not vars_disciplina: # Se não há oferta, não pode ser cursada
            cursada_vars[d_id] = solver.IntVar(0, 0, f'cursada_{d_id}')
            # Define o semestre como DUMMY
            solver.Add(semestre_da_disciplina[d_id] == DUMMY_VALUE)
            continue
            
        cursada_var = solver.Sum(vars_disciplina)
        cursada_vars[d_id] = cursada_var 

        termos_semestre = []
        for (d, s, t), var in alocacao.items():
            if d == d_id:
                termos_semestre.append(s * var)
        
        solver.Add(semestre_da_disciplina[d_id] == solver.Sum(termos_semestre) + (1 - cursada_var) * DUMMY_VALUE) 

    # R3: Créditos Mínimos (Usando os *restantes*)
    if ids_restritas_total:
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
            
            if prereq_id in disciplinas_concluidas_ids:
                continue # Pré-requisito satisfeito

            elif prereq_id in disciplinas_a_cursar_ids:
                solver.Add(cursada_vars[prereq_id] >= cursada_vars[d_id])
                solver.Add(semestre_da_disciplina[d_id] - semestre_da_disciplina[prereq_id] >= 
                           1 - M_prereq * (1 - cursada_vars[d_id]))
            
            # Caso 3: Pré-requisito não foi concluído e não está nas 'a_cursar'
            # (ex: não tem oferta, ou é de outro curso).
            # A disciplina d_id não poderá ser cursada.
            else:
                # Força cursada_vars[d_id] a ser 0, pois seu pré-requisito é impossível.
                solver.Add(cursada_vars[d_id] == 0)


    # --- Variáveis Auxiliares para Créditos (Antes de R5, R6, R7) ---
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

    creditos_acumulados_no_inicio_de = {}
    for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 2): # Até s+1
        
        # --- CORREÇÃO AQUI ---
        # O solver linear (pywraplp) aceita constantes (números) diretamente no Sum()
        termos_acumulados = [creditos_concluidos_pelo_usuario] 
        # --- FIM DA CORREÇÃO ---
        
        # Soma todos os semestres *anteriores* a 's'
        termos_acumulados.extend([
            creditos_cursados_no_semestre[s_prime] 
            for s_prime in range(semestre_inicio, s) # Soma de s_inicio até s-1
            if s_prime in creditos_cursados_no_semestre
        ])
        creditos_acumulados_no_inicio_de[s] = solver.Sum(termos_acumulados)

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

    # R6: Limite de Créditos por Semestre (Usa as variáveis auxiliares)
    for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1):
        solver.Add(creditos_cursados_no_semestre[s] <= CREDITOS_MAXIMOS_POR_SEMESTRE)

    # --- R7: Regra de Estágio (MODIFICADA para Créditos) ---
    id_estagio = "EEWU00"
    if id_estagio in disciplinas_a_cursar_ids: 
        
        # M (Big-M) deve ser um número maior que o mínimo de créditos
        M_estagio = CREDITOS_MINIMOS_ESTAGIO + 1.0 # Usar float é seguro
        
        for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1):
            
            alocado_em_s_vars = [var for (d, sem, t), var in alocacao.items() if d == id_estagio and sem == s]
            
            if alocado_em_s_vars:
                alocado_em_s = solver.Sum(alocado_em_s_vars)
                
                # A REGRA: Se alocado_em_s = 1, ENTÃO creditos_acumulados[s] >= CREDITOS_MINIMOS_ESTAGIO
                # Forma linear (Big-M):
                # creditos_acumulados[s] >= MINIMO - M * (1 - alocado_em_s)
                
                solver.Add(
                    creditos_acumulados_no_inicio_de[s] >= 
                    CREDITOS_MINIMOS_ESTAGIO - M_estagio * (1 - alocado_em_s)
                )

    # --- 5. Função Objetivo (Com "Front-Loading") ---
    
    # Objetivo Primário: Minimizar o semestre máximo
    semestre_maximo = solver.IntVar(semestre_inicio, NUM_SEMESTRES_TOTAL, 'semestre_maximo')
    M_obj = NUM_SEMESTRES_TOTAL + 2
    for d_id in disciplinas_a_cursar_ids:
        solver.Add(semestre_maximo >= semestre_da_disciplina[d_id] - M_obj * (1 - cursada_vars[d_id]))

    # Objetivo Secundário: Minimizar a soma dos semestres (para "encher" os semestres iniciais)
    soma_dos_semestres_terms = []
    for d_id in disciplinas_a_cursar_ids:
        soma_dos_semestres_terms.append(
            semestre_da_disciplina[d_id] - DUMMY_VALUE * (1 - cursada_vars[d_id])
        )
    soma_dos_semestres = solver.Sum(soma_dos_semestres_terms)

    # Ponderação Hierárquica
    PESO_PRIMARIO = 10000
    PESO_SECUNDARIO = 1
    
    solver.Minimize(
        PESO_PRIMARIO * semestre_maximo + PESO_SECUNDARIO * soma_dos_semestres
    )

    # --- 6. Chamar o Solver ---
    solver.set_time_limit(120 * 1000) # 2 minutos de timeout
    status = solver.Solve()
    
    # --- 7. Processar e Retornar os Resultados ---
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        grade = {s: [] for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1)}
        creditos_por_semestre = {s: 0 for s in range(semestre_inicio, NUM_SEMESTRES_TOTAL + 1)}

        for (d_id, s, t_id), var in alocacao.items():
            if var.solution_value() > 0.5:
                # Retorna os dados estruturados
                disciplina_alocada = {
                    "nome": disciplinas[d_id]["nome"],
                    "turma": t_id,
                    "horarios": horarios_por_turma.get(t_id, []),
                    "creditos": disciplinas[d_id]['creditos']
                }
                grade[s].append(disciplina_alocada)
                creditos_por_semestre[s] += int(disciplinas[d_id]['creditos'])
        
        grade_filtrada = {s: g for s, g in grade.items() if g}
        
        # Pega o valor real do semestre máximo (arredondado, pois o obj é ponderado)
        obj_real = round(solver.Objective().Value() / PESO_PRIMARIO)
        
        return grade_filtrada, creditos_por_semestre, status, obj_real
    
    return None, None, status, None