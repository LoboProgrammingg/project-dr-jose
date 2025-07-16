# Projeto Dr. José

**Sistema de Conciliação Bancária, Gerenciamento Financeiro e Controle de Devedores para Micro e Pequenos Negócios**

---

## 📋 Sumário

- [Sobre o Projeto](#sobre-o-projeto)
- [Principais Funcionalidades](#principais-funcionalidades)
- [Arquitetura e Tecnologias](#arquitetura-e-tecnologias)
    - [Django](#django)
    - [Pandas](#pandas)
    - [openpyxl & xlsxwriter](#openpyxl--xlsxwriter)
    - [ofxparse](#ofxparse)
    - [Outras Bibliotecas](#outras-bibliotecas)
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

Com foco em **usabilidade, segurança e precisão**, o sistema reduz drasticamente o tempo gasto com tarefas financeiras repetitivas, minimiza erros humanos e fornece uma visão clara da saúde financeira do negócio.

---

## Principais Funcionalidades

- **Importação de Extratos Bancários (OFX):** Suporte a arquivos padrão utilizados pelos bancos brasileiros.
- **Importação de Planilhas Financeiras (CSV):** Compatível com exportações do sistema eGestor.
- **Conciliação Automatizada:** Cruzamento inteligente entre registros bancários e registros internos.
- **Identificação de Pendências e Divergências:** Destaca lançamentos presentes em apenas um dos lados ou com valores divergentes.
- **Geração de Relatórios Profissionais:** Exportação em Excel com formatação condicional para facilitar a análise.
- **Controle de Devedores:** Identificação de inadimplentes e acompanhamento de receitas/pendências.
- **Interface Responsiva:** Desenvolvido para uso via web (Django), acessível de qualquer dispositivo.

---

## Arquitetura e Tecnologias

### Django

O **Django** é o framework web fundamental do projeto, responsável por:

- Estruturar o backend da aplicação, fornecendo rotas, autenticação e integração com banco de dados.
- Organizar a lógica de negócio por meio do padrão MTV (Model-Template-View).
- Oferecer segurança nativa (proteção contra CSRF, XSS, SQL Injection etc.).
- Permitir fácil extensão via APIs ou módulos.

### Pandas

O **Pandas** é utilizado para:

- Leitura e tratamento de grandes volumes de dados financeiros (CSV e OFX).
- Conversão, limpeza e transformação dos dados em DataFrames.
- Realização de joins, filtros, agrupamentos e cálculos necessários para a conciliação.
- Geração de relatórios e exportação para Excel.

### openpyxl & xlsxwriter

- **openpyxl:** Permite leitura e manipulação de planilhas Excel (.xlsx) já existentes.
- **xlsxwriter:** Utilizado para criação de relatórios Excel sofisticados, com formatação condicional, diretamente na memória, prontos para download.

### ofxparse

- **ofxparse:** Biblioteca dedicada ao parsing de extratos bancários no formato OFX, padrão utilizado por bancos brasileiros. Permite transformar arquivos de extrato em objetos Python, facilitando a extração de transações.

### Outras Bibliotecas

- **numpy:** Suporte matemático e otimização de operações em arrays numéricos.
- **pdfminer.six, pdfplumber, pypdfium2:** Suporte a leitura e tratamento de PDFs (caso necessário para relatórios ou extratos).
- **beautifulsoup4, lxml:** Parsing e tratamento de dados em HTML/XML, caso seja necessário importar dados de portais bancários.
- **cryptography, cffi:** Suporte a criptografia e manipulação segura de dados sensíveis.
- **pandas, sqlparse, python-dateutil, pytz, tzdata:** Suporte completo a manipulação de datas, horários e SQL.

---

## Explicação do Código Principal

O núcleo do sistema de conciliação está em `conciliacao/services.py`. Abaixo, uma explicação detalhada:

### Fluxo da Conciliação

1. **Importação dos arquivos**: O usuário envia um arquivo OFX (extrato bancário) e um arquivo CSV (planilha do sistema interno, como eGestor).
2. **Processamento dos arquivos**: Cada arquivo é lido, processado e convertido em DataFrames Pandas padronizados.
3. **Conciliação**: O sistema compara os lançamentos de ambos, identificando transações coincidentes, divergentes e pendentes.
4. **Geração de relatório**: Um DataFrame final é criado com o status de cada transação, que é então exportado para um arquivo Excel formatado.

### Explicação das Funções

#### 1. `limpar_valor_csv`
- **Função:** Normaliza valores financeiros (removendo símbolos, espaços, trocando vírgulas por pontos, etc.) e converte para float, garantindo precisão na comparação.
- **Exemplo:** Converte `"R$ 1.234,56"` em `1234.56`.

#### 2. `processar_banco_ofx`
- **Função:** Lê o arquivo OFX em memória, decodificando em UTF-8 ou Latin-1, faz o parse com a ofxparse e extrai transações como DataFrame. Cada linha recebe data, histórico, valor e código bancário.
- **Destaque:** Tenta diferentes codificações para garantir robustez contra arquivos de diferentes bancos.

#### 3. `carregar_egestor_csv`
- **Função:** Lê o CSV do sistema interno, padroniza os nomes das colunas, converte datas e valores, aplica a limpeza de valores e retorna DataFrame pronto para conciliação.

#### 4. `gerar_dataframe_conciliacao`
- **Função:** Realiza o cruzamento entre os DataFrames do banco e do sistema interno por data e valor arredondado. Marca transações como:
    - **Conciliadas:** Encontradas em ambos com o mesmo valor e data.
    - **Divergentes:** Mesma data, mas valores diferentes.
    - **Pendentes:** Presentes apenas no banco ou apenas no sistema interno.
- **Resultado:** DataFrame final com status, diferença de valores e detalhes históricos.

#### 5. `criar_arquivo_excel`
- **Função:** Gera, em memória, um arquivo Excel formatado, com:
    - Cabeçalhos destacados.
    - Coloração condicional (verde para conciliado, vermelho para divergente, amarelo para pendente).
    - Formatação de datas e valores no padrão brasileiro.
    - Pronto para download pelo usuário.

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
   No navegador, acesse [http://localhost:8000](http://localhost:8000)

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
4. Envie a branch para o seu fork:
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