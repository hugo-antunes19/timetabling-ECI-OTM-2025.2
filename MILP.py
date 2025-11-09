# main3.py
import time
from ortools.linear_solver import pywraplp # <<< MUDANÇA AQUI
from data_loader import carregar_dados
from optimizerMILP import resolver_grade
from visualizer import gerar_visualizacao_html, imprimir_grade_terminal

def main():
    start_time = time.time()

    # --- Parâmetros ---
    CAMINHO_DISCIPLINAS = './attempt1/disciplinas.json'
    CAMINHO_OFERTAS = './attempt1/ofertas.json'
    NUM_SEMESTRES = 10
    CREDITOS_MAXIMOS_POR_SEMESTRE = 32

    # --- NOVO: Definir os créditos mínimos para cada categoria ---
    CREDITOS_MINIMOS = {
        "restrita": 4,
        "condicionada": 40,
        "livre": 8
    }

    try:
        dados = carregar_dados(CAMINHO_DISCIPLINAS, CAMINHO_OFERTAS)
    except FileNotFoundError as e:
        print(f"Erro ao carregar dados: {e}")
        return

    grade, creditos, status, obj_value = resolver_grade(
        dados, CREDITOS_MINIMOS, NUM_SEMESTRES, CREDITOS_MAXIMOS_POR_SEMESTRE
    )

    # --- MUDANÇA AQUI: Verificar os códigos de status do solver MILP ---
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        print(f'\nSolução encontrada em {time.time() - start_time:.2f} segundos.')
        print(f'Número mínimo de semestres: {obj_value}')
        imprimir_grade_terminal(grade, creditos)
        gerar_visualizacao_html(grade, creditos)
    elif status == pywraplp.Solver.INFEASIBLE:
        print('\nNenhuma solução encontrada: O modelo é infactível.')
        print('Verifique se a combinação de restrições é possível.')
    else:
        print(f'\nNenhuma solução encontrada: O solver parou por outro motivo (status: {status}).')

if __name__ == '__main__':
    main()