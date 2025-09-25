# 📅 Otimizador de Grade Curricular - Engenharia de Computação (UFRJ)

## 📜 Descrição

Este projeto é a implementação de um solver de otimização para a geração de uma grade curricular ótima para o curso de Engenharia de Computação e Informação da UFRJ. O objetivo principal é encontrar a sequência de disciplinas que minimiza o tempo de graduação (número de semestres), respeitando todas as restrições de pré-requisitos, co-requisitos e evitando conflitos de horário.

O projeto foi desenvolvido como trabalho final para a disciplina de Otimização, aplicando conceitos de Pesquisa Operacional e Programação por Restrições a um problema real e complexo.

https://www.siga.ufrj.br/sira/temas/zire/frameConsultas.jsp?mainPage=/repositorio-curriculo/61AD45DD-92A4-F79B-3D87-7A444052DF9B.html - Visitado 25 de Setembro de 2025 às 15:52

Os horários das disciplinas utilizados tiveram como base o histórico delas visto em 25 de Setembro de 2025 às 18:30

## ✨ Funcionalidades

  * **Extração Automática de Dados:** Um script de web scraping (`scraper_ufrj.py`) analisa o HTML oficial da grade curricular da UFRJ e extrai todas as disciplinas, créditos e pré-requisitos.
  * **Modelo de Otimização Robusto:** Utiliza o solver CP-SAT do Google OR-Tools para encontrar uma solução ótima (ou viável) para o problema de alocação de disciplinas.
  * **Geração de Grade Válida:** A grade gerada garante que:
      * Todas as disciplinas obrigatórias sejam cursadas.
      * Todos os pré-requisitos sejam satisfeitos.
      * Não haja conflitos de horário em um mesmo semestre.
  * **Minimização do Tempo de Graduação:** A função objetivo do modelo é minimizar o número total de semestres necessários para concluir o curso.

## 🛠️ Tecnologias Utilizadas

  * **Linguagem:** Python 3
  * **Otimização:** Google OR-Tools (CP-SAT Solver)
  * **Web Scraping:** Beautiful Soup 4
  * **Manipulação de Dados:** JSON

## 📁 Estrutura do Projeto

```
/projeto-otimizacao-grade
|
|-- grade_curricular.html   # O arquivo HTML da grade curricular da UFRJ
|-- scraper_ufrj.py         # Script para extrair os dados do HTML
|-- disciplinas.json        # Arquivo de dados gerado pelo scraper
|-- gerador_grade.py        # O script principal com o solver de otimização
|-- README.md               # Este arquivo
|-- venv/                     # Pasta do ambiente virtual (opcional)
```

## 🚀 Como Executar

Siga os passos abaixo para executar o projeto em sua máquina local.

#### 1\. Pré-requisitos

  * Python 3.8 ou superior
  * Git (opcional, para clonar o repositório)

#### 2\. Instalação

Clone este repositório (ou simplesmente baixe os arquivos):

```bash
git clone https://github.com/hugo-antunes19/timetabling-ECI-OTM-2025.2.git
cd projeto-otimizacao-grade
```

Crie e ative um ambiente virtual:

```bash
# Para Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Para Windows
python -m venv venv
.\venv\Scripts\activate
```

Instale as dependências necessárias:

```bash
pip install ortools beautifulsoup4
```

#### 3\. Execução

O processo é feito em duas etapas:

**Etapa 1: Extrair os dados da grade curricular**

Execute o scraper para gerar o arquivo `disciplinas.json` a partir do `grade_curricular.html`.

```bash
python scraper_ufrj.py
```

Este comando irá ler o HTML, processar todas as disciplinas e salvar um arquivo JSON estruturado.

**Etapa 2: Gerar a grade otimizada**

Com o arquivo `disciplinas.json` criado, execute o solver de otimização.

```bash
python gerador_grade.py
```

O script irá carregar os dados, construir o modelo matemático, resolver o problema e imprimir no terminal a grade curricular ótima, semestre por semestre.

## 🧠 O Modelo de Otimização

O problema foi modelado como um Problema de Satisfação de Restrições (CSP) com otimização.

  * **Objetivo:** Minimizar o número de semestres ativos.
  * **Variáveis de Decisão:** Variáveis binárias $x\_{d,s,t}$ que indicam se a *turma t* da *disciplina d* deve ser cursada no *semestre s*.
  * **Principais Restrições:**
    1.  **Unicidade:** Cada disciplina deve ser cursada exatamente uma vez.
    2.  **Pré-requisitos:** Se uma disciplina $D\_2$ tem $D\_1$ como pré-requisito, o semestre de $D\_2$ deve ser estritamente maior que o semestre de $D\_1$.
    3.  **Não-Conflito:** Para um dado semestre e horário, no máximo uma disciplina pode ser alocada.
    4.  **Limite de Créditos (a implementar):** A soma dos créditos em um semestre não pode exceder um limite máximo.

## 📈 Possíveis Melhorias

  - [ ] Implementar uma interface de usuário mais amigável (CLI com `argparse` ou web com `Streamlit`).
  - [ ] Adicionar mais restrições personalizáveis (ex: preferência por turno, evitar "buracos" na grade, limite de créditos).
  - [ ] Considerar a oferta real de disciplinas, já que nem todas são ofertadas em todos os semestres.
  - [ ] Modelar a alocação de disciplinas optativas de forma mais flexível (ex: "cursar 20 créditos do grupo de optativas X").
  - [ ] Permitir que o usuário informe quais disciplinas já foram cursadas.

## 👤 Autor

**Hugo Antunes**

  * **Email:** `hugoleandroantunes@gmail.com`
  * **GitHub:** `[hugo-antunes19](https://github.com/hugo-antunes19)`
  * **LinkedIn:** `[seu-linkedin](https://www.linkedin.com/in/hugo-antunes-08a76b213/)`

## 📄 Licença

Este projeto está sob a licença MIT.

## O que encontramos até o momento

--- Semestre 1 (Créditos: 28.0) ---
  - Algoritmos e Programação (Turma: COS110T1) --- Horários: [SEG-13-15, QUA-13-15, SEX-13-15]
  - Banco de Dados (Turma: EEL871T1) --- Horários: [SEG-08-10, SEX-07-10]
  - Computacao Grafica (Turma: EEL882T1) --- Horários: [TER-15-17, QUI-15-17]
  - Física Experimental I (Turma: FIS111T1) --- Horários: [TER-08-10]
  - Física I - a (Turma: FIT112T4) --- Horários: [QUA-15-17, SEX-15-17]
  - Gestão de Conhecimento I (Turma: COP232T1) --- Horários: [QUA-08-12]
  - Introd Eng Comput e Informação (Turma: COS111T1) --- Horários: [QUI-13-15]
  - Sistemas Distribuídos (Turma: COS470T1) --- Horários: [TER-10-12, QUI-10-12]

--- Semestre 2 (Créditos: 27.0) ---
  - Computadores e Sociedade (Turma: COS471T1) --- Horários: [TER-13-15, QUI-13-15]
  - Cálculo Difer e Integral I (Turma: MAC118T4) --- Horários: [SEG-15-17, QUA-15-17, SEX-15-17]
  - Empreendedorismo I (Turma: COP364T1) --- Horários: [SEX-08-12]
  - Física Experimental II (Turma: FIS121T2) --- Horários: [SEX-08-10]
  - Química Ee (Turma: IQG111T1) --- Horários: [TER-08-10, QUI-08-10]
  - Redes de Computadores II (Turma: EEL879T1) --- Horários: [SEG-10-12, QUA-10-12]
  - Álgebra Linear (Turma: MAE125T4) --- Horários: [TER-15-17, QUI-15-17]

--- Semestre 3 (Créditos: 22.0) ---
  - Circuitos Logicos (Turma: EEL280T1) --- Horários: [TER-10-12, TER-13-15, QUI-10-12]
  - Computação de Alto Desempenho (Turma: COC472T1) --- Horários: [SEX-08-12]
  - Cálculo Diferen e Integral II (Turma: MAC128T4) --- Horários: [SEG-15-17, QUA-15-17]
  - Estruturas de Dados (Turma: COS231T1) --- Horários: [QUA-13-15, SEX-13-15]
  - Física Experimental III (Turma: FIN231T1) --- Horários: [SEX-15-17]
  - Redes de Computadores I (Turma: EEL878T1) --- Horários: [SEG-10-12, QUA-10-13]

--- Semestre 4 (Créditos: 30.0) ---
  - Cálculo Diferen e Integral III (Turma: MAC238T1) --- Horários: [TER-10-12, QUI-10-12]
  - Cálculo Diferen e Integral IV (Turma: MAC248T3) --- Horários: [QUA-15-17, SEX-15-17]
  - Engenharia de Software (Turma: EEL873T1) --- Horários: [TER-08-10, QUI-08-10]
  - Física Experimental IV (Turma: FIN241T1) --- Horários: [SEG-15-17]
  - Inteligência Computacional (Turma: COC361T1) --- Horários: [TER-15-17, QUI-15-17]
  - Linguagens de Programacao (Turma: EEL670T1) --- Horários: [SEG-08-10, SEX-08-10, SEX-10-12]
  - Telecomunicações (Turma: COE363T1) --- Horários: [TER-13-15, QUI-13-15]
  - Teorias dos Grafos (Turma: COS242T1) --- Horários: [SEG-13-15, QUA-13-15]

--- Semestre 5 (Créditos: 21.0) ---
  - Algebra Linear Computacional (Turma: COC473T1) --- Horários: [TER-08-10, QUI-08-10]
  - Arquitetura de Computadores (Turma: EEL580T1) --- Horários: [TER-13-15, QUI-12-15]
  - Física II - a (Turma: FIT122T2) --- Horários: [QUA-15-17, SEX-15-17]
  - Física III - a (Turma: FIM230T2) --- Horários: [QUA-10-12, SEX-10-12]
  - Lógica Matemática (Turma: COS351T1) --- Horários: [TER-10-12, QUI-10-12]

--- Semestre 6 (Créditos: 21.0) ---
  - Construção de Bancos de Dados (Turma: COS480T1) --- Horários: [SEG-10-12, QUA-10-12]
  - Estatística e Mod. Probabilist (Turma: COE241T1) --- Horários: [TER-15-17, QUI-15-17]
  - Otimização (Turma: COS360T1) --- Horários: [SEG-08-10, QUA-08-10]
  - Qualidade de Software (Turma: COS482T1) --- Horários: [TER-10-12, QUI-10-12]
  - Sistemas Digitais (Turma: EEL480T1) --- Horários: [TER-08-10, TER-13-15, QUI-08-10]

--- Semestre 7 (Créditos: 19.0) ---
  - Física IV - a (Turma: FIM240T1) --- Horários: [QUA-08-10, SEX-08-10]
  - Programação Avançada (Turma: EEL418T1) --- Horários: [SEG-15-17, SEX-15-17]
  - Quimica Experimental EE (Turma: IQG112T1) --- Horários: [QUA-13-17]
  - Sistemas Operacionais (Turma: EEL770T1) --- Horários: [TER-15-17, QUI-15-17]
  - Teoria da Computacao (Turma: EEL881T1) --- Horários: [TER-08-12, QUI-08-10, QUI-10-12]