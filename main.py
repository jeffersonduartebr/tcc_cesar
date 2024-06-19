import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

from sqlalchemy import create_engine, URL
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
import urllib.parse
#time.sleep(15)

import warnings
import pymysql
import pandas as pd
#warnings.filterwarnings("ignore")



pool = mariadb.ConnectionPool(
    pool_name="pool_dash",
    pool_size=10,
    host='bd',
    user='root',
    password='abc.123',
    database='dados_tribunais'
)

try:
    conn = pool.get_connection()
    cursor = conn.cursor()
    estrutura = list()
    cursor.execute(f"SELECT DISTINCT orgao_julgador FROM tjrn ;")
    unidades = cursor.fetchall()
    for unidade in unidades:
        estrutura.append(unidade)
    cursor.close()
    conn.close()

except mariadb.Error as e:
    print(f"Erro ao conectar ou executar a consulta: {e}")


#print(data_ddf)

app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(label='Visualização', children=[
            html.H1("Visualização de Séries Temporais de Ajuizamentos do TJRN", style={
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
                id='unidade-judiciaria-dropdown',
                options=[{'label': unidade[0], 'value': unidade[0]} for unidade in estrutura],
                value=estrutura[1][0],
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
        ])
    ])
])

@app.callback(
    Output('time-series-chart', 'figure'),
    [Input('unidade-judiciaria-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_graph(unidade_judiciaria, start_date, end_date):
    try:

        username = "root"
        password = "abc.123"
        host = "bd"
        database = "dados_tribunais"

        connection = pymysql.connect(
            host=host,
            user=username,
            password=password,
            database=database
        )

        query = f"SELECT * FROM tjrn WHERE orgao_julgador = '{unidade_judiciaria}';"
        df_tribunal = pd.read_sql(query, con=connection, index_col='numero_processo')

        connection.close()
        
        #df_tribunal['data_ajuizamento'] = df_tribunal['data_ajuizamento'].swifter.apply(dateutil.parser.parse)
        #df_tribunal['data_ajuizamento'] = df_tribunal['data_ajuizamento'].swifter.apply(datetime.datetime.date)
    except mariadb.Error as e:
        print(f"Erro ao conectar ou executar a consulta: {e}")
        cursor.close()
        conn.close()
        return None
    start_date = dateutil.parser.parse(start_date)
    start_date = datetime.datetime.date(start_date)
    end_date = dateutil.parser.parse(end_date)
    end_date = datetime.datetime.date(end_date)
    
    filtered_data_ddf = df_tribunal[(df_tribunal['data_ajuizamento'] >= start_date) & (df_tribunal['data_ajuizamento'] <= end_date)]
    print(filtered_data_ddf.head(5))


    dataframe = filtered_data_ddf.groupby(['data_ajuizamento', 'orgao_julgador']).size()
    data_ddf = dataframe.to_frame(name='quantidade')
    data_ddf = data_ddf.rename_axis(['data_ajuizamento', 'orgao_julgador']).reset_index().sort_values('data_ajuizamento')      
    filtered_data = filtered_data_ddf.set_index('data_ajuizamento').sort_index()
    
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
    