import pandas as pd
import requests
import json
import datetime
import concurrent.futures
import swifter
import os

pd.set_option('display.max_columns', None)  # or 1000
pd.set_option('display.max_rows', None)  # or 1000
pd.set_option('display.max_colwidth', None)  # or 199

def converte_data(data_str):
    return pd.to_datetime(data_str).tz_convert('America/Sao_Paulo')


def gera_lista_assuntos(assuntos_do_df):
    lst_assuntos=[]
    for assunto in assuntos_do_df:
        try:
            lst_assuntos.append(assunto.get('nome'))
        except:
            lst_assuntos.append('')

    return lst_assuntos


def gera_lista_movimentos(movimentos):
    lst_movimentos_final =[]
    for movimento in movimentos:
        codigo = movimento.get('codigo')
        nome = movimento.get('nome')
        data_hora = movimento.get('dataHora')
        if data_hora:
            data_hora = converte_data(data_hora)
        lst_movimentos_final.append([ codigo, nome, data_hora])
    return lst_movimentos_final

def process_movimento(movimento):
    codigo = movimento.get('codigo')
    nome = movimento.get('nome')
    data_hora = movimento.get('dataHora')
    if data_hora:
        data_hora = converte_data(data_hora)
    return [codigo, nome, data_hora]

def gera_lista_movimentos_multithread(movimentos):
    lst_movimentos_final = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_movimento, movimentos))
        lst_movimentos_final.extend(results)
    return lst_movimentos_final


def lista_para_dataframe(dados_dict):
  processos = []
  for processo in dados_dict['hits']['hits']:
    numero_processo = processo['_source']['numeroProcesso']
    grau = processo['_source']['grau']
    classe = processo['_source']['classe']['nome']
    try:
      assuntos = processo['_source']['assuntos'] # Pode ter mais de um
    except:
      assuntos = []
    data_ajuizamento = processo['_source']['dataAjuizamento']
    ultima_atualizacao = processo['_source']['dataHoraUltimaAtualizacao']
    #formato = processo['_source']['formato']['nome']
    codigo = processo['_source']['orgaoJulgador']['codigo']
    orgao_julgador = processo['_source']['orgaoJulgador']['nome']
    municipio = processo['_source']['orgaoJulgador']['codigoMunicipioIBGE']
    sort = processo['sort'][0]
    try:
      movimentos = processo['_source']['movimentos']
    except:
      movimentos = []

    processos.append([numero_processo, classe, data_ajuizamento, ultima_atualizacao, \
                      codigo, orgao_julgador, municipio, grau, assuntos, movimentos, sort])

  df = pd.DataFrame(processos, columns=['numero_processo', 'classe', 'data_ajuizamento', 'ultima_atualizacao', \
                        'codigo', 'orgao_julgador', 'municipio', 'grau', 'assuntos', 'movimentos', 'sort'])
  df['movimentos'] = df['movimentos'].swifter.apply(gera_lista_movimentos_multithread)
  df['assuntos'] = df['assuntos'].swifter.apply(gera_lista_assuntos)
  #df['movimentos'] = df['movimentos'].swifter.apply(gera_lista_movimentos_multithread)
  df['data_ajuizamento'] = df['data_ajuizamento'].swifter.apply(converte_data)
  df['ultima_atualizacao'] = df['ultima_atualizacao'].swifter.apply(converte_data)
  try:
    df['movimentos']= df['movimentos'].swifter.apply(lambda x: sorted(x, key=lambda tup: tup[2], reverse=False))
  except:
    pass
  #print(df.head(1))  
  return df

df_tribunal = pd.DataFrame()
url = "https://api-publica.datajud.cnj.jus.br/api_publica_tjrn/_search"
api_key = "APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==" # Chave pública
tribunal = 'TJRN'
orgaoJulgador = '4º JUIZADO ESPECIAL DA FAZENDA PÚBLICA'
size = 2500
data = '2024-02-01'

payload = json.dumps(
{
"size": size,
"query": {
    "bool": {
    "must": [
        {"match": {"tribunal": tribunal}},
        {"match": {"orgaoJulgador.nome": orgaoJulgador}},
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
            {"match": {"orgaoJulgador.nome": orgaoJulgador}},
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
    df_tribunal = df_tribunal[df_tribunal['orgao_julgador'] == orgaoJulgador]
    print(df_tribunal.head(1))
    tamanho_dataset = len(df_tribunal.index)
    ultima_data_ajuizamento = dados_dict['hits']['hits'][len(dados_dict['hits']['hits'])-1]['_source']['dataAjuizamento']
    print(f'{datetime.datetime.now()}\t Serventia: {orgaoJulgador}\tNúmero de processos: {tamanho_dataset} \t Data do último processo adicionado: {ultima_data_ajuizamento}' )
    #if tamanho_dataset > 2000000:
    #  break

try:
    print(f'Número de processos incorporados: {tamanho_dataset} da Serventia: {orgaoJulgador}')
except:
    print(f'Última página do dicionário veio vazia: {orgaoJulgador}')
print(df_tribunal.head(1))