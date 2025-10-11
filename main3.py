# main.py
import time
from ortools.sat.python import cp_model
from data_loader import carregar_dados
from optimizer import resolver_grade
from visualizer import gerar_visualizacao_html, imprimir_grade_terminal

def main():
    start_time = time.time()

    # --- Parâmetros ---
    CAMINHO_DISCIPLINAS = './attempt1/disciplinas.json'
    CAMINHO_OFERTAS = './attempt1/ofertas.json'
    NUM_SEMESTRES = 10
    CREDITOS_MAXIMOS_POR_SEMESTRE = 32

    # --- NOVO: Definir os créditos mínimos para cada categoria ---
    # Nota: Usei 8 para 'restrita' conforme seu texto. A tabela indicava 4.
    # Você pode ajustar esses valores facilmente aqui.
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

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f'\nSolução encontrada em {time.time() - start_time:.2f} segundos.')
        print(f'Número mínimo de semestres: {obj_value}')
        imprimir_grade_terminal(grade, creditos)
        gerar_visualizacao_html(grade, creditos)
    elif status == cp_model.INFEASIBLE:
        print('\nNenhuma solução encontrada: O modelo é infactível.')
        print('Verifique se a combinação de restrições é possível.')
    else:
        print('Nenhuma solução encontrada: O solver parou por outro motivo (ex: tempo limite).')

if __name__ == '__main__':
    main()