import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import dask.dataframe as dd

import mariadb
import matplotlib.pyplot as plt
import swifter
import dateutil
import datetime
import pandas as pd
import numpy as np

from cachetools import cached, TTLCache
import time
import dataset
#time.sleep(15)

try:
    mydb = mariadb.connect(host="bd", database = 'dados_tribunais',user="root", passwd="abc@123")
    query = "select data_ajuizamento, orgao_julgador, data_sentenca from processos where tribunal='TJRN' and grau='JE';"
    df_tribunal = pd.read_sql(query,mydb)
    mydb.close() #close the connection
except Exception as e:
    mydb.close()
    print(str(e))

cursor = conectar_banco()
criar_dataset(cursor, 'tjce', data, 10000)    

unidades_jurisdicionais = df_tribunal['orgao_julgador'].unique()
data_ddf = dd.from_pandas(df_tribunal, npartitions=6)

data = df_tribunal
dataframe = data_ddf.groupby(['data_ajuizamento', 'orgao_julgador']).size()
data_ddf = dataframe.to_frame(name='quantidade')
data_ddf = data_ddf.rename_axis(['data_ajuizamento', 'orgao_julgador']).reset_index().compute()
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
                html.Label("Selecione a Unidade Jurisdicional:", style={
                    'fontFamily': 'Arial, sans-serif',
                    'color': '#333'
                }),
                dcc.Dropdown(
                    id='jurisdiction-dropdown',
                    options=[{'label': j, 'value': j} for j in unidades_jurisdicionais],
                    value=unidades_jurisdicionais[0],  # Valor padrão
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
                    start_date=data_ddf['data_ajuizamento'].min(),
                    end_date=data_ddf['data_ajuizamento'].max(),
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
    Output('output-metodo', 'children'),
    [Input('input-tribunal', 'value')]
)
def chamar_metodo(nome_tribunal):
    if nome_tribunal:
        resultado = meu_metodo(nome_tribunal)
        return resultado
    else:
        return "Digite um nome de tribunal válido."

# Definindo cache com Time-To-Live (TTL) de 300 segundos (5 minutos) e capacidade máxima de 100 itens
cache = TTLCache(maxsize=100, ttl=300)

@cached(cache)
def get_filtered_data(jurisdiction, start_date, end_date):
    filtered_data_ddf = data_ddf[(data_ddf['orgao_julgador'] == jurisdiction) &
                                 (data_ddf['data_ajuizamento'] >= start_date) & 
                                 (data_ddf['data_ajuizamento'] <= end_date)]
    filtered_data = filtered_data_ddf
    return filtered_data.sort_values(by='data_ajuizamento')

@app.callback(
    Output('time-series-chart', 'figure'),
    [Input('jurisdiction-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_graph(selected_jurisdiction, start_date, end_date):
    filtered_data = get_filtered_data(selected_jurisdiction, start_date, end_date)

    fig = go.Figure(go.Scatter(
        x=filtered_data['data_ajuizamento'],
        y=filtered_data['quantidade'],
        mode='lines+markers',
        name='Ajuizamentos',
        line=dict(color='#1f77b4'),  # Cor da linha
        marker=dict(color='#1f77b4')  # Cor dos marcadores
        ))

    fig.update_layout(
        title={
            'text': f'Série Temporal de Ajuizamentos - {selected_jurisdiction}',
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
    