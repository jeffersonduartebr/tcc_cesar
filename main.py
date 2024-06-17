import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.graph_objs as go


import mariadb
import matplotlib.pyplot as plt
import swifter
import dateutil
import datetime
import pandas as pd
import numpy as np

from cachetools import cached, TTLCache
import time
from dataset import criar_dataset, conectar_banco
#time.sleep(15)

import warnings
warnings.filterwarnings("ignore")

try:
    conn = mariadb.connect(host="bd", database = 'dados_tribunais',user="root", passwd="abc@123")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT tribunal FROM processos;")
    tribunais = cursor.fetchall()
    conn.close()

except mariadb.Error as e:
    print(f"Erro ao conectar ou executar a consulta: {e}")

lista_tribunais = [tribunal[0] for tribunal in tribunais]

#print(data_ddf)

app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(label='Visualização', children=[
            html.H1("Visualização de Séries Temporais de Ajuizamentos de Processos", style={
                'textAlign': 'center',
                'fontFamily': 'Arial, sans-serif',
                'color': '#4CAF50',
                'marginTop': '20px'
            }),
            html.Div([
                html.Label("Selecione o Tribunal:", style={
                    'fontFamily': 'Arial, sans-serif',
                    'color': '#333'
                }),
            dcc.Dropdown(
                id='tribunal-dropdown',
                options=[{'label': t, 'value': t} for t in lista_tribunais],
                value=lista_tribunais[1],
                style={'fontFamily': 'Arial, sans-serif'}
            )
            ], style={'width': '50%', 'margin': 'auto', 'padding': '20px'}),

            html.Div([
                html.Label("Selecione a Unidade Jurisdicional:", style={
                    'fontFamily': 'Arial, sans-serif',
                    'color': '#333'
                }),
            dcc.Dropdown(
                id='unidade-judiciaria-dropdown',
                options={},
                style={'fontFamily': 'Arial, sans-serif'}
            )
            ], style={'width': '50%', 'margin': 'auto', 'padding': '20px'}),

            dcc.Graph(id='time-series-chart'),

            html.Div([
                html.Label("Selecione o Intervalo de Datas:", style={
                    'fontFamily': 'Arial, sans-serif',
                    'color': '#333'
                }),
                dcc.DatePickerRange(
                    id='date-picker-range',
                    start_date='2018-01-01',
                    end_date=datetime.datetime.today().strftime('%Y-%m-%d'),
                    display_format='YYYY-MM-DD',
                    style={'fontFamily': 'Arial, sans-serif'}
                )
            ], style={'width': '50%', 'margin': 'auto', 'padding': '20px'})
        ]),

        dcc.Tab(label='Entrada de Dados', children=[
            html.H2("Digite o Nome do Tribunal:", style={'textAlign': 'center'}),
            dcc.Input(id='input-tribunal', type='text', value='', style={'width': '50%', 'margin': 'auto'}),
            html.Div(id='output-metodo', style={'textAlign': 'center'})
        ])
    ])
])

@app.callback(
    Output('unidade-judiciaria-dropdown', 'options'),
    [Input('tribunal-dropdown', 'value')]
)
def update_unidade_judiciarias_dropdown(tribunal_selecionado):
    try:
        mydb = mariadb.connect(host="bd", database = 'dados_tribunais',user="root", passwd="abc@123")
        cursor = mydb.cursor()
        agora = datetime.datetime.now()
        print(agora, ': Iniciando a consulta das unidades jurisdicionais')
        cursor.execute("SELECT DISTINCT orgao_julgador FROM processos WHERE tribunal = '%s' and data_ajuizamento > '2020-01-01';", tribunal_selecionado)
        agora = datetime.datetime.now()
        print(agora, ': Encerrando a consulta das unidades jurisdicionais')
        lista_unidades = cursor.fetchall()
        mydb.close() 
        cursor.close()
    except Exception as e:
        mydb.close()
        cursor.close()
        print(str(e)) 
        print(tribunal_selecionado)
    opcoes_dropdown_unidades = [{'label': unidade[0], 'value': unidade[0]} for unidade in lista_unidades]
    return opcoes_dropdown_unidades


@app.callback(
    Output('output-metodo', 'children'),
    Input('input-tribunal', 'value')
)
def download_dados_tribunais(nome_tribunal):
    if nome_tribunal:
        cursor = conectar_banco()
        criar_dataset(cursor, nome_tribunal, '2024-01-01', 1000)         
    else:
        return "Digite um nome de tribunal válido."

# Definindo cache com Time-To-Live (TTL) de 300 segundos (5 minutos) e capacidade máxima de 100 itens
cache = TTLCache(maxsize=1000, ttl=300)

@cached(cache)
def get_filtered_data(tribunal, unidade_jurisdicional, start_date, end_date):
    try:
        mydb = mariadb.connect(host="bd", database = 'dados_tribunais',user="root", passwd="abc@123")
        query = f"select * from processos where tribunal='{tribunal}' and orgao_julgador = '{unidade_jurisdicional}';"
        df_tribunal = pd.read_sql(query,mydb)
        
        mydb.close() #close the connection
    except Exception as e:
        mydb.close()
        print(str(e))
    
    filtered_data_ddf = df_tribunal[(df_tribunal['data_ajuizamento'] >= start_date) & (df_tribunal['data_ajuizamento'] <= end_date)]
    filtered_data = filtered_data_ddf
    return filtered_data.sort_values(by='data_ajuizamento')

@app.callback(
    Output('time-series-chart', 'figure'),
    [Input('tribunal-dropdown', 'value'),
     Input('unidade-judiciaria-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_graph(tribunal_dropdown, unidade_judiciaria, start_date, end_date):
    filtered_data = get_filtered_data(tribunal_dropdown, unidade_judiciaria, start_date, end_date)
    dataframe = filtered_data.groupby(['data_ajuizamento', 'orgao_julgador']).size()
    data_ddf = dataframe.to_frame(name='quantidade').rename_axis(['data_ajuizamento', 'orgao_julgador']).reset_index()   
    fig = go.Figure(go.Scatter(
        x=data_ddf['data_ajuizamento'],
        y=data_ddf['quantidade'],
        mode='lines+markers',
        name='Ajuizamentos',
        line=dict(color='#1f77b4'),  # Cor da linha
        marker=dict(color='#1f77b4')  # Cor dos marcadores
        ))

    fig.update_layout(
        title={
            'text': f'Série Temporal de Ajuizamentos - {unidade_judiciaria}',
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        title_font=dict(
            family='Arial, sans-serif',
            size=20,
            color='#4CAF50'
        ),
        xaxis_title='Data',
        yaxis_title='Número de Ajuizamentos',
        font=dict(
            family='Arial, sans-serif',
            size=12,
            color='#333'
        ),
        template='plotly_white'
    )

    return fig


if __name__ == '__main__':
    app.run_server(debug=True, port='8050', host='0.0.0.0')
    