# optimizer.py
from ortools.sat.python import cp_model

def resolver_grade(dados, NUM_SEMESTRES, CREDITOS_MAXIMOS_POR_SEMESTRE):
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

    # --- 3. Criar as Variáveis de Decisão ---
    alocacao = {}
    for d_id in disciplinas:
        periodos_validos = periodos_validos_por_disciplina.get(d_id, {1, 2})
        oferta_em_impar = 1 in periodos_validos
        oferta_em_par = 2 in periodos_validos

        for t_id in turmas_por_disciplina[d_id]:
            for s in range(1, NUM_SEMESTRES + 1):
                is_semestre_impar = (s % 2 != 0)
                if (is_semestre_impar and oferta_em_impar) or (not is_semestre_impar and oferta_em_par):
                    alocacao[(d_id, s, t_id)] = model.NewBoolVar(f'alocacao_{d_id}_s{s}_t{t_id}')

    semestre_da_disciplina = {
        d_id: model.NewIntVar(1, NUM_SEMESTRES, f'semestre_{d_id}')
        for d_id in disciplinas
    }

    # --- 4. Adicionar as Restrições ---
    for d_id in disciplinas:
        model.AddExactlyOne([var for key, var in alocacao.items() if key[0] == d_id])

    for d_id in disciplinas:
        for s in range(1, NUM_SEMESTRES + 1):
            turmas_no_semestre_s = [alocacao[key] for key in alocacao if key[0] == d_id and key[1] == s]
            cursada_em_s = model.NewBoolVar(f'{d_id}_cursada_em_s{s}')
            if not turmas_no_semestre_s: model.Add(cursada_em_s == 0)
            else:
                model.Add(sum(turmas_no_semestre_s) == 1).OnlyEnforceIf(cursada_em_s)
                model.Add(sum(turmas_no_semestre_s) == 0).OnlyEnforceIf(cursada_em_s.Not())
            model.Add(semestre_da_disciplina[d_id] == s).OnlyEnforceIf(cursada_em_s)
            model.Add(semestre_da_disciplina[d_id] != s).OnlyEnforceIf(cursada_em_s.Not())

    for d_id, disc_info in disciplinas.items():
        for prereq_id in disc_info.get('prerequisitos', []):
            if prereq_id in semestre_da_disciplina:
                model.Add(semestre_da_disciplina[d_id] > semestre_da_disciplina[prereq_id])

    for s in range(1, NUM_SEMESTRES + 1):
        horarios_do_semestre = {}
        for (d, sem, t), var in alocacao.items():
            if sem == s:
                for h in horarios_por_turma[t]:
                    if h not in horarios_do_semestre: horarios_do_semestre[h] = []
                    horarios_do_semestre[h].append(var)
        for h, turmas_conflitantes in horarios_do_semestre.items():
            model.AddAtMostOne(turmas_conflitantes)

    for s in range(1, NUM_SEMESTRES + 1):
        termos_de_credito = []
        for d_id, disc_info in disciplinas.items():
            creditos = int(disc_info['creditos'])
            cursada_neste_semestre_vars = [var for (d, sem, t), var in alocacao.items() if d == d_id and sem == s]
            if cursada_neste_semestre_vars: termos_de_credito.append(creditos * sum(cursada_neste_semestre_vars))
        if termos_de_credito: model.Add(sum(termos_de_credito) <= CREDITOS_MAXIMOS_POR_SEMESTRE)

    # --- 5. Definir a Função Objetivo ---
    semestre_maximo = model.NewIntVar(1, NUM_SEMESTRES, 'semestre_maximo')
    model.AddMaxEquality(semestre_maximo, list(semestre_da_disciplina.values()))
    model.Minimize(semestre_maximo)

    # --- 6. Chamar o Solver ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0
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