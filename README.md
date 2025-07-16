# Projeto Dr. José

**Sistema de Conciliação Bancária, Gerenciamento Financeiro e Controle de Devedores para Micro e Pequenos Negócios**

---

## 📋 Sumário

- [Sobre o Projeto](#sobre-o-projeto)
- [Principais Funcionalidades](#principais-funcionalidades)
- [Como as Bibliotecas São Utilizadas](#como-as-bibliotecas-são-utilizadas)
    - [Django](#django)
    - [Pandas](#pandas)
    - [openpyxl & xlsxwriter](#openpyxl--xlsxwriter)
    - [ofxparse](#ofxparse)
- [Explicação do Código Principal](#explicação-do-código-principal)
    - [Fluxo da Conciliação](#fluxo-da-conciliação)
    - [Explicação das Funções](#explicação-das-funções)
- [Como Executar o Projeto](#como-executar-o-projeto)
- [Como Contribuir](#como-contribuir)
- [Licença](#licença)
- [Contato](#contato)

---

## Sobre o Projeto

O **Projeto Dr. José** foi criado para automatizar a conciliação bancária e o controle financeiro de micro e pequenos negócios. Ele facilita a importação de extratos bancários (formato OFX), planilhas de receitas/despesas (CSV), realiza o cruzamento automático das informações, identifica divergências e gera relatórios profissionais em Excel.

---

## Principais Funcionalidades

- Importação de extratos bancários (OFX)
- Importação de planilhas financeiras (CSV)
- Conciliação automática entre dados bancários e internos
- Identificação de divergências e pendências
- Geração de relatórios em Excel com formatação especial
- Controle de devedores e inadimplentes
- Interface web responsiva

---

## Como as Bibliotecas São Utilizadas

### Django

O Django estrutura toda a aplicação web, fornecendo rotas, autenticação, painéis de administração e integração com o banco de dados. Toda a lógica de upload dos arquivos, disparo dos processos de conciliação e exibição dos relatórios acontece através de views e templates Django. As funções de processamento financeiro ficam centralizadas em módulos Python, integrados às views do Django.

### Pandas

No projeto, o Pandas é usado para ler, transformar e manipular os dados dos extratos bancários (OFX) e das planilhas do sistema interno (CSV). Ele permite:

- Ler arquivos CSV e transformar em DataFrames para fácil manipulação.
- Padronizar datas, valores e históricos financeiros.
- Realizar junções (merge) entre diferentes conjuntos de dados para encontrar correspondências, divergências e pendências.
- Gerar o DataFrame final que serve de base para os relatórios exportados.

### openpyxl & xlsxwriter

Essas bibliotecas são utilizadas para exportar os dados conciliados em formato Excel. O xlsxwriter é particularmente utilizado para criar o arquivo Excel em memória, com:

- Cabeçalhos personalizados e coloridos.
- Formatação condicional (células verdes para conciliados, vermelhas para divergências, amarelas para pendentes).
- Formatação de valores e datas conforme padrão brasileiro.
- Geração do arquivo pronto para download na interface web.

O openpyxl pode ser utilizado caso seja necessário ler planilhas Excel vindas de outros sistemas.

### ofxparse

A ofxparse é responsável por ler e interpretar os extratos bancários em formato OFX enviados pelo usuário. Ela transforma os arquivos em objetos Python, permitindo extrair facilmente informações como data, valor, histórico e código da transação bancária. Esses dados são então convertidos em DataFrames do Pandas para todo o processamento posterior.

---

## Explicação do Código Principal

O núcleo do sistema de conciliação está em `conciliacao/services.py`.

### Fluxo da Conciliação

1. **Upload dos arquivos**: O usuário envia um arquivo OFX do banco e um CSV do sistema interno.
2. **Processamento**:
    - O arquivo OFX é lido via ofxparse e convertido em DataFrame Pandas.
    - O CSV é lido pelo Pandas, suas colunas e valores são padronizados e normalizados.
3. **Conciliação**:
    - Utilizando Pandas, os dois DataFrames são cruzados por data e valor.
    - São identificadas transações conciliadas, divergentes e pendentes.
4. **Relatório**:
    - Um DataFrame final é criado com status e diferenças.
    - O xlsxwriter gera um arquivo Excel formatado, pronto para download.

### Explicação das Funções

- **`limpar_valor_csv`**: Normaliza e converte valores financeiros lidos de CSV para float, facilitando a comparação.
- **`processar_banco_ofx`**: Converte o extrato bancário OFX em DataFrame Pandas, extraindo todas as transações.
- **`carregar_egestor_csv`**: Lê o CSV do sistema interno, ajusta colunas, datas e valores, e retorna DataFrame padronizado.
- **`gerar_dataframe_conciliacao`**: Faz o “match” entre lançamentos bancários e internos, atribuindo status a cada lançamento. 
- **`criar_arquivo_excel`**: Usa xlsxwriter para montar um arquivo Excel formatado com todos os resultados da conciliação.

---

## Como Executar o Projeto

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/LoboProgrammingg/project-dr-jose.git
   cd project-dr-jose
   ```
2. **Crie um ambiente virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Realize as migrações do banco de dados:**
   ```bash
   python manage.py migrate
   ```
5. **Inicie o servidor:**
   ```bash
   python manage.py runserver
   ```
6. **Acesse a aplicação:**  
   [http://localhost:8000](http://localhost:8000)

---

## Como Contribuir

1. Faça um fork do projeto.
2. Crie uma branch para sua feature/correção:
   ```bash
   git checkout -b minha-feature
   ```
3. Realize commits das alterações:
   ```bash
   git commit -m "Minha contribuição"
   ```
4. Envie para seu fork:
   ```bash
   git push origin minha-feature
   ```
5. Abra um Pull Request detalhando suas mudanças.

---

## Licença

[Defina aqui a licença do projeto, ex: MIT License]

---

## Contato

Desenvolvido por [LoboProgrammingg](https://github.com/LoboProgrammingg)  
Dúvidas ou sugestões? Abra uma [issue](https://github.com/LoboProgrammingg/project-dr-jose/issues) ou envie um e-mail para o mantenedor do projeto.

---