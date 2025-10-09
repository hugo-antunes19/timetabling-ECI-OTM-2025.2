import json

def find_prerequisite_cycle(disciplinas_file):
    """
    Lê o arquivo de disciplinas, constrói um grafo de pré-requisitos
    e procura por qualquer dependência circular (ciclo).
    """
    try:
        with open(disciplinas_file, 'r') as f:
            disciplinas_data = json.load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo '{disciplinas_file}' não encontrado.")
        return

    # Constrói o grafo: {disciplina: [lista_de_prerequisitos]}
    graph = {d['id']: d.get('prerequisitos', []) for d in disciplinas_data}
    
    # Conjuntos para controlar os nós durante a busca em profundidade (DFS)
    visiting = set()  # Nós no caminho de recursão atual
    visited = set()   # Nós que já foram completamente explorados

    for node_id in graph:
        if node_id not in visited:
            # Tenta encontrar um ciclo a partir de cada nó não visitado
            cycle_path = find_cycle_util(node_id, graph, visiting, visited, [])
            if cycle_path:
                print("\n--- PROBLEMA ENCONTRADO! ---")
                print("Foi identificada uma dependência circular (ciclo) nos seus pré-requisitos:")
                print(" -> ".join(reversed(cycle_path)))
                print("\nIsso cria uma contradição lógica que torna o modelo impossível de resolver.")
                print("Para corrigir, revise a cadeia de pré-requisitos acima no seu arquivo 'disciplinas.json'.")
                return

    print("\n--- DIAGNÓSTICO CONCLUÍDO ---")
    print("Nenhum ciclo de pré-requisitos foi encontrado.")
    print("Isso sugere que a inviabilidade do modelo pode ser causada pela interação de múltiplas restrições (ex: pré-requisitos + conflitos de horário + limite de créditos).")


def find_cycle_util(node_id, graph, visiting, visited, path):
    """Função auxiliar recursiva para a busca em profundidade (DFS)."""
    visiting.add(node_id)
    path.append(node_id)

    if node_id in graph:
        for prereq_id in graph[node_id]:
            # Se o pré-requisito não existe na lista de disciplinas, ignora
            if prereq_id not in graph:
                continue

            # Se encontramos um nó que já está sendo visitado na busca atual, achamos um ciclo!
            if prereq_id in visiting:
                # Retorna o caminho do ciclo para exibição
                cycle_start_index = path.index(prereq_id)
                return path[cycle_start_index:] + [prereq_id]
            
            # Se o pré-requisito ainda não foi explorado, continua a busca a partir dele
            if prereq_id not in visited:
                result = find_cycle_util(prereq_id, graph, visiting, visited, path)
                if result:
                    return result
    
    # Marca o nó como totalmente explorado e o remove do caminho atual
    visiting.remove(node_id)
    visited.add(node_id)
    path.pop()
    return None


if __name__ == '__main__':
    # Altere o caminho se o seu arquivo disciplinas.json estiver em outro lugar
    find_prerequisite_cycle('./attempt1/disciplinas.json')