import pandas as pd
import requests
import json
import datetime
import dateutil
import concurrent.futures
import swifter
import os

pd.set_option('display.max_columns', None)  # or 1000
pd.set_option('display.max_rows', None)  # or 1000
pd.set_option('display.max_colwidth', None)  # or 199

def converte_data(data_str):
    return pd.to_datetime(data_str)


def lista_para_dataframe(dados_dict):
  processos = []
  for processo in dados_dict['hits']['hits']:
    tribunal = processo['_source']['tribunal']
    grau = processo['_source']['grau']
    classe = processo['_source']['classe']['codigo']
    data_ajuizamento = processo['_source']['dataAjuizamento']
    codigo = processo['_source']['orgaoJulgador']['codigo']

    processos.append([tribunal, classe, data_ajuizamento, codigo, grau])

  df = pd.DataFrame(processos, columns=['tribunal','classe_codigo', 'data_ajuizamento', 'codigo_orgaoJulgador', 'grau'])
  #df['data_ajuizamento'] = df['data_ajuizamento'].swifter.apply(converte_data)
  df['data_ajuizamento'] = df['data_ajuizamento'].swifter.apply(dateutil.parser.parse)
  df['data_ajuizamento'] = df['data_ajuizamento'].swifter.apply(datetime.datetime.date)
   
  return df

df_tribunal = pd.DataFrame()
url = "https://api-publica.datajud.cnj.jus.br/api_publica_tjmg/_search"
api_key = "APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==" # Chave pública
tribunal = 'TJMG'
size = 10000
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
    df_tribunal = pd.concat([df_tribunal, lista_para_dataframe(dados_dict)])
    #print(df_tribunal.head(2))
    #print(df_tribunal.tail(1))
    tamanho_dataset = len(df_tribunal.index)
    ultima_data_ajuizamento = dados_dict['hits']['hits'][len(dados_dict['hits']['hits'])-1]['_source']['dataAjuizamento']
    print(f'{datetime.datetime.now()}\t Número de processos: {tamanho_dataset} \t Data do último processo adicionado: {ultima_data_ajuizamento}' )
    #if tamanho_dataset > 2000000:
    #  break

df_tribunal.to_csv('dados/processados/serie_temporal_ajuizamento-TJMG_2018.csv', header=True, sep=';', compression='zip')
df_g1 = df_tribunal[df_tribunal['grau'] == 'G1'] 
df_g1.to_csv('dados/processados/serie_temporal_ajuizamento-TJMG_G1_2018.csv', header=True, sep=';', compression='zip')
df_g2 = df_tribunal[df_tribunal['grau'] == 'G2'] 
df_g2.to_csv('dados/processados/serie_temporal_ajuizamento-TJMG_G2_2018.csv', header=True, sep=';', compression='zip')
df_je = df_tribunal[df_tribunal['grau'] == 'JE'] 
df_je.to_csv('dados/processados/serie_temporal_ajuizamento-TJMG_JE_2018.csv', header=True, sep=';', compression='zip')
print(df_tribunal.head(1))