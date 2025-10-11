# optimizer.py
from ortools.sat.python import cp_model
import json

def resolver_grade(dados, creditos_minimos, NUM_SEMESTRES, CREDITOS_MAXIMOS_POR_SEMESTRE, proximo_periodo_tipo):
    """
    Cria e resolve o modelo de otimização da grade horária.
    """
    model = cp_model.CpModel()

    disciplinas = dados["disciplinas"]
    turmas_por_disciplina = dados["turmas_por_disciplina"]
    horarios_por_turma = dados["horarios_por_turma"]
    periodos_validos_por_disciplina = dados["periodos_validos_por_disciplina"]
    obrigatorias_ids = dados["obrigatorias_ids"]
    restritas_ids = dados["restritas_ids"]
    condicionadas_ids = dados["condicionadas_ids"]
    livres_ids = dados["livres_ids"]
    ids_optativas = restritas_ids + condicionadas_ids + livres_ids

    with open('./data/disciplinas.json', 'r', encoding='utf-8') as f:
        todas_disciplinas = json.load(f)
        total_creditos_obrigatorios = sum(d.get('creditos', 0) for d in todas_disciplinas if "Período" in d.get('tipo', ''))
    creditos_para_estagio_threshold = int(total_creditos_obrigatorios / 2)

    alocacao = {}
    for d_id in disciplinas:
        periodos_validos = periodos_validos_por_disciplina.get(d_id, {1, 2})
        oferta_em_periodo_1, oferta_em_periodo_2 = 1 in periodos_validos, 2 in periodos_validos
        for t_id in turmas_por_disciplina.get(d_id, []):
            for s in range(1, NUM_SEMESTRES + 1):
                eh_semestre_impar_no_plano = (s % 2 != 0)
                if proximo_periodo_tipo == 'impar':
                    pode_cursar_em_periodo_1, pode_cursar_em_periodo_2 = eh_semestre_impar_no_plano, not eh_semestre_impar_no_plano
                else:
                    pode_cursar_em_periodo_1, pode_cursar_em_periodo_2 = not eh_semestre_impar_no_plano, eh_semestre_impar_no_plano
                if (pode_cursar_em_periodo_1 and oferta_em_periodo_1) or \
                   (pode_cursar_em_periodo_2 and oferta_em_periodo_2):
                    alocacao[(d_id, s, t_id)] = model.NewBoolVar(f'alocacao_{d_id}_s{s}_t{t_id}')
    
    semestre_da_disciplina = {d_id: model.NewIntVar(1, NUM_SEMESTRES + 1, f'semestre_{d_id}') for d_id in disciplinas}
    cursada_vars = {}
    for d_id in obrigatorias_ids: model.AddExactlyOne([var for key, var in alocacao.items() if key[0] == d_id])
    for d_id in ids_optativas: model.AddAtMostOne([var for key, var in alocacao.items() if key[0] == d_id])
    for d_id in disciplinas:
        cursada = model.NewBoolVar(f'cursada_{d_id}'); cursada_vars[d_id] = cursada
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
    termos_creditos_restritas = [int(disciplinas[d_id]['creditos']) * cursada_vars[d_id] for d_id in restritas_ids]
    if termos_creditos_restritas: model.Add(sum(termos_creditos_restritas) >= creditos_minimos['restrita'])
    termos_creditos_condicionadas = [int(disciplinas[d_id]['creditos']) * cursada_vars[d_id] for d_id in condicionadas_ids]
    if termos_creditos_condicionadas: model.Add(sum(termos_creditos_condicionadas) >= creditos_minimos['condicionada'])
    termos_creditos_livres = [int(disciplinas[d_id]['creditos']) * cursada_vars[d_id] for d_id in livres_ids]
    if termos_creditos_livres: model.Add(sum(termos_creditos_livres) >= creditos_minimos['livre'])
    for d_id, disc_info in disciplinas.items():
        for prereq_id in disc_info.get('prerequisitos', []):
            if prereq_id in semestre_da_disciplina: model.Add(semestre_da_disciplina[d_id] > semestre_da_disciplina[prereq_id])
    for s in range(1, NUM_SEMESTRES + 1):
        horarios_do_semestre = {}
        for (d, sem, t), var in alocacao.items():
            if sem == s:
                for h in horarios_por_turma.get(t, []):
                    if h not in horarios_do_semestre: horarios_do_semestre[h] = []
                    horarios_do_semestre[h].append(var)
        for h, turmas_conflitantes in horarios_do_semestre.items(): model.AddAtMostOne(turmas_conflitantes)
    for s in range(1, NUM_SEMESTRES + 1):
        termos_de_credito = [int(disciplinas[d_id]['creditos']) * var for (d_id, sem, t_id), var in alocacao.items() if sem == s]
        if termos_de_credito: model.Add(sum(termos_de_credito) <= CREDITOS_MAXIMOS_POR_SEMESTRE)
    
    creditos_acumulados_por_semestre = {s: model.NewIntVar(0, 500, f'creditos_acumulados_s{s}') for s in range(NUM_SEMESTRES + 1)}
    model.Add(creditos_acumulados_por_semestre[0] == 0)
    for s in range(1, NUM_SEMESTRES + 1):
        creditos_neste_semestre_expr = sum(int(disciplinas[d_id]['creditos']) * var for (d_id, sem, t_id), var in alocacao.items() if sem == s)
        model.Add(creditos_acumulados_por_semestre[s] == creditos_acumulados_por_semestre[s-1] + creditos_neste_semestre_expr)
    id_estagio = "EEWU00"
    if id_estagio in disciplinas:
        for s in range(1, NUM_SEMESTRES + 1):
            estagio_neste_semestre_vars = [var for (d, sem, t), var in alocacao.items() if d == id_estagio and sem == s]
            if estagio_neste_semestre_vars:
                estagio_cursado_em_s = model.NewBoolVar(f'estagio_cursado_em_s{s}')
                model.Add(sum(estagio_neste_semestre_vars) >= 1).OnlyEnforceIf(estagio_cursado_em_s)
                model.Add(sum(estagio_neste_semestre_vars) == 0).OnlyEnforceIf(estagio_cursado_em_s.Not())
                model.Add(creditos_acumulados_por_semestre[s-1] >= creditos_para_estagio_threshold).OnlyEnforceIf(estagio_cursado_em_s)

    # --- 5. Definir a Função Objetivo (CORRIGIDO) ---
    semestre_maximo = model.NewIntVar(1, NUM_SEMESTRES + 1, 'semestre_maximo')
    
    # Queremos minimizar o último semestre em que o aluno está ATIVO (cursando qualquer matéria).
    semestres_ativos_vars = []
    for s in range(1, NUM_SEMESTRES + 1):
        # Var booleana que é verdadeira se o aluno cursa QUALQUER matéria no semestre 's'
        ativo_em_s = model.NewBoolVar(f'ativo_em_s{s}')
        
        # Pega todas as variáveis de alocação para o semestre 's'
        alocacoes_no_semestre_s = [var for (d, sem, t), var in alocacao.items() if sem == s]
        
        if alocacoes_no_semestre_s:
            # Se a soma das alocações for > 0, o aluno está ativo.
            model.Add(sum(alocacoes_no_semestre_s) > 0).OnlyEnforceIf(ativo_em_s)
            model.Add(sum(alocacoes_no_semestre_s) == 0).OnlyEnforceIf(ativo_em_s.Not())
        else:
            model.Add(ativo_em_s == 0) # Nenhuma matéria pode ser cursada neste semestre
            
        # Otimizador maximizará o termo s * ativo_em_s.
        # Se ativo_em_s for 1, o termo é 's'. Se for 0, o termo é 0.
        semestres_ativos_vars.append(s * ativo_em_s)
    
    # semestre_maximo será o maior 's' para o qual 'ativo_em_s' é verdadeiro.
    if semestres_ativos_vars:
        model.AddMaxEquality(semestre_maximo, semestres_ativos_vars)
    else: # Caso não haja nenhuma disciplina a ser cursada.
        model.Add(semestre_maximo == 1)

    model.Minimize(semestre_maximo)
    # --- FIM DA CORREÇÃO ---

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        grade = {s: [] for s in range(1, NUM_SEMESTRES + 1)}
        creditos_por_semestre = {s: 0 for s in range(1, NUM_SEMESTRES + 1)}
        for (d_id, s, t_id), var in alocacao.items():
            if solver.Value(var):
                string_disciplina = f'{disciplinas[d_id]["nome"]} (Turma: {t_id}) --- Horários: [{", ".join(horarios_por_turma.get(t_id, []))}]'
                grade[s].append(string_disciplina)
                creditos_por_semestre[s] += int(disciplinas[d_id]['creditos'])
        return grade, creditos_por_semestre, status, solver.ObjectiveValue()
    
    return None, None, status, None