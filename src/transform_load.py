#IMPORTAR AS DEPENDÊNCIAS
import os 
import json 
from pathlib import Path 
from datetime import datetime
import psycopg 
from dotenv import load_dotenv

#CARREGAR AS VARIÁVEIS DE AMBIENTE
load_dotenv()

#STRING DE CONEXÃO COM O BANCO DE DADOS
DB_USER=os.getenv("DB_USER")
DB_PASSWORD=os.getenv("DB_PASSWORD")
DB_HOST= os.getenv("DB_HOST")
DB_PORT=os.getenv("DB_PORT")
DB_NAME=os.getenv("DB_NAME")
connection_string = postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}

#DEFINIR O CAMINHO PARA O DIRETÓRIO RAW
RAW_DIR = Path("data/raw")

#CRIAR AS FUNÇÕES PARA CARREGAR OS DADOS NO BANCO DE DADOS


def criar_tabelas(conn):
    """
    CRIAR AS TABELAS NO BANCO DE DADOS SE ELA NÃO EXISTIR
    """
    with conn.cursor() as cur:
    #elt_execucao
    #staging_raw
    #tabelas finais analíticas [municipio, exercicio_receita]

def normalizar_conta(nome_conta):
    """
    PADRONIZA O NOME DO IMPOSTO. O SICONFI MUDA A NOMENCLATURA ENTRE OS ANOS.
    """
def run_elt_transform_load():
    with psycopg.connect(connection_string) as conn:
        criar_tabelas(conn)
        #ETL
        #EXTRAÇÃO
        #TRANSFORMAÇÃO
        #LOAD