import pandas as pd

df_2020 = pd.read_csv('dados/TRF4_JE_2020-12-31.csv', header='infer', sep=';', compression='zip')
df_2021 = pd.read_csv('dados/TRF4_JE_2021-01-01.csv', header='infer', sep=';', compression='zip')

df_total = pd.concat([df_2020, df_2021])

<<<<<<< HEAD
<<<<<<< HEAD
df_total.to_parquet('dados/TRF4_JE_2018-01-01.parquet', index=False)
df_total.to_csv('dados/TRF4_JE_2018-01-01.csv', header=True, sep=';', index=False)
=======
df_total.to_csv('dados/TRF4_JE_2018-01-01.csv', header=True, index=False, sep=';', compression='zip')

>>>>>>> 2f5dd87038b8131d1e7c3f40bb84d07080eca5e3
=======
df_total.to_csv('dados/TRF4_JE_2018-01-01.csv', header=True, index=False, sep=';', compression='zip')

>>>>>>> 2f5dd87038b8131d1e7c3f40bb84d07080eca5e3
print('Tarefa concluída')