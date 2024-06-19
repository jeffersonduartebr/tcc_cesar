import mariadb
import pandas as pd
import numpy as np

from neuralprophet import NeuralProphet

class NeuralProphetModel:
    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.model = NeuralProphet(n_lags=15, n_forecasts=60, ar_layers=(16, 64))

    def connect_to_database(self):
        try:
            self.conn = mariadb.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            self.cursor = self.conn.cursor()
            print("Connected to MariaDB!")
            return self.cursor
            
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB: {e}")

    def train_model(self, data):
        self.model = self.model.add_country_holidays("BR")
        self.model.set_plotting_backend("plotly-static")
        df_train, df_val = self.model.split_df(data, valid_p=0.25)
        metrics = self.model.fit(df_train, validation_df=df_val, freq='D', progress="None")
        return self.model

    def predict(self, dados, future=365):
        df_future = self.model.make_future_dataframe(dados, n_historic_predictions=True, periods=future)
        previsoes = self.model.predict(df_future)
        return previsoes

    def close_connection(self):
        self.cursor.close()
        self.conn.close()
        print("Connection to MariaDB closed!")
        
    def salvar_predicoes(self, previsoes, unidade_jurisdicional):
        conexao = self.connect_to_database(self)
        try:
            for index, row in previsoes.iterrows():
                self.cursor.execute(f"INSERT INTO previsoes (data_ajuizamento, quantidade, {unidade_jurisdicional}) VALUES (?, ?, ?)", (row['ds'], row['yhat1'], unidade_jurisdicional))
            self.conn.commit()
            print("Previsões salvas no banco de dados!")
        except mariadb.Error as e:
            print(f"Erro ao salvar previsões no banco de dados: {e}")

def carregar_serie_temporal_bd(orgao_julgador):
    try:
        dados = pd.DataFrame()
        mydb = mariadb.connect(host="bd", database = 'dados_tribunais',user="root", passwd="abc.123")
        query = f"select data_ajuizamento, count(*) as quantidade from tjrn where orgao_julgador='{orgao_julgador}' GROUP BY data_ajuizamento; ;"
        df_serie = pd.read_sql(query,mydb)
        df_serie.reset_index(inplace=True)
        dados['ds'] = df_serie['data_ajuizamento']
        dados['y'] = df_serie['quantidade']
        return dados
    except mariadb.Error as e:
        print(f"Erro de conexão ao MariaDB: {e}")
        return None


df_tribunal = carregar_serie_temporal_bd(orgao_julgador)
profeta = NeuralProphetModel("bd", 3306, "root", "abc.123", "dados_tribunais")
profeta.connect_to_database()

profeta.train_model(df_tribunal)
previsoes = profeta.predict(df_tribunal, 90)

print(previsoes)

profeta.close_connection()