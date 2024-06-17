import requests
import json
import datetime
import dateutil
import concurrent.futures
import swifter
import os
import mariadb
import sys
import pandas as pd
import re

def conectar_banco():    
    try:
        conn = mariadb.connect(
            user="root",
            password="abc@123",
            host="bd",
            port=3306,
            database='dados_tribunais',
            autocommit=True
        )
        print("Connection established successfully!")
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        
    # Get Cursor
    cursor = conn.cursor()
    return cursor

def criar_bd():
    cursor = conectar_banco()
    cursor.execute("CREATE DATABASE IF NOT EXISTS dados_tribunais")
    #cursor.commit()
    cursor.close()
    
def criar_tabela():
    try:
        cursor = conectar_banco()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processos (
                numero_processo VARCHAR(255) PRIMARY KEY,
                tribunal VARCHAR(255),
                classe VARCHAR(255),
                data_ajuizamento DATE,
                ultima_atualizacao DATE,
                codigo VARCHAR(50),
                orgao_julgador VARCHAR(255),
                municipio VARCHAR(255),
                grau VARCHAR(50),
                assuntos TEXT,
                movimentos TEXT,
                data_sentenca VARCHAR(255),
                tempo_ate_sentenca VARCHAR(255),
                tempo_entre_1e2_mov VARCHAR(255),
                tempo_entre_2e3_mov VARCHAR(255),
                tempo_entre_3e4_mov VARCHAR(255),
                mais60d VARCHAR(255)
                
            )
        ''')

        print("Tabela criada com sucesso!")

    except: 
        print(f"Erro na criação da tabela")
    cursor.close()

            
def adicionar_processo_mariadb(cursor, numero_processo, tribunal, classe, data_ajuizamento, ultima_atualizacao, codigo, orgao_julgador, municipio, grau, assuntos, movimentos, data_sentenca,tempo_entre_1e2_mov, tempo_entre_2e3_mov, tempo_entre_3e4_mov, mais60d):
    try:
        cursor.execute('''
            INSERT INTO processos (numero_processo, tribunal, classe, data_ajuizamento, ultima_atualizacao, codigo, orgao_julgador, municipio, grau, assuntos, movimentos, data_sentenca,tempo_entre_1e2_mov, tempo_entre_2e3_mov, tempo_entre_3e4_mov, mais60d)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (numero_processo, tribunal, classe, data_ajuizamento, ultima_atualizacao, codigo, orgao_julgador, municipio, grau, assuntos, movimentos, data_sentenca,tempo_entre_1e2_mov, tempo_entre_2e3_mov, tempo_entre_3e4_mov, mais60d))
        
        
    except mariadb.Error as e:
        print(f"Erro na adição do processo: {tribunal}:  {e}")


def converte_data(data_str):
    data = dateutil.parser.parse(data_str)
    data = datetime.datetime.date(data)
    return data.strftime('%Y-%m-%d')


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

def obter_data(item):
  return datetime.strptime(item[2], '%Y-%m-%d')

def carregar_movimentacoes(tribunal):
    
    if tribunal[:2] == 'TJ':
        movimentacoes_gabinete = pd.read_csv('dados/movimentos_gabinete.csv', sep=';', header='infer')
        movimentacoes_gabinete['codigo'] = movimentacoes_gabinete['vazio.1']
        lista_movimentacoes_gabinete = movimentacoes_gabinete['codigo'].to_list()
        movimentacoes_secretaria = pd.read_csv('dados/movimentos_secretaria.csv', sep=';', header='infer')
        lista_movimentacoes_secretaria = movimentacoes_secretaria['codigo'].to_list()
    else:
        movimentacoes_gabinete = pd.read_csv('dados/jf_movimentos_gabinete.csv', sep=';', header='infer')
        lista_movimentacoes_gabinete = movimentacoes_gabinete['codigo'].to_list()
        movimentacoes_secretaria = pd.read_csv('dados/jf_movimentos_secretaria.csv', sep=';', header='infer')
        lista_movimentacoes_secretaria = movimentacoes_secretaria['codigo'].to_list()

    lista_movimentacoes_gabinete_set = set(lista_movimentacoes_gabinete)
    return lista_movimentacoes_gabinete_set
  
def calcular_data_sentenca(tribunal, movimentacao):
    lista_movimentacoes_gabinete_set = carregar_movimentacoes(tribunal)
    padrao_movimentacao = r'\[(\d+),\s+\'(.*?)\',\s+\'(\d{4}-\d{2}-\d{2})\'\]'
    resultado = re.findall(padrao_movimentacao, movimentacao)
    if resultado:
        for codigo, texto, data in resultado:
            if int(codigo) in lista_movimentacoes_gabinete_set:
                #print(codigo, '\: ', data)
                return data
        
    return -1

def calcular_tempo_entre_movimentacoes(movimentacoes, inicial, final):
    if final < inicial:
        return -1
    
    padrao_movimentacao = r'\[(\d+),\s+\'(.*?)\',\s+\'(\d{4}-\d{2}-\d{2})\'\]'
    resultado = re.findall(padrao_movimentacao, movimentacoes)
    try:
        if len(resultado) >= 2 and len(resultado) > final:
            #print()
            data_1 = datetime.datetime.strptime(resultado.pop(inicial)[2], '%Y-%m-%d')
            data_2 = datetime.datetime.strptime(resultado.pop(inicial)[2], '%Y-%m-%d')
            diferenca = data_2 - data_1
            return abs(diferenca.days)
        else:
            return -1
    except:
        print(f'erro: {len(resultado)}, {inicial}:{final},  {resultado}')
    return -1
  
def lista_para_dataframe(conector, dados_dict):
  processos = []
  for processo in dados_dict['hits']['hits']:
    numero_processo = processo['_source']['numeroProcesso']
    grau = processo['_source']['grau']
    tribunal = processo['_source']['tribunal']
    classe = processo['_source']['classe']['nome']
    try:
      assuntos = processo['_source']['assuntos'] # Pode ter mais de um
      asuntos = gera_lista_assuntos(assuntos)
    except:
      assuntos = []
    data_ajuizamento = converte_data(processo['_source']['dataAjuizamento'])
    ultima_atualizacao = converte_data(processo['_source']['dataHoraUltimaAtualizacao'])
    #formato = processo['_source']['formato']['nome']
    codigo = processo['_source']['orgaoJulgador']['codigo']
    orgao_julgador = processo['_source']['orgaoJulgador']['nome']
    municipio = processo['_source']['orgaoJulgador']['codigoMunicipioIBGE']
    try:
      movimentos = processo['_source']['movimentos']
      movimentos = gera_lista_movimentos_multithread(movimentos)
      movimentos = sorted(movimentos, key=lambda x: x[2])
      #print(movimentos) 
      
    except:
      movimentos = []
      print(f'Erro ao processar os movimentos do processo {numero_processo}')
    assuntos_str = '; '.join(str(assunto).split(',')[0].split(':')[1].strip() for assunto in assuntos) ## Pegando primeiro assunto
    movimentos_str = '; '.join(str(movimento) for movimento in movimentos)
    tempo_entre_1e2_mov = calcular_tempo_entre_movimentacoes(movimentos_str,0,1)
    tempo_entre_2e3_mov = calcular_tempo_entre_movimentacoes(movimentos_str,1,2)
    tempo_entre_3e4_mov = calcular_tempo_entre_movimentacoes(movimentos_str,2,3)
    mais60d = (tempo_entre_1e2_mov > 60) | (tempo_entre_2e3_mov > 60) | (tempo_entre_3e4_mov > 60)
    data_sentenca = calcular_data_sentenca(tribunal, movimentos_str)
    
      
    adicionar_processo_mariadb( conector, numero_processo, tribunal, classe,
                               data_ajuizamento, ultima_atualizacao, codigo,
                               orgao_julgador, municipio, grau, assuntos_str,
                               movimentos_str, data_sentenca,tempo_entre_1e2_mov, 
                               tempo_entre_2e3_mov, tempo_entre_3e4_mov, mais60d  )  
    

def criar_dataset(conector, tribunal, data, tamanho_consulta):
  
  url = f"https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal}/_search"
  api_key = "APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==" # Chave pública
  tribunal = tribunal.upper()
  size = tamanho_consulta
  data = data

  payload = json.dumps(
  {
  "size": tamanho_consulta,
  "query": {
      "bool": {
        "must": [
            {"match": {"tribunal": tribunal}},
            {"match": {"grau": 'JE'}},
            {"range": {"dataAjuizamento": {"gte": data }}},
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
  if len(dados_dict['hits']['hits']) < 5:
    print(f'Parece que você digitou um código de Serventia errado. Confira novamente.')
  lista_para_dataframe(conector, dados_dict)
  numero_processos = size

  while numero_processos == size:
    numero_processos = len(dados_dict['hits']['hits'])
    tamanho_dicionario_retornado = len(dados_dict['hits']['hits'])-1
    if tamanho_dicionario_retornado < 1:
      #print(f'Tamanho do dicionário da página anterior: {tamanho_dicionario_retornado}')
      continue
    ultima_posicao_dicionario = dados_dict['hits']['hits'][(len(dados_dict['hits']['hits'])-1)]['sort'][0]
    payload = json.dumps(
    {
    "size": tamanho_consulta,
    "query": {
        "bool": {
          "must": [
            {"match": {"tribunal": tribunal}},
            {"match": {"grau": 'JE'}},            
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
    lista_para_dataframe(conector, dados_dict)
  
  

                   