meu_projeto/                  
├── .gitignore                  <-- (Recomendado) Para ignorar arquivos no Git
├── db.sqlite3
├── manage.py
├── README.md                   <-- (Recomendado) Descrição do projeto
├── requirements.txt            <-- (Essencial) Dependências do projeto
│
├── config/                     
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py             <-- Configurações principais (precisa de ajuste)
│   ├── urls.py                 <-- URLs raiz do projeto
│   └── wsgi.py
│
├── conciliacao/                
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── services.py
│   ├── urls.py
│   └── views.py
│
├── credores/                   
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
│
├── planilhas/                  
│   ├── __init__.py
│   ├── admin.py
│   ├── forms.py
│   ├── models.py
│   ├── services.py
│   ├── urls.py
│   └── views.py
│
├── static/                     
│   └── img/                    <-- Suas imagens de layout ficam aqui
│
├── media/                      <-- Para uploads de usuários (vazio inicialmente)
│
└── templates/                  
    ├── base.html
    ├── dashboard.html
    ├── home.html
    ├── login.html
    │
    ├── conciliacao/
    │   ├── detalhe_relatorio.html
    │   ├── instrucoes_ofx.html
    │   ├── lista_relatorios.html
    │   └── upload.html
    │
    ├── credores/
    │   ├── credor_confirm_delete.html
    │   ├── credor_detail.html
    │   ├── credor_form.html
    │   └── credor_list.html
    │
    └── planilhas/
        ├── detalhe_ano.html
        ├── detalhe_planilha.html
        ├── detalhe_planilha_nativa.html
        ├── editor_planilha_nativa.html
        ├── lista_anos.html
        ├── planilha_confirm_delete.html
        ├── planilha_form.html
        └── planilha_nativa_form.html