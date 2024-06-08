import pandas as pd
import requests
import json
import datetime
import dateutil
import concurrent.futures
import swifter
import os

import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb import DataFrameClient



pd.set_option('display.max_columns', None)  # or 1000
pd.set_option('display.max_rows', None)  # or 1000
pd.set_option('display.max_colwidth', None)  # or 199

API_TOKEN_INFLUXDB = 'MEKovSzfY-UB99ZCVPun6A8GgntWK3sUWxKBEUHCvS8LeQYk8x_gd-OFlnlrLPWTv_sQAeHXn9um1xxKINLPyA=='

token = '4QrxUJ8rO4lqJaDJytPxCPANBXt0Z3JSKOC3di3w43r5b5u_YSfD1QqHUqHnId98IozDiypUUn4HsSNKmI0i8w=='
ORG = "TCC"
URL = "http://localhost:8086"
BUCKET = "series_temporais"


#processos.append([tribunal, classe, data_ajuizamento, codigo, grau])
    
def save_pandas_to_infludb(df, measurement):
    valores = df['numero_processo']
    valores.index = df [['data_ajuizamento']]
    tag = {'classe': df[['classe_codigo']], 'codigo': df[['codigo_orgaoJulgador']], 'grau': df[['grau']]}
    client_from_pandas = DataFrameClient(host='127.0.0.1', port=8086, username='jefferson.silva', password='fcs!(%(Jeff))', database='series_temporais_tcc')
    client_from_pandas.write_points(df, measurement, valores, tags = tag)
    


def converte_data(data_str):
    return pd.to_datetime(data_str).tz_convert('America/Sao_Paulo')


def lista_para_dataframe(dados_dict):
  processos = []
  for processo in dados_dict['hits']['hits']:
    tribunal = processo['_source']['tribunal']
    numero_processo = processo['_source']['numeroProcesso']
    grau = processo['_source']['grau']
    classe = processo['_source']['classe']['codigo']
    data_ajuizamento = processo['_source']['dataAjuizamento']
    codigo = processo['_source']['orgaoJulgador']['codigo']

    processos.append([tribunal, processo, classe, data_ajuizamento, codigo, grau])

  df = pd.DataFrame(processos, columns=['tribunal','numero_processo','classe_codigo', 'data_ajuizamento', 'codigo_orgaoJulgador', 'grau'])
  df['data_ajuizamento'] = df['data_ajuizamento'].swifter.apply(converte_data)
  #df['data_ajuizamento'] = df['data_ajuizamento'].swifter.apply(dateutil.parser.parse)
  #df['data_ajuizamento'] = df['data_ajuizamento'].swifter.apply(datetime.datetime.date)
   
  return df

df_tribunal = pd.DataFrame()
url = "https://api-publica.datajud.cnj.jus.br/api_publica_tjce/_search"
api_key = "APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==" # Chave pública
tribunal = 'TJCE'
size = 1000
data = '2018-01-01'


payload = json.dumps(
{
"size": size,
"query": {
    "bool": {
    "must": [
        {"match": {"tribunal": tribunal}},
        {"range": {"dataAjuizamento": {"gte": data }}}
    ]
    }
},
"sort": [{"@timestamp": {"order": "asc"}}]
})

headers = {
'Authorization': api_key,
'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)  # <Response [200]>
dados_dict = response.json() # <class 'dict'>
df_tribunal = lista_para_dataframe(dados_dict)
#df_tribunal.set_index("data_ajuizamento", inplace=True)
save_pandas_to_infludb(df_tribunal, tribunal)
numero_processos = size

while numero_processos == size:
    numero_processos = len(dados_dict['hits']['hits'])
    tamanho_dicionario_retornado = len(dados_dict['hits']['hits'])-1
    if tamanho_dicionario_retornado < 1:
        print(f'Tamanho do dicionário da página anterior: {tamanho_dicionario_retornado}')
        continue
    ultima_posicao_dicionario = dados_dict['hits']['hits'][(len(dados_dict['hits']['hits'])-1)]['sort'][0]
    #print(f'Partindo da posição: {ultima_posicao_dicionario}')
    payload = json.dumps(
    {
    "size": size,
    "query": {
        "bool": {
            "must": [
            {"match": {"tribunal": tribunal}},
            {"range": {"dataAjuizamento": {"gte": data}}}
            
            ]
        }
    },
        "search_after": [ ultima_posicao_dicionario ],
        "sort": [{"@timestamp": {"order": "asc"}}]
    })

    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)  # <Response [200]>
    dados_dict = response.json() # <class 'dict'>
    numero_processos = len(dados_dict['hits']['hits'])
    ultima_posicao_dicionario = dados_dict['hits']['hits'][(len(dados_dict['hits']['hits'])-1)]['sort']
    df_tribunal = lista_para_dataframe(dados_dict)
    df_tribunal.set_index("data_ajuizamento", inplace=True)
    save_pandas_to_infludb(df_tribunal, tribunal)

    
    #df_tribunal = pd.concat([df_tribunal, lista_para_dataframe(dados_dict)])

    tamanho_dataset = len(df_tribunal.index)
    ultima_data_ajuizamento = dados_dict['hits']['hits'][len(dados_dict['hits']['hits'])-1]['_source']['dataAjuizamento']
    print(f'{datetime.datetime.now()}\t Número de processos: {tamanho_dataset} \t Data do último processo adicionado: {ultima_data_ajuizamento}' )
    #if tamanho_dataset > 2000000:
    #  break

df_tribunal.to_csv('dados/processados/serie_temporal_ajuizamento-TJCE_2018.csv', header=True, sep=';', compression='zip')
df_g1 = df_tribunal[df_tribunal['grau'] == 'G1'] 
df_g1.to_csv('dados/processados/serie_temporal_ajuizamento-TJCE_G1_2018.csv', header=True, sep=';', compression='zip')
df_g2 = df_tribunal[df_tribunal['grau'] == 'G2'] 
df_g2.to_csv('dados/processados/serie_temporal_ajuizamento-TJCE_G2_2018.csv', header=True, sep=';', compression='zip')
df_je = df_tribunal[df_tribunal['grau'] == 'JE'] 
df_je.to_csv('dados/processados/serie_temporal_ajuizamento-TJCE_JE_2018.csv', header=True, sep=';', compression='zip')
write_api.__del__()
client.__del__()
print(df_tribunal.head(1))