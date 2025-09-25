import json
from ortools.sat.python import cp_model

def gerar_grade_otimizada():
    # --- 1. Carregar os Dados ---
    with open('disciplinas.json', 'r') as f:
        disciplinas_data = json.load(f)
    with open('ofertas.json', 'r') as f:
        ofertas_data = json.load(f)

    # Parâmetros do modelo
    NUM_SEMESTRES = 4  # Definimos um horizonte máximo de semestres
    
    # Estruturas de dados auxiliares para facilitar o acesso
    disciplinas = {d['id']: d for d in disciplinas_data}
    
    todos_horarios = set()
    for oferta in ofertas_data:
        for horario in oferta['horario']:
            todos_horarios.add(horario)
    
    # --- 2. Criar o Modelo ---
    model = cp_model.CpModel()

    # --- 3. Criar as Variáveis de Decisão ---
    # alocacao[d, s, t] = 1 se a turma t da disciplina d for cursada no semestre s
    alocacao = {}
    for oferta in ofertas_data:
        d_id = oferta['disciplina_id']
        t_id = oferta['turma_id']
        for s in range(1, NUM_SEMESTRES + 1):
            alocacao[(d_id, s, t_id)] = model.NewBoolVar(f'alocacao_{d_id}_s{s}_t{t_id}')

    # --- 4. Adicionar as Restrições ---

    # R1: Cada disciplina obrigatória deve ser cursada exatamente uma vez.
    for d_id in disciplinas:
        turmas_da_disciplina = [v for k, v in alocacao.items() if k[0] == d_id]
        model.Add(sum(turmas_da_disciplina) == 1)

    # R2: Sem conflitos de horário no mesmo semestre.
    for s in range(1, NUM_SEMESTRES + 1):
        for h in todos_horarios:
            # Pega todas as turmas que usam o horário h
            turmas_no_horario = []
            for oferta in ofertas_data:
                if h in oferta['horario']:
                    d_id = oferta['disciplina_id']
                    t_id = oferta['turma_id']
                    turmas_no_horario.append(alocacao[(d_id, s, t_id)])
            
            # No máximo uma pode ser escolhida
            model.Add(sum(turmas_no_horario) <= 1)
    
    # R3: Respeitar pré-requisitos.
    for d_id, disc_info in disciplinas.items():
        for prereq_id in disc_info['prerequisitos']:
            # Para cada semestre s, se a disciplina d_id for cursada nele,
            # então o pré-requisito prereq_id deve ter sido cursado em um semestre anterior (1 até s-1).

            # Variáveis que indicam se uma disciplina foi cursada ATÉ um semestre s'
            cursou_disciplina_ate_s = [model.NewBoolVar(f'cursou_{d_id}_ate_s{s_prime}') for s_prime in range(NUM_SEMESTRES + 1)]
            cursou_prereq_ate_s = [model.NewBoolVar(f'cursou_{prereq_id}_ate_s{s_prime}') for s_prime in range(NUM_SEMESTRES + 1)]
            
            for s in range(1, NUM_SEMESTRES + 1):
                # Define o significado das variáveis auxiliares
                turmas_d = [v for k, v in alocacao.items() if k[0] == d_id and k[1] <= s]
                model.Add(sum(turmas_d) == 1).OnlyEnforceIf(cursou_disciplina_ate_s[s])
                model.Add(sum(turmas_d) == 0).OnlyEnforceIf(cursou_disciplina_ate_s[s].Not())

                turmas_prereq = [v for k, v in alocacao.items() if k[0] == prereq_id and k[1] <= s]
                model.Add(sum(turmas_prereq) == 1).OnlyEnforceIf(cursou_prereq_ate_s[s])
                model.Add(sum(turmas_prereq) == 0).OnlyEnforceIf(cursou_prereq_ate_s[s].Not())

                # A restrição de fato: Se d_id foi cursada até s, então prereq_id tem que ter sido cursado até s-1.
                model.AddImplication(cursou_disciplina_ate_s[s], cursou_prereq_ate_s[s-1])

    # --- 5. Definir a Função Objetivo ---
    # Minimizar o número de semestres usados.
    # Criamos uma variável y_s para cada semestre, que é 1 se ele for usado.
    semestres_usados = [model.NewBoolVar(f'semestre_usado_s{s}') for s in range(1, NUM_SEMESTRES + 1)]

    for s in range(1, NUM_SEMESTRES + 1):
        # Se qualquer disciplina for alocada no semestre s, então semestres_usados[s-1] deve ser 1.
        disciplinas_no_semestre = [v for k, v in alocacao.items() if k[1] == s]
        model.Add(sum(disciplinas_no_semestre) > 0).OnlyEnforceIf(semestres_usados[s-1])
        model.Add(sum(disciplinas_no_semestre) == 0).OnlyEnforceIf(semestres_usados[s-1].Not())

    model.Minimize(sum(semestres_usados))

    # --- 6. Chamar o Solver ---
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # --- 7. Exibir os Resultados ---
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f'Solução encontrada em {solver.WallTime()} segundos.')
        print(f'Número mínimo de semestres: {int(solver.ObjectiveValue())}')
        
        grade = {s: [] for s in range(1, NUM_SEMESTRES + 1)}
        for (d_id, s, t_id), var in alocacao.items():
            if solver.Value(var) == 1:
                grade[s].append(f'{disciplinas[d_id]["nome"]} (Turma: {t_id})')
        
        for s, disciplinas_semestre in grade.items():
            if disciplinas_semestre:
                print(f'\n--- Semestre {s} ---')
                for d_str in disciplinas_semestre:
                    print(f'  - {d_str}')
    else:
        print('Nenhuma solução encontrada.')


if __name__ == '__main__':
    gerar_grade_otimizada()