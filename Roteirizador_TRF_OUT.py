import streamlit as st
import mysql.connector
import decimal
import pandas as pd
from datetime import timedelta, time, datetime
from itertools import combinations
from collections import Counter
import gspread 
import requests
from google.cloud import secretmanager 
import json
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account

def gerar_df_phoenix(vw_name, base_luck):
    
    data_hoje = datetime.now()

    data_hoje_str = data_hoje.strftime("%Y-%m-%d")

    # Parametros de Login AWS
    config = {
    'user': 'user_automation_jpa',
    'password': 'luck_jpa_2024',
    'host': 'comeia.cixat7j68g0n.us-east-1.rds.amazonaws.com',
    'database': base_luck
    }
    # Conexão as Views
    conexao = mysql.connector.connect(**config)
    cursor = conexao.cursor()

    if base_luck=='test_phoenix_maceio':

        if vw_name=='vw_router':

            request_name = f'SELECT * FROM {vw_name} WHERE {vw_name}.`Data Execucao`>={data_hoje_str}'

        elif vw_name=='vw_payment_guide':

            request_name = f"SELECT 'Tipo de Servico', 'Reserva', 'Escala' FROM {vw_name}"

    else:

        request_name = f'SELECT * FROM {vw_name} WHERE {vw_name}.`Data Execucao`>={data_hoje_str}'

    # Script MySql para requests
    cursor.execute(
        request_name
    )
    # Coloca o request em uma variavel
    resultado = cursor.fetchall()
    # Busca apenas o cabecalhos do Banco
    cabecalho = [desc[0] for desc in cursor.description]

    # Fecha a conexão
    cursor.close()
    conexao.close()

    # Coloca em um dataframe e muda o tipo de decimal para float
    df = pd.DataFrame(resultado, columns=cabecalho)
    df = df.applymap(lambda x: float(x) if isinstance(x, decimal.Decimal) else x)
    return df

def puxar_sequencias_hoteis(id_gsheet, lista_abas, lista_nomes_df_hoteis):

    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(id_gsheet)

    for index in range(len(lista_abas)):

        aba = lista_abas[index]

        df_hotel = lista_nomes_df_hoteis[index]
        
        sheet = spreadsheet.worksheet(aba)

        sheet_data = sheet.get_all_values()

        st.session_state[df_hotel] = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

        st.session_state[df_hotel]['Hoteis Juntos p/ Apoios'] = \
        st.session_state[df_hotel]['Hoteis Juntos p/ Apoios'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Hoteis Juntos p/ Apoios'] = \
        pd.to_numeric(st.session_state[df_hotel]['Hoteis Juntos p/ Apoios'], errors='coerce')

        st.session_state[df_hotel]['Hoteis Juntos p/ Carro Principal'] = \
        st.session_state[df_hotel]['Hoteis Juntos p/ Carro Principal'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Hoteis Juntos p/ Carro Principal'] = \
        pd.to_numeric(st.session_state[df_hotel]['Hoteis Juntos p/ Carro Principal'], errors='coerce')

        st.session_state[df_hotel]['Bus'] = \
        st.session_state[df_hotel]['Bus'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Micro'] = \
        st.session_state[df_hotel]['Micro'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Van'] = \
        st.session_state[df_hotel]['Van'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Utilitario'] = \
        st.session_state[df_hotel]['Utilitario'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Sequência'] = pd.to_numeric(st.session_state[df_hotel]['Sequência'], errors='coerce')

def transformar_timedelta(intervalo):
    
    intervalo = timedelta(hours=intervalo.hour, minutes=intervalo.minute, seconds=intervalo.second)

    return intervalo

def objeto_intervalo(titulo, valor_padrao, chave):

    intervalo_ref = st.time_input(label=titulo, value=valor_padrao, key=chave, step=300)
    
    intervalo_ref = transformar_timedelta(intervalo_ref)

    return intervalo_ref

def gerar_itens_faltantes(df_servicos, df_hoteis):

    lista_hoteis_df_router = df_servicos['Est Origem'].unique().tolist()

    lista_hoteis_sequencia = df_hoteis['Est Origem'].unique().tolist()

    itens_faltantes = set(lista_hoteis_df_router) - set(lista_hoteis_sequencia)

    itens_faltantes = list(itens_faltantes)

    return itens_faltantes, lista_hoteis_df_router

def inserir_hoteis_faltantes(itens_faltantes, df_hoteis, aba_excel, regiao):

    df_itens_faltantes = pd.DataFrame(itens_faltantes, columns=['Est Origem'])

    st.dataframe(df_itens_faltantes, hide_index=True)

    df_itens_faltantes[['Região', 'Sequência', 'Bus', 'Micro', 'Van', 'Hoteis Juntos p/ Apoios', 'Hoteis Juntos p/ Carro Principal']]=''

    # df_hoteis_geral = pd.concat([df_hoteis, df_itens_faltantes], ignore_index=True)

    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)
    
    spreadsheet = client.open_by_key('1ch1NfOKeK008ZeqexQTzOqXuCZ2Q6sL8hY2sPqQegLQ')

    sheet = spreadsheet.worksheet(aba_excel)
    sheet_data = sheet.get_all_values()
    last_filled_row = len(sheet_data)
    # limpar_colunas = "A:H"
    # sheet.batch_clear([limpar_colunas])
    # data = [df_hoteis_geral.columns.values.tolist()] + df_hoteis_geral.values.tolist()
    data = df_itens_faltantes.values.tolist()
    # sheet.update("A1", data)
    start_row = last_filled_row + 1
    start_cell = f"A{start_row}"
    
    sheet.update(start_cell, data)

    st.error('Os hoteis acima não estão cadastrados na lista de sequência de hoteis.' + 
             f' Eles foram inseridos no final da lista de {regiao}. Por favor, coloque-os na sequência e tente novamente')

def ordenar_juncoes(df_router_ref):

    max_juncao = df_router_ref['Junção'].dropna().max()

    if pd.isna(max_juncao):

        max_juncao = 0

    for juncao in range(1, int(max_juncao) + 1):

        df_ref = df_router_ref[(df_router_ref['Modo do Servico']=='REGULAR') & (df_router_ref['Junção']==juncao)]\
            .sort_values(by='Sequência', ascending=False).reset_index()

        if len(df_ref)>0:

            index_inicial = df_ref['index'].min()
    
            index_final = df_ref['index'].max()
    
            df_ref = df_ref.drop('index', axis=1)
    
            df_router_ref.iloc[index_inicial:index_final+1] = df_ref

    return df_router_ref

def colocar_menor_horario_juncao(df_router_ref, df_juncao_voos):

    df_menor_horario = pd.DataFrame(columns=['Junção', 'Menor Horário'])

    contador=0

    for juncao in df_juncao_voos['Junção'].unique().tolist():

        menor_horario = df_juncao_voos[df_juncao_voos['Junção']==juncao]['Horário'].min()

        df_menor_horario.at[contador, 'Junção']=juncao

        df_menor_horario.at[contador, 'Menor Horário']=menor_horario

        contador+=1

    df_router_ref = pd.merge(df_router_ref, df_menor_horario, on='Junção', how='left')

    return df_router_ref

def criar_df_servicos_2(df_servicos, df_juncao_voos, df_hoteis):

    # Criando coluna de paxs totais

    df_servicos['Total ADT | CHD'] = df_servicos['Total ADT'] + df_servicos['Total CHD']    

    # Preenchendo coluna 'Data Horario Apresentacao'

    df_servicos['Data Horario Apresentacao'] = pd.to_datetime(df_servicos['Data Voo'].astype(str) + ' ' + df_servicos['Horario Voo'].astype(str))
    
    # Criando coluna de Junção através de pd.merge

    df_servicos_2 = pd.merge(df_servicos, df_juncao_voos[['Servico', 'Voo', 'Junção']], on=['Servico', 'Voo'], how='left')

    # Criando colunas Micro Região e Sequência através de pd.merge

    df_servicos_2 = pd.merge(df_servicos_2, df_hoteis, on='Est Origem', how='left')

    # Ordenando dataframe por ['Modo do Servico', 'Servico', 'Junção', 'Voo', 'Sequência']

    df_servicos_2 = df_servicos_2.sort_values(by=['Modo do Servico', 'Junção', 'Voo', 'Sequência'], 
                                              ascending=[True, True, True, False]).reset_index(drop=True)

    # Ordenando cada junção pela sequência de hoteis

    df_servicos_2 = ordenar_juncoes(df_servicos_2)

    # Colocando qual o menor horário de cada junção

    df_servicos_2 = colocar_menor_horario_juncao(df_servicos_2, df_juncao_voos)

    # Identificar tipo de translado das junções

    df_voos_internacionais = pd.merge(df_juncao_voos[['Voo', 'Junção']], df_servicos_2[['Voo', 'Tipo do Translado']].drop_duplicates(), on='Voo', how='left')

    df_voos_internacionais = df_voos_internacionais[df_voos_internacionais['Tipo do Translado']=='Internacional'][['Junção', 'Tipo do Translado']]\
        .drop_duplicates().reset_index(drop=True)
    
    df_voos_internacionais = df_voos_internacionais.rename(columns={'Tipo do Translado': 'Tipo do Translado Junção'})

    df_servicos_2 = pd.merge(df_servicos_2, df_voos_internacionais, on='Junção', how='left')

    # Criando colunas Roteiro e Carros

    df_servicos_2['Roteiro']=0

    df_servicos_2['Carros']=0

    return df_servicos_2

def definir_horario_primeiro_hotel(df, index):

    servico = df.at[index, 'Servico']

    data_voo = df.at[index, 'Data Voo']

    regiao = df.at[index, 'Região']

    if 'Junção' in df.columns.tolist():

        juncao = df.at[index, 'Junção']

    else:

        juncao = None

    modo = df.at[index, 'Modo do Servico']

    if pd.isna(juncao) or modo!='REGULAR':

        hora_voo = df.at[index, 'Horario Voo']

        tipo_voo = df.at[index, 'Tipo do Translado']

    else:

        hora_voo = df.at[index, 'Menor Horário']

        tipo_voo = 'Nacional'

    data_hora_voo_str = f'{data_voo} {hora_voo}'

    data_hora_voo = pd.to_datetime(data_hora_voo_str, format='%Y-%m-%d %H:%M:%S')

    horario_ultimo_hotel = df.at[index, 'Antecipação Último Hotel']

    if pd.isna(horario_ultimo_hotel):

        if (servico=='OUT - Natal' or servico=='Out - Genipabu') and (regiao!='CAMURUPIM'):

            if tipo_voo=='Internacional':

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_natal) - transformar_timedelta(time(1, 0))

            else:

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_natal)
        
        elif servico=='OUT - Pipa' or servico=='OUT - Touros':

            if tipo_voo=='Internacional':

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_pipa) - transformar_timedelta(time(1, 0))

            else:

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_pipa)
        
        elif servico=='OUT - São Miguel Gostoso' or servico=='OUT - Baia Formosa':

            if tipo_voo=='Internacional':

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_sao_miguel) - transformar_timedelta(time(1, 0))

            else:

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_sao_miguel)
        
        elif servico=='Out - Galinhos':

            if tipo_voo=='Internacional':

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_galinhos) - transformar_timedelta(time(1, 0))

            else:

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_galinhos)
        
        elif servico=='OUT - Camurupim' or servico=='OUT - Pirangi' or regiao=='CAMURUPIM':

            if tipo_voo=='Internacional':

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_camurupim) - transformar_timedelta(time(1, 0))

            else:

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_camurupim)
            
    else:

        horario_ultimo_hotel = transformar_timedelta(horario_ultimo_hotel)

        return data_hora_voo - horario_ultimo_hotel

def roteirizar_hoteis_mais_pax_max(df_servicos, roteiro, df_hoteis_pax_max):

    # Roteirizando reservas com mais paxs que a capacidade máxima da frota

    df_ref_reservas_pax_max = df_servicos.groupby(['Modo do Servico', 'Reserva', 'Servico', 'Est Origem']).agg({'Total ADT | CHD': 'sum'}).reset_index()

    df_ref_reservas_pax_max = df_ref_reservas_pax_max[df_ref_reservas_pax_max['Total ADT | CHD']>=st.session_state.pax_max].reset_index()

    if len(df_ref_reservas_pax_max)>0:

        carro=0

        for index in range(len(df_ref_reservas_pax_max)):

            roteiro+=1

            pax_ref = df_ref_reservas_pax_max.at[index, 'Total ADT | CHD']

            modo = df_ref_reservas_pax_max.at[index, 'Modo do Servico']

            servico = df_ref_reservas_pax_max.at[index, 'Servico']

            reserva_ref = df_ref_reservas_pax_max.at[index, 'Reserva']

            hotel = df_ref_reservas_pax_max.at[index, 'Est Origem']

            st.warning(f'O hotel {hotel} da reserva {reserva_ref} tem {pax_ref} paxs e, portanto vai ser roteirizado em um ônibus')

            carro+=1

            df_hotel_pax_max = df_servicos[(df_servicos['Reserva']==reserva_ref)].reset_index()

            df_servicos = df_servicos.drop(index=df_hotel_pax_max.at[index, 'index'])

            df_hoteis_pax_max = pd.concat([df_hoteis_pax_max, df_hotel_pax_max.loc[[index]]], ignore_index=True)

            df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Roteiro']=roteiro

            df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Carros']=carro

    # Roteirizando junções com mais paxs que a capacidade máxima da frota

    df_ref_com_juncao = df_servicos[(df_servicos['Bus']=='X') & ~(pd.isna(df_servicos['Junção']))]\
        .groupby(['Modo do Servico', 'Servico', 'Junção', 'Est Origem']).agg({'Total ADT | CHD': 'sum'}).reset_index()

    df_ref_com_juncao = df_ref_com_juncao[df_ref_com_juncao['Total ADT | CHD']>=st.session_state.pax_max].reset_index()

    if len(df_ref_com_juncao)>0:

        for index in range(len(df_ref_com_juncao)):

            carro=0

            roteiro+=1

            pax_ref = df_ref_com_juncao.at[index, 'Total ADT | CHD']

            loops = int(pax_ref//st.session_state.pax_max)

            modo = df_ref_com_juncao.at[index, 'Modo do Servico']

            servico = df_ref_com_juncao.at[index, 'Servico']

            ref_juncao = df_ref_com_juncao.at[index, 'Junção']

            hotel = df_ref_com_juncao.at[index, 'Est Origem']

            st.warning(f'O hotel {hotel} da junção {ref_juncao} tem {pax_ref} paxs e, portanto vai ser roteirizado em um ônibus')

            for loop in range(loops):

                carro+=1

                df_hotel_pax_max = df_servicos[(df_servicos['Modo do Servico']==modo) & (df_servicos['Servico']==servico) & 
                                                (df_servicos['Junção']==ref_juncao) & (df_servicos['Est Origem']==hotel)].reset_index()
                
                paxs_total_ref = 0
                
                for index_2, value in df_hotel_pax_max['Total ADT | CHD'].items():

                    if paxs_total_ref+value>st.session_state.pax_max:

                        break

                    else:

                        paxs_total_ref+=value

                        df_servicos = df_servicos.drop(index=df_hotel_pax_max.at[index_2, 'index'])

                        df_hoteis_pax_max = pd.concat([df_hoteis_pax_max, df_hotel_pax_max.loc[[index_2]]], ignore_index=True)

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Roteiro']=roteiro

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Carros']=carro

    # Roteirizando voos com mais paxs que a capacidade máxima da frota

    df_ref_sem_juncao = df_servicos[(df_servicos['Bus']=='X') & (pd.isna(df_servicos['Junção']))]\
        .groupby(['Modo do Servico', 'Servico', 'Voo', 'Est Origem']).agg({'Total ADT | CHD': 'sum'}).reset_index()

    df_ref_sem_juncao = df_ref_sem_juncao[df_ref_sem_juncao['Total ADT | CHD']>=st.session_state.pax_max].reset_index()

    if len(df_ref_sem_juncao)>0:

        for index in range(len(df_ref_sem_juncao)):

            carro=0

            roteiro+=1

            pax_ref = df_ref_sem_juncao.at[index, 'Total ADT | CHD']

            loops = int(pax_ref//st.session_state.pax_max)

            modo = df_ref_sem_juncao.at[index, 'Modo do Servico']

            servico = df_ref_sem_juncao.at[index, 'Servico']

            ref_voo = df_ref_sem_juncao.at[index, 'Voo']

            hotel = df_ref_sem_juncao.at[index, 'Est Origem']

            st.warning(f'O hotel {hotel} do voo {ref_voo} tem {pax_ref} paxs e, portanto vai ser roteirizado em um ônibus')

            for loop in range(loops):

                carro+=1

                df_hotel_pax_max = df_servicos[(df_servicos['Modo do Servico']==modo) & (df_servicos['Servico']==servico) & 
                                                (df_servicos['Voo']==ref_voo) & (df_servicos['Est Origem']==hotel)].reset_index()
                
                paxs_total_ref = 0
                
                for index_2, value in df_hotel_pax_max['Total ADT | CHD'].items():

                    if paxs_total_ref+value>st.session_state.pax_max:

                        break

                    else:

                        paxs_total_ref+=value

                        df_servicos = df_servicos.drop(index=df_hotel_pax_max.at[index_2, 'index'])

                        df_hoteis_pax_max = pd.concat([df_hoteis_pax_max, df_hotel_pax_max.loc[[index_2]]], ignore_index=True)

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Roteiro']=roteiro

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Carros']=carro

    # Transformando colunas 'Horario Voo' e 'Menor Horário' em datetime

    if len(df_hoteis_pax_max)>0:

        df_hoteis_pax_max['Horario Voo'] = pd.to_datetime(df_hoteis_pax_max['Horario Voo'], format='%H:%M:%S').dt.time
    
        df_hoteis_pax_max['Menor Horário'] = pd.to_datetime(df_hoteis_pax_max['Menor Horário'], format='%H:%M:%S').dt.time

    # Definindo horários de cada linha de df_hoteis_pax_max com a função definir_horario_primeiro_hotel

    for index in range(len(df_hoteis_pax_max)):

        df_hoteis_pax_max.at[index, 'Data Horario Apresentacao'] = definir_horario_primeiro_hotel(df_hoteis_pax_max, index)

    # Resetando os índices de df_servicos porque houve exclusão de linhas

    df_servicos = df_servicos.reset_index(drop=True)

    # Excluindo coluna 'index' do dataframe df_hoteis_pax_max

    if 'index' in df_hoteis_pax_max.columns.tolist():

        df_hoteis_pax_max = df_hoteis_pax_max.drop(columns=['index'])

    return df_servicos, df_hoteis_pax_max, roteiro

def definir_intervalo_ref(df, value):

    if ((df.at[value-1, 'Região']=='PONTA NEGRA 1') & (df.at[value, 'Região']=='PRAIA DOS ARTISTAS')) | \
        ((df.at[value-1, 'Região']=='PONTA NEGRA 2') & (df.at[value, 'Região']=='PRAIA DOS ARTISTAS')):

        return transformar_timedelta(st.session_state.intervalo_hoteis_bairros_iguais)*3
    
    elif (df.at[value-1, 'Região']=='TIBAU') & (df.at[value, 'Região']=='PIPA'):

        return transformar_timedelta(st.session_state.intervalo_hoteis_bairros_diferentes)*2
    
    elif df.at[value-1, 'Região']==df.at[value, 'Região']:

        return transformar_timedelta(st.session_state.intervalo_hoteis_bairros_iguais)
    
    elif df.at[value-1, 'Região']!=df.at[value, 'Região']:

        return transformar_timedelta(st.session_state.intervalo_hoteis_bairros_diferentes)

def roteirizar_privativos(roteiro, df_servicos, index):

    roteiro+=1

    df_servicos.at[index, 'Data Horario Apresentacao'] = \
        definir_horario_primeiro_hotel(df_servicos, index)
    
    df_servicos.at[index, 'Roteiro'] = roteiro
    
    df_servicos.at[index, 'Carros'] = 1

    return roteiro, df_servicos

def preencher_roteiro_carros(df_servicos, roteiro, carros, value):

    df_servicos.at[value, 'Roteiro'] = roteiro

    df_servicos.at[value, 'Carros'] = carros

    return df_servicos

def abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel):

    carros+=1

    df_servicos.at[value, 'Data Horario Apresentacao'] = \
        definir_horario_primeiro_hotel(df_servicos, index)

    data_horario_primeiro_hotel = df_servicos.at[value, 'Data Horario Apresentacao']

    paxs_total_roteiro = 0

    bairro = ''

    paxs_total_roteiro+=paxs_hotel

    df_servicos.at[value, 'Roteiro'] = roteiro

    df_servicos.at[value, 'Carros'] = carros

    return carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro

def contar_hoteis_df(df_ref):

    df_ref_contagem_hoteis = df_ref.groupby('Est Origem')['Hoteis Juntos p/ Carro Principal'].first().reset_index()

    hoteis_mesmo_voo=0

    for index in range(len(df_ref_contagem_hoteis)):

        if index==0:

            hoteis_mesmo_voo+=1

        elif not ((df_ref_contagem_hoteis.at[index, 'Hoteis Juntos p/ Carro Principal']==
                  df_ref_contagem_hoteis.at[index-1, 'Hoteis Juntos p/ Carro Principal']) and 
                  (~pd.isna(df_ref_contagem_hoteis.at[index, 'Hoteis Juntos p/ Carro Principal']))):

            hoteis_mesmo_voo+=1

    return hoteis_mesmo_voo

def gerar_horarios_apresentacao(df_servicos, roteiro, max_hoteis):

    for index in range(len(df_servicos)):

        # Se o serviço for privativo

        if df_servicos.at[index, 'Modo do Servico']=='PRIVATIVO POR VEICULO' or \
            df_servicos.at[index, 'Modo do Servico']=='PRIVATIVO POR PESSOA' or \
                df_servicos.at[index, 'Modo do Servico']=='CADEIRANTE':

            roteiro, df_servicos = roteirizar_privativos(roteiro, df_servicos, index)


        # Se o serviço não for privativo

        elif df_servicos.at[index, 'Modo do Servico']=='REGULAR':

            juntar = df_servicos.at[index, 'Junção']

            voo = df_servicos.at[index, 'Voo']

            # Se o voo não estiver em alguma junção

            if pd.isna(juntar):

                df_ref = df_servicos[(df_servicos['Modo do Servico']=='REGULAR') & (df_servicos['Voo']==voo)].reset_index()

                index_inicial = df_ref['index'].min()              
                
                hoteis_mesmo_voo = contar_hoteis_df(df_ref)

                if index==index_inicial:

                    if hoteis_mesmo_voo<=max_hoteis:

                        roteiro+=1

                        carros = 1

                        paxs_total_roteiro = 0

                        bairro = ''

                        # Loop no voo para colocar os horários

                        for index_2, value in df_ref['index'].items():

                            # Se for o primeiro hotel do voo, define o horário inicial, colhe o horário do hotel e inicia somatório de paxs do roteiro

                            if value==index_inicial:

                                df_servicos.at[value, 'Data Horario Apresentacao'] = \
                                    definir_horario_primeiro_hotel(df_servicos, value)
                                
                                data_horario_primeiro_hotel = df_servicos.at[value, 'Data Horario Apresentacao']
                                
                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]\
                                        ['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                paxs_total_roteiro+=paxs_hotel

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                            # Se não for a primeira linha do voo, mas o hotel for igual o hotel anterior, só repete o horário de apresentação

                            elif (df_servicos.at[value, 'Est Origem']==df_servicos.at[value-1, 'Est Origem']) | \
                                (df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']==df_servicos.at[value-1, 'Hoteis Juntos p/ Carro Principal']):

                                df_servicos.at[value, 'Data Horario Apresentacao']=\
                                    df_servicos.at[value-1, 'Data Horario Apresentacao']

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                            # Se não for a primeira linha do voo e o hotel não for igual ao anterior

                            else:

                                # Colhe a quantidade de paxs do hotel anterior, o bairro do hotel atual, a quantidade de paxs do hotel atual 
                                # e verifica se estoura a capacidade máxima de um carro

                                bairro=df_servicos.at[value, 'Região']

                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]\
                                        ['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                # Se estourar a capacidade do carro, aí trata como se fosse o primeiro hotel e adiciona 1 na variável carros
                                # pra, no final, eu saber quantos carros foram usados nesse roteiro e poder dividir 'igualmente' a quantidade de hoteis

                                if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                                    carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = \
                                        abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)

                                # Se não estourar a capacidade máxima

                                else:

                                    paxs_total_roteiro+=paxs_hotel

                                    # Sempre que inicia um carro, o bairro fica vazio. Portanto, se não for o primeiro hotel do carro, vai definir a variavel
                                    # intervalo_ref pra o robô saber quantos minutos deve adicionar até o próximo horário de apresentação

                                    if bairro!='':

                                        intervalo_ref = definir_intervalo_ref(df_servicos, value)
                                        
                                    if paxs_hotel>=st.session_state.pax_cinco_min:

                                        intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                                    data_horario_hotel = df_servicos.at[value-1, 'Data Horario Apresentacao']-\
                                        intervalo_ref

                                    if  data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):

                                        carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = \
                                            abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)

                                    else:

                                        df_servicos.at[value, 'Data Horario Apresentacao']=data_horario_hotel

                                        df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, 
                                                                                            value)

                    # Se no voo tiver mais que o número máximo de hoteis permitidos por carro

                    else:

                        roteiro+=1

                        carros = 1

                        paxs_total_roteiro = 0

                        contador_hoteis = 0

                        bairro = ''

                        # Loop no voo para colocar os horários

                        for index_2, value in df_ref['index'].items():

                            # Se for o primeiro hotel do voo, define o horário inicial, colhe o horário do hotel e inicia somatório de paxs do roteiro

                            if value==index_inicial:

                                df_servicos.at[value, 'Data Horario Apresentacao'] = \
                                    definir_horario_primeiro_hotel(df_servicos, value)
                                
                                data_horario_primeiro_hotel = df_servicos.at[value, 'Data Horario Apresentacao']
                                
                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]\
                                        ['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                paxs_total_roteiro+=paxs_hotel

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                                contador_hoteis+=1

                            # Se não for a primeira linha do voo, mas o hotel for igual o hotel anterior, só repete o horário de apresentação

                            elif (df_servicos.at[value, 'Est Origem']==df_servicos.at[value-1, 'Est Origem']) | \
                                (df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']==df_servicos.at[value-1, 'Hoteis Juntos p/ Carro Principal']):

                                df_servicos.at[value, 'Data Horario Apresentacao']=\
                                    df_servicos.at[value-1, 'Data Horario Apresentacao']

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                            # Se não for a primeira linha do voo e o hotel não for igual ao anterior

                            else:

                                # Colhe a quantidade de paxs do hotel anterior, o bairro do hotel atual, a quantidade de paxs do hotel atual 
                                # e verifica se estoura a capacidade máxima de um carro

                                contador_hoteis+=1

                                bairro=df_servicos.at[value, 'Região']

                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]\
                                        ['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                if contador_hoteis>max_hoteis:

                                    carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = \
                                        abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)
                                    
                                    contador_hoteis = 1
                                    
                                else:

                                    # Se estourar a capacidade do carro, aí trata como se fosse o primeiro hotel e adiciona 1 na variável carros
                                    # pra, no final, eu saber quantos carros foram usados nesse roteiro e poder dividir 'igualmente' a quantidade de hoteis

                                    if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                                        carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = \
                                            abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)
                                        
                                        contador_hoteis = 1

                                    # Se não estourar a capacidade máxima

                                    else:

                                        paxs_total_roteiro+=paxs_hotel

                                        # Sempre que inicia um carro, o bairro fica vazio. Portanto, se não for o primeiro hotel do carro, vai definir a variavel
                                        # intervalo_ref pra o robô saber quantos minutos deve adicionar até o próximo horário de apresentação

                                        if bairro!='':

                                            intervalo_ref = definir_intervalo_ref(df_servicos, value)
                                            
                                        if paxs_hotel>=st.session_state.pax_cinco_min:

                                            intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                                        data_horario_hotel = df_servicos.at[value-1, 'Data Horario Apresentacao']-\
                                            intervalo_ref

                                        if  data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):

                                            carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = \
                                            abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)
                                            
                                            contador_hoteis = 1

                                        else:

                                            df_servicos.at[value, 'Data Horario Apresentacao']=data_horario_hotel

                                            df_servicos = preencher_roteiro_carros(df_servicos, roteiro, 
                                                                                                carros, value)
    
            # Se o voo estiver em alguma junção

            else:

                df_ref = df_servicos[(df_servicos['Modo do Servico']=='REGULAR') & (df_servicos['Junção']==juntar)].reset_index()

                index_inicial = df_ref['index'].min()

                hoteis_mesma_juncao = contar_hoteis_df(df_ref)

                if index==index_inicial:

                    if hoteis_mesma_juncao<=max_hoteis:

                        roteiro+=1

                        carros = 1

                        paxs_total_roteiro = 0

                        bairro = ''

                        # Loop no voo para colocar os horários

                        for index_2, value in df_ref['index'].items():

                            # Se for o primeiro hotel do voo, define o horário inicial, colhe o horário do hotel e inicia somatório de paxs do roteiro

                            if value==index_inicial:

                                df_servicos.at[value, 'Data Horario Apresentacao']=\
                                    definir_horario_primeiro_hotel(df_servicos, value)
                                
                                data_horario_primeiro_hotel = df_servicos.at[value, 'Data Horario Apresentacao']
                                
                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]\
                                        ['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                paxs_total_roteiro+=paxs_hotel

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                            # Se não for a primeira linha do voo, mas o hotel for igual o hotel anterior, só repete o horário de apresentação

                            elif (df_servicos.at[value, 'Est Origem']==df_servicos.at[value-1, 'Est Origem']) | \
                                (df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']==df_servicos.at[value-1, 'Hoteis Juntos p/ Carro Principal']):

                                df_servicos.at[value, 'Data Horario Apresentacao']=\
                                    df_servicos.at[value-1, 'Data Horario Apresentacao']

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                            # Se não for a primeira linha do voo e o hotel não for igual ao anterior

                            else:

                                # Colhe a quantidade de paxs do hotel anterior, o bairro do hotel atual, a quantidade de paxs do hotel atual 
                                # e verifica se estoura a capacidade máxima de um carro

                                bairro=df_servicos.at[value, 'Região']

                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]\
                                        ['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                # Se estourar a capacidade do carro, aí trata como se fosse o primeiro hotel e adiciona 1 na variável carros
                                # pra, no final, eu saber quantos carros foram usados nesse roteiro e poder dividir 'igualmente' a quantidade de hoteis

                                if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                                    carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = \
                                        abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)

                                # Se não estourar a capacidade máxima

                                else:

                                    paxs_total_roteiro+=paxs_hotel

                                    # Sempre que inicia um carro, o bairro fica vazio. Portanto, se não for o primeiro hotel do carro, vai definir a variavel
                                    # intervalo_ref pra o robô saber quantos minutos deve adicionar até o próximo horário de apresentação

                                    if bairro!='':

                                        intervalo_ref = definir_intervalo_ref(df_servicos, value)
                                        
                                    if paxs_hotel>=st.session_state.pax_cinco_min:

                                        intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                                    data_horario_hotel = df_servicos.at[value-1, 'Data Horario Apresentacao']-\
                                        intervalo_ref

                                    if  data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):

                                        carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = \
                                            abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)

                                    else:

                                        df_servicos.at[value, 'Data Horario Apresentacao']=data_horario_hotel

                                        df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                    else:

                        roteiro+=1

                        carros = 1

                        paxs_total_roteiro = 0

                        contador_hoteis = 0

                        bairro = ''

                        # Loop no voo para colocar os horários

                        for index_2, value in df_ref['index'].items():

                            # Se for o primeiro hotel do voo, define o horário inicial, colhe o horário do hotel e inicia somatório de paxs do roteiro

                            if value==index_inicial:

                                df_servicos.at[value, 'Data Horario Apresentacao']=\
                                    definir_horario_primeiro_hotel(df_servicos, value)
                                
                                data_horario_primeiro_hotel = df_servicos.at[value, 'Data Horario Apresentacao']
                                
                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]\
                                        ['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                paxs_total_roteiro+=paxs_hotel

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                                contador_hoteis+=1

                            # Se não for a primeira linha do voo, mas o hotel for igual o hotel anterior, só repete o horário de apresentação

                            elif (df_servicos.at[value, 'Est Origem']==df_servicos.at[value-1, 'Est Origem']) | \
                                (df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']==df_servicos.at[value-1, 'Hoteis Juntos p/ Carro Principal']):

                                df_servicos.at[value, 'Data Horario Apresentacao']=\
                                    df_servicos.at[value-1, 'Data Horario Apresentacao']

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                            # Se não for a primeira linha do voo e o hotel não for igual ao anterior

                            else:   

                                # Colhe a quantidade de paxs do hotel anterior, o bairro do hotel atual, a quantidade de paxs do hotel atual 
                                # e verifica se estoura a capacidade máxima de um carro

                                contador_hoteis+=1

                                bairro=df_servicos.at[value, 'Região']

                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]\
                                        ['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                if contador_hoteis>max_hoteis:

                                    carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = \
                                        abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)
                                    
                                    contador_hoteis = 1
                                    
                                else:

                                    # Se estourar a capacidade do carro, aí trata como se fosse o primeiro hotel e adiciona 1 na variável carros
                                    # pra, no final, eu saber quantos carros foram usados nesse roteiro e poder dividir 'igualmente' a quantidade de hoteis

                                    if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                                        carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = \
                                            abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)
                                        
                                        contador_hoteis = 1

                                    # Se não estourar a capacidade máxima

                                    else:

                                        paxs_total_roteiro+=paxs_hotel

                                        # Sempre que inicia um carro, o bairro fica vazio. Portanto, se não for o primeiro hotel do carro, vai definir a variavel
                                        # intervalo_ref pra o robô saber quantos minutos deve adicionar até o próximo horário de apresentação

                                        if bairro!='':

                                            intervalo_ref = definir_intervalo_ref(df_servicos, value)
                                            
                                        if paxs_hotel>=st.session_state.pax_cinco_min:

                                            intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                                        data_horario_hotel = df_servicos.at[value-1, 'Data Horario Apresentacao']-\
                                            intervalo_ref

                                        if  data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):

                                            carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = \
                                            abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)
                                            
                                            contador_hoteis = 1

                                        else:

                                            df_servicos.at[value, 'Data Horario Apresentacao']=data_horario_hotel

                                            df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

    return df_servicos, roteiro

def gerar_roteiros_alternativos(df_servicos):

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())

    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    # Gerando roteiros alternativos

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        n_hoteis_df_ref = contar_hoteis_df(df_ref)

        divisao_inteira = n_hoteis_df_ref // df_ref['Carros'].max()

        if n_hoteis_df_ref % df_ref['Carros'].max() == 0:

            max_hoteis = divisao_inteira

        else:

            max_hoteis = divisao_inteira + 1

        carros = 1
    
        paxs_total_roteiro = 0

        contador_hoteis = 0

        bairro = ''

        for index in range(len(df_ref)):

            # Se for o primeiro hotel do voo, define o horário inicial, colhe o horário do hotel e inicia somatório de paxs do roteiro

            if index==0:

                df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                
                data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
                
                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                        ['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                paxs_total_roteiro+=paxs_hotel

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

                contador_hoteis+=1

            # Se não for a primeira linha do voo, mas o hotel for igual o hotel anterior, só repete o horário de apresentação

            elif (df_ref.at[index, 'Est Origem']==df_ref.at[index-1, 'Est Origem']) | \
                    (df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

                df_ref.at[index, 'Data Horario Apresentacao']=df_ref.at[index-1, 'Data Horario Apresentacao']

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

            # Se não for a primeira linha do voo e o hotel não for igual ao anterior

            else:

                # Colhe a quantidade de paxs do hotel anterior, o bairro do hotel atual, a quantidade de paxs do hotel atual 
                # e verifica se estoura a capacidade máxima de um carro

                contador_hoteis+=1

                if contador_hoteis>max_hoteis:

                    carros+=1

                    df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                    
                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                            ['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                    paxs_total_roteiro = 0

                    bairro = ''

                    paxs_total_roteiro+=paxs_hotel

                    df_ref.at[index, 'Roteiro'] = item

                    df_ref.at[index, 'Carros'] = carros
                    
                    contador_hoteis = 1
                    
                else:

                    bairro=df_ref.at[index, 'Região']

                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                            ['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    # Se estourar a capacidade do carro, aí trata como se fosse o primeiro hotel e adiciona 1 na variável carros
                    # pra, no final, eu saber quantos carros foram usados nesse roteiro e poder dividir 'igualmente' a quantidade de hoteis

                    if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                        carros+=1

                        df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)

                        data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                        paxs_total_roteiro = 0

                        bairro = ''

                        paxs_total_roteiro+=paxs_hotel

                        df_ref.at[index, 'Roteiro'] = item

                        df_ref.at[index, 'Carros'] = carros
                        
                        contador_hoteis = 1

                    # Se não estourar a capacidade máxima

                    else:

                        paxs_total_roteiro+=paxs_hotel

                        # Sempre que inicia um carro, o bairro fica vazio. Portanto, se não for o primeiro hotel do carro, vai definir a variavel
                        # intervalo_ref pra o robô saber quantos minutos deve adicionar até o próximo horário de apresentação

                        if bairro!='':

                            intervalo_ref = definir_intervalo_ref(df_ref, index)
                            
                        if paxs_hotel>=st.session_state.pax_cinco_min:

                            intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                        data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref

                        if data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):

                            carros+=1

                            df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)

                            data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                            paxs_total_roteiro = 0

                            bairro = ''

                            paxs_total_roteiro+=paxs_hotel

                            df_ref.at[index, 'Roteiro'] = item

                            df_ref.at[index, 'Carros'] = carros
                            
                            contador_hoteis = 1

                        else:

                            df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel

                            df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

        df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_ref], ignore_index=True)

    return df_roteiros_alternativos

def gerar_roteiros_alternativos_2(df_servicos, max_hoteis_ref, intervalo_pu_hotel):

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())
    
    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        carros = 1
    
        paxs_total_roteiro = 0

        contador_hoteis = 0

        bairro = ''

        for index in range(len(df_ref)):

            if index==0:

                df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                
                data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
                
                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                paxs_total_roteiro+=paxs_hotel

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

                contador_hoteis+=1

            elif (df_ref.at[index, 'Est Origem']==df_ref.at[index-1, 'Est Origem']) | (df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

                df_ref.at[index, 'Data Horario Apresentacao']=df_ref.at[index-1, 'Data Horario Apresentacao']

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

            else:

                contador_hoteis+=1

                if contador_hoteis>max_hoteis_ref:

                    carros+=1

                    df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                    
                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                    paxs_total_roteiro = 0

                    bairro = ''

                    paxs_total_roteiro+=paxs_hotel

                    df_ref.at[index, 'Roteiro'] = item

                    df_ref.at[index, 'Carros'] = carros
                    
                    contador_hoteis = 1
                    
                else:

                    bairro=df_ref.at[index, 'Região']

                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                        carros+=1

                        df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)

                        data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                        paxs_total_roteiro = 0

                        bairro = ''

                        paxs_total_roteiro+=paxs_hotel

                        df_ref.at[index, 'Roteiro'] = item

                        df_ref.at[index, 'Carros'] = carros
                        
                        contador_hoteis = 1

                    else:

                        paxs_total_roteiro+=paxs_hotel

                        if bairro!='':

                            intervalo_ref = definir_intervalo_ref(df_ref, index)
                            
                        if paxs_hotel>=st.session_state.pax_cinco_min:

                            intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                        data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref

                        if data_horario_primeiro_hotel - data_horario_hotel>intervalo_pu_hotel:

                            carros+=1

                            df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)

                            data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                            paxs_total_roteiro = 0

                            bairro = ''

                            paxs_total_roteiro+=paxs_hotel

                            df_ref.at[index, 'Roteiro'] = item

                            df_ref.at[index, 'Carros'] = carros
                            
                            contador_hoteis = 1

                        else:

                            df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel

                            df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

        df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_ref], ignore_index=True)

    return df_roteiros_alternativos

def gerar_roteiros_alternativos_3(df_servicos):

    df_servicos_ref = df_servicos.sort_values(by=['Roteiro', 'Carros', 'Data Horario Apresentacao']).reset_index(drop=True)

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())

    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos_ref[df_servicos_ref['Roteiro']==item].reset_index(drop=True)

        df_regiao_carro = df_ref[['Região', 'Carros']].drop_duplicates().reset_index(drop=True)

        df_regiao_duplicada = df_regiao_carro.groupby('Região')['Carros'].count().reset_index()

        carros_repetidos = df_regiao_duplicada['Carros'].max()

        df_ref = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        if carros_repetidos>1:

            carros = 1
    
            paxs_total_roteiro = 0
    
            contador_hoteis = 0
    
            bairro = ''
    
            for index in range(len(df_ref)):
    
                if index==0:
    
                    df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                    
                    data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
                    
                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                            ['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
    
                    paxs_total_roteiro+=paxs_hotel
    
                    df_ref = preencher_roteiro_carros(df_ref, item, carros, index)
    
                    contador_hoteis+=1

                elif (df_ref.at[index, 'Est Origem']==df_ref.at[index-1, 'Est Origem']) | \
                        (df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']):
    
                    df_ref.at[index, 'Data Horario Apresentacao']=df_ref.at[index-1, 'Data Horario Apresentacao']
    
                    df_ref = preencher_roteiro_carros(df_ref, item, carros, index)
    
                else:

                    bairro_anterior=df_ref.at[index-1, 'Região']

                    bairro=df_ref.at[index, 'Região']

                    if bairro_anterior!=bairro:

                        n_hoteis_novo_bairro = len(df_ref[df_ref['Região']==bairro]['Est Origem'].unique().tolist())

                        paxs_novo_bairro = df_ref[df_ref['Região'] == bairro]['Total ADT | CHD'].sum()

                        if n_hoteis_novo_bairro+contador_hoteis<=st.session_state.max_hoteis and paxs_total_roteiro+paxs_novo_bairro<=st.session_state.pax_max:
    
                            contador_hoteis+=1
            
                            if contador_hoteis>st.session_state.max_hoteis:
            
                                carros+=1
            
                                df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                                
                                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                                        ['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
            
                                data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
            
                                paxs_total_roteiro = 0
            
                                bairro = ''
            
                                paxs_total_roteiro+=paxs_hotel
            
                                df_ref.at[index, 'Roteiro'] = item
            
                                df_ref.at[index, 'Carros'] = carros
                                
                                contador_hoteis = 1
                                
                            else:

                                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                                        ['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
            
                                # Se estourar a capacidade do carro, aí trata como se fosse o primeiro hotel e adiciona 1 na variável carros
                                # pra, no final, eu saber quantos carros foram usados nesse roteiro e poder dividir 'igualmente' a quantidade de hoteis
            
                                if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:
            
                                    carros+=1
            
                                    df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
            
                                    data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
            
                                    paxs_total_roteiro = 0
            
                                    bairro = ''
            
                                    paxs_total_roteiro+=paxs_hotel
            
                                    df_ref.at[index, 'Roteiro'] = item
            
                                    df_ref.at[index, 'Carros'] = carros
                                    
                                    contador_hoteis = 1
            
                                # Se não estourar a capacidade máxima
            
                                else:
            
                                    paxs_total_roteiro+=paxs_hotel
            
                                    # Sempre que inicia um carro, o bairro fica vazio. Portanto, se não for o primeiro hotel do carro, vai definir a variavel
                                    # intervalo_ref pra o robô saber quantos minutos deve adicionar até o próximo horário de apresentação
            
                                    if bairro!='':
            
                                        intervalo_ref = definir_intervalo_ref(df_ref, index)
                                        
                                    if paxs_hotel>=st.session_state.pax_cinco_min:

                                        intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)
            
                                    data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref
            
                                    if data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):
            
                                        carros+=1
            
                                        df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
            
                                        data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
            
                                        paxs_total_roteiro = 0
            
                                        bairro = ''
            
                                        paxs_total_roteiro+=paxs_hotel
            
                                        df_ref.at[index, 'Roteiro'] = item
            
                                        df_ref.at[index, 'Carros'] = carros
                                        
                                        contador_hoteis = 1
            
                                    else:
            
                                        df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel
            
                                        df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

                        else:

                            carros+=1
            
                            df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                            
                            if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                                    ['Total ADT | CHD'].sum()
                                
                            else:
        
                                paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
        
                            data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
        
                            paxs_total_roteiro = 0
        
                            bairro = ''
        
                            paxs_total_roteiro+=paxs_hotel
        
                            df_ref.at[index, 'Roteiro'] = item
        
                            df_ref.at[index, 'Carros'] = carros
                            
                            contador_hoteis = 1

                    else:

                        contador_hoteis+=1
            
                        if contador_hoteis>st.session_state.max_hoteis:
        
                            carros+=1
        
                            df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                            
                            if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                                    ['Total ADT | CHD'].sum()
                                
                            else:
        
                                paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
        
                            data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
        
                            paxs_total_roteiro = 0
        
                            bairro = ''
        
                            paxs_total_roteiro+=paxs_hotel
        
                            df_ref.at[index, 'Roteiro'] = item
        
                            df_ref.at[index, 'Carros'] = carros
                            
                            contador_hoteis = 1
                            
                        else:
        
                            bairro=df_ref.at[index, 'Região']
        
                            if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                                    ['Total ADT | CHD'].sum()
                                
                            else:
        
                                paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
        
                            # Se estourar a capacidade do carro, aí trata como se fosse o primeiro hotel e adiciona 1 na variável carros
                            # pra, no final, eu saber quantos carros foram usados nesse roteiro e poder dividir 'igualmente' a quantidade de hoteis
        
                            if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:
        
                                carros+=1
        
                                df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
        
                                data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
        
                                paxs_total_roteiro = 0
        
                                bairro = ''
        
                                paxs_total_roteiro+=paxs_hotel
        
                                df_ref.at[index, 'Roteiro'] = item
        
                                df_ref.at[index, 'Carros'] = carros
                                
                                contador_hoteis = 1
        
                            # Se não estourar a capacidade máxima
        
                            else:
        
                                paxs_total_roteiro+=paxs_hotel
        
                                # Sempre que inicia um carro, o bairro fica vazio. Portanto, se não for o primeiro hotel do carro, vai definir a variavel
                                # intervalo_ref pra o robô saber quantos minutos deve adicionar até o próximo horário de apresentação
        
                                if bairro!='':
        
                                    intervalo_ref = definir_intervalo_ref(df_ref, index)
                                    
                                if paxs_hotel>=st.session_state.pax_cinco_min:

                                    intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                                data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref
        
                                df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel
        
                                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)
    
            df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_ref], ignore_index=True)

    return df_roteiros_alternativos

def gerar_roteiros_alternativos_4(df_servicos, max_hoteis):

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())

    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        carros = 1
    
        paxs_total_roteiro = 0

        contador_hoteis = 0

        bairro = ''

        for index in range(len(df_ref)):

            # Se for o primeiro hotel do voo, define o horário inicial, colhe o horário do hotel e inicia somatório de paxs do roteiro

            if index==0:

                df_ref.at[index, 'Data Horario Apresentacao']=\
                    definir_horario_primeiro_hotel(df_ref, index)
                
                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                        ['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                paxs_total_roteiro+=paxs_hotel

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

                contador_hoteis+=1

            # Se não for a primeira linha do voo, mas o hotel for igual o hotel anterior, só repete o horário de apresentação

            elif (df_ref.at[index, 'Est Origem']==df_ref.at[index-1, 'Est Origem']) | \
                    (df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

                df_ref.at[index, 'Data Horario Apresentacao']=df_ref.at[index-1, 'Data Horario Apresentacao']

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

            # Se não for a primeira linha do voo e o hotel não for igual ao anterior

            else:

                # Colhe a quantidade de paxs do hotel anterior, o bairro do hotel atual, a quantidade de paxs do hotel atual 
                # e verifica se estoura a capacidade máxima de um carro

                contador_hoteis+=1

                if contador_hoteis>max_hoteis:

                    carros+=1

                    df_ref.at[index, 'Data Horario Apresentacao']=\
                        definir_horario_primeiro_hotel(df_ref, index)
                    
                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                            ['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    paxs_total_roteiro = 0

                    bairro = ''

                    paxs_total_roteiro+=paxs_hotel

                    df_ref.at[index, 'Roteiro'] = item

                    df_ref.at[index, 'Carros'] = carros
                    
                    contador_hoteis = 1
                    
                else:

                    bairro=df_ref.at[index, 'Região']

                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                            ['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    # Se estourar a capacidade do carro, aí trata como se fosse o primeiro hotel e adiciona 1 na variável carros
                    # pra, no final, eu saber quantos carros foram usados nesse roteiro e poder dividir 'igualmente' a quantidade de hoteis

                    if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                        carros+=1

                        df_ref.at[index, 'Data Horario Apresentacao']=\
                            definir_horario_primeiro_hotel(df_ref, index)

                        paxs_total_roteiro = 0

                        bairro = ''

                        paxs_total_roteiro+=paxs_hotel

                        df_ref.at[index, 'Roteiro'] = item

                        df_ref.at[index, 'Carros'] = carros
                        
                        contador_hoteis = 1

                    # Se não estourar a capacidade máxima

                    else:

                        paxs_total_roteiro+=paxs_hotel

                        # Sempre que inicia um carro, o bairro fica vazio. Portanto, se não for o primeiro hotel do carro, vai definir a variavel
                        # intervalo_ref pra o robô saber quantos minutos deve adicionar até o próximo horário de apresentação

                        if bairro!='':

                            intervalo_ref = definir_intervalo_ref(df_ref, index)
                            
                        if paxs_hotel>=st.session_state.pax_cinco_min:

                            intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                        data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref

                        df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel

                        df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

        df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_ref], ignore_index=True)

    return df_roteiros_alternativos

def identificar_apoios_em_df(df_servicos, pax_max_utilitario, pax_max_van, pax_max_micro):

    df_servicos['Apoios'] = ''

    for n_roteiro in df_servicos['Roteiro'].unique().tolist():

        df_ref = df_servicos[df_servicos['Roteiro']==n_roteiro].reset_index()

        for veiculo in df_ref['Carros'].unique().tolist():

            df_ref_2 = df_ref[df_ref['Carros']==veiculo].reset_index(drop=True)

            pax_carro = df_ref[df_ref['Carros']==veiculo]['Total ADT | CHD'].sum()

            limitacao_van = df_ref_2['Van'].isnull().any()

            limitacao_micro = df_ref_2['Micro'].isnull().any()

            limitacao_bus = df_ref_2['Bus'].isnull().any()

            if pax_carro>pax_max_utilitario and pax_carro<=pax_max_van and limitacao_van:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Van'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            elif pax_carro>pax_max_van and pax_carro<=pax_max_micro and limitacao_micro:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Micro'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            elif pax_carro>pax_max_micro and limitacao_bus:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Bus'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            if len(df_ref_2)>1:

                for index in range(len(df_ref_2)):

                    indice = df_ref_2.at[index, 'index']

                    regiao_ref = df_ref_2.at[index, 'Região']

                    if regiao_ref == 'CAMURUPIM':

                        df_servicos.at[indice, 'Apoios']='Y'

    return df_servicos

def identificar_apoios_em_df_4(df_servicos, pax_max_utilitario, pax_max_van, pax_max_micro):

    df_servicos['Apoios'] = ''

    for n_roteiro in df_servicos['Roteiro'].unique().tolist():

        df_ref = df_servicos[df_servicos['Roteiro']==n_roteiro].reset_index()

        for veiculo in df_ref['Carros'].unique().tolist():

            df_ref_2 = df_ref[df_ref['Carros']==veiculo].reset_index(drop=True)

            pax_carro = df_ref[df_ref['Carros']==veiculo]['Total ADT | CHD'].sum()

            limitacao_van = df_ref_2['Van'].isnull().any()

            limitacao_micro = df_ref_2['Micro'].isnull().any()

            limitacao_bus = df_ref_2['Bus'].isnull().any()

            if pax_carro>pax_max_utilitario and pax_carro<=pax_max_van and limitacao_van:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Van'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            elif pax_carro>pax_max_van and pax_carro<=pax_max_micro and limitacao_micro:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Micro'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            elif pax_carro>pax_max_micro and limitacao_bus:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Bus'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            if len(df_ref_2)>1:

                for index in range(len(df_ref_2)):

                    indice = df_ref_2.at[index, 'index']

                    regiao_ref = df_ref_2.at[index, 'Região']

                    if regiao_ref == 'CAMURUPIM':

                        df_servicos.at[indice, 'Apoios']='Y'

    for n_roteiro in df_servicos['Roteiro'].unique().tolist():

        df_ref_4 = df_servicos[(df_servicos['Roteiro']==n_roteiro)].sort_values(by=['Apoios', 'Sequência'], ascending=[False, True])\
            .reset_index()
        
        df_ref_4_group_hoteis = df_ref_4.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Apoios': 'first'}).reset_index()

        df_ref_4_group_hoteis = df_ref_4_group_hoteis[(df_ref_4_group_hoteis['Total ADT | CHD']<=pax_max_utilitario) | 
                                                      (df_ref_4_group_hoteis['Apoios']!='')].reset_index(drop=True)
        
        lista_hoteis_apoio_4 = df_ref_4_group_hoteis['Est Origem'].unique().tolist()
        
        df_ref_4 = df_ref_4[df_ref_4['Est Origem'].isin(lista_hoteis_apoio_4)].reset_index(drop=True)

        for veiculo in df_ref_4['Carros'].unique().tolist():

            sem_roteiro = 0

            df_ref_5 = df_ref_4[df_ref_4['Carros']==veiculo].reset_index()

            max_hoteis = len(df_ref_4['Est Origem'].unique().tolist()) // 2

            df_ref_5_contagem_hoteis_apoios = df_ref_5[df_ref_5['Apoios']!=''].groupby('Est Origem')['Hoteis Juntos p/ Apoios'].first().reset_index()

            hoteis_total_apoio=0

            for index in range(len(df_ref_5_contagem_hoteis_apoios)):

                if index==0:

                    hoteis_total_apoio+=1

                elif not ((df_ref_5_contagem_hoteis_apoios.at[index, 'Hoteis Juntos p/ Apoios']==
                          df_ref_5_contagem_hoteis_apoios.at[index-1, 'Hoteis Juntos p/ Apoios']) and 
                          (~pd.isna(df_ref_5_contagem_hoteis_apoios.at[index, 'Hoteis Juntos p/ Apoios']))):

                    hoteis_total_apoio+=1

            if 'X' in df_ref_5['Apoios'].values:

                paxs_total_apoio = df_ref_5[df_ref_5['Apoios']=='X']['Total ADT | CHD'].sum()

            else:

                paxs_total_apoio = 0

            for index in range(len(df_ref_5)):

                hotel = df_ref_5.at[index, 'Est Origem']

                if not pd.isna(df_ref_5.at[index, 'Hoteis Juntos p/ Apoios']):
                                    
                    paxs_hotel = df_ref_5[df_ref_5['Hoteis Juntos p/ Apoios']==df_ref_5.at[index, 'Hoteis Juntos p/ Apoios']]\
                        ['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref_5[df_ref_5['Est Origem']==df_ref_5.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                if index==0:

                    if df_ref_5.at[index, 'Apoios']=='':

                        hoteis_total_apoio+=1

                        if paxs_total_apoio+paxs_hotel<=pax_max_van:

                            paxs_total_apoio+=paxs_hotel

                            df_servicos.loc[(df_servicos['Est Origem']==hotel) & (df_servicos['Roteiro']==n_roteiro) & 
                                            (df_servicos['Carros']==veiculo), 'Apoios']='X'

                        else:

                            sem_roteiro = 1

                            break

                elif df_ref_5.at[index, 'Est Origem']==df_ref_5.at[index-1, 'Est Origem']:

                    df_servicos.loc[(df_servicos['Est Origem']==hotel) & (df_servicos['Roteiro']==n_roteiro) & 
                                            (df_servicos['Carros']==veiculo), 'Apoios']='X'

                else:

                    
                    if df_ref_5.at[index, 'Apoios']=='':

                        if not ((df_ref_5.at[index, 'Hoteis Juntos p/ Apoios']==df_ref_5.at[index-1, 'Hoteis Juntos p/ Apoios']) and 
                                 (~pd.isna(df_ref_5.at[index, 'Hoteis Juntos p/ Apoios']))):

                            verificador_n_hoteis = hoteis_total_apoio+1

                        else:

                            verificador_n_hoteis = hoteis_total_apoio

                        if verificador_n_hoteis<=max_hoteis and paxs_total_apoio+paxs_hotel<=pax_max_van:

                            if not ((df_ref_5.at[index, 'Hoteis Juntos p/ Apoios']==df_ref_5.at[index-1, 'Hoteis Juntos p/ Apoios']) and 
                                    (~pd.isna(df_ref_5.at[index, 'Hoteis Juntos p/ Apoios']))):

                                hoteis_total_apoio+=1

                            paxs_total_apoio+=paxs_hotel

                            df_servicos.loc[(df_servicos['Est Origem']==hotel) & (df_servicos['Roteiro']==n_roteiro) & 
                                            (df_servicos['Carros']==veiculo), 'Apoios']='X'

                        else:

                            break

            if sem_roteiro==1:

                break

        if sem_roteiro==1:

            df_servicos = df_servicos[df_servicos['Roteiro']!=n_roteiro].reset_index(drop=True)

    df_servicos.loc[df_servicos['Região']=='CAMURUPIM', 'Apoios']='Y'

    return df_servicos

def gerar_roteiros_apoio(df_servicos):

    df_roteiros_apoios = df_servicos[(df_servicos['Apoios']=='X') | (df_servicos['Apoios']=='Y')].reset_index()

    df_roteiros_apoios['Carros Apoios']=''

    df_roteiros_carros = df_roteiros_apoios[['Roteiro', 'Carros']].drop_duplicates().reset_index(drop=True)

    for index, value in df_roteiros_carros['Roteiro'].items():

        veiculo = df_roteiros_carros.at[index, 'Carros']

        df_ref = df_servicos[(df_servicos['Roteiro']==value) & 
                                        (df_servicos['Carros']==veiculo)].reset_index()

        df_ref_apoios = df_ref[(df_ref['Apoios']=='X') | (df_ref['Apoios']=='Y')].reset_index(drop=True)

        carros = 1

        paxs_total_roteiro = 0

        contador_hoteis = 0

        bairro = ''

        for index in range(len(df_ref_apoios)):

            # Se for o primeiro hotel do voo, define o horário inicial, colhe o horário do hotel e inicia somatório de paxs do roteiro

            if index==0:

                df_ref_apoios.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref_apoios, index)

                df_ref_apoios.at[index, 'Data Horario Apresentacao']-=timedelta(hours=0, minutes=10, seconds=0)
                
                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                    paxs_hotel = df_ref_apoios[df_ref_apoios['Hoteis Juntos p/ Carro Principal']==df_ref_apoios.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                        ['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref_apoios[df_ref_apoios['Est Origem']==df_ref_apoios.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                paxs_total_roteiro+=paxs_hotel

                df_ref_apoios = preencher_roteiro_carros(df_ref_apoios, value, carros, index)

                contador_hoteis+=1

            # Se não for a primeira linha do voo, mas o hotel for igual o hotel anterior, só repete o horário de apresentação

            elif (df_ref_apoios.at[index, 'Est Origem']==df_ref_apoios.at[index-1, 'Est Origem']) | \
                (df_ref_apoios.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref_apoios.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

                df_ref_apoios.at[index, 'Data Horario Apresentacao']=df_ref_apoios.at[index-1, 'Data Horario Apresentacao']

                df_ref_apoios = preencher_roteiro_carros(df_ref_apoios, value, carros, index)

            elif df_ref_apoios.at[index, 'Apoios']=='Y':

                carros+=1

                df_ref_apoios.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref_apoios, index)

                paxs_total_roteiro = 0

                bairro = ''

                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                    paxs_hotel = df_ref_apoios[df_ref_apoios['Hoteis Juntos p/ Carro Principal']==df_ref_apoios.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                        ['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref_apoios[df_ref_apoios['Est Origem']==df_ref_apoios.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                paxs_total_roteiro+=paxs_hotel

                df_ref_apoios.at[index, 'Roteiro'] = value

                df_ref_apoios.at[index, 'Carros'] = carros

            # Se não for a primeira linha do voo e o hotel não for igual ao anterior

            else:

                bairro=df_ref_apoios.at[index, 'Região']

                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                    paxs_hotel = df_ref_apoios[df_ref_apoios['Hoteis Juntos p/ Carro Principal']==df_ref_apoios.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                        ['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref_apoios[df_ref_apoios['Est Origem']==df_ref_apoios.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                

                # Se estourar a capacidade do carro, aí trata como se fosse o primeiro hotel e adiciona 1 na variável carros
                # pra, no final, eu saber quantos carros foram usados nesse roteiro e poder dividir 'igualmente' a quantidade de hoteis

                if paxs_total_roteiro+paxs_hotel>18:

                    carros+=1

                    df_ref_apoios.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref_apoios, index)

                    paxs_total_roteiro = 0

                    bairro = ''

                    paxs_total_roteiro+=paxs_hotel

                    df_ref_apoios.at[index, 'Roteiro'] = value

                    df_ref_apoios.at[index, 'Carros'] = carros

                # Se não estourar a capacidade máxima

                else:

                    paxs_total_roteiro+=paxs_hotel

                    # Sempre que inicia um carro, o bairro fica vazio. Portanto, se não for o primeiro hotel do carro, vai definir a variavel
                    # intervalo_ref pra o robô saber quantos minutos deve adicionar até o próximo horário de apresentação

                    if bairro!='':

                        intervalo_ref = definir_intervalo_ref(df_ref_apoios, index)
                        
                    if paxs_hotel>=st.session_state.pax_cinco_min:

                        intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                    data_horario_hotel = df_ref_apoios.at[index-1, 'Data Horario Apresentacao']-intervalo_ref

                    df_ref_apoios.at[index, 'Data Horario Apresentacao']=data_horario_hotel

                    df_ref_apoios = preencher_roteiro_carros(df_ref_apoios, value, carros, index)

        for index, value in df_ref_apoios['index'].items():

            df_roteiros_apoios.loc[df_roteiros_apoios['index']==value, 'Data Horario Apresentacao']=\
                df_ref_apoios.at[index, 'Data Horario Apresentacao']

            df_roteiros_apoios.loc[df_roteiros_apoios['index']==value, 'Carros Apoios']=df_ref_apoios.at[index, 'Carros']

            df_servicos.at[value, 'Data Horario Apresentacao']=df_ref_apoios.at[index, 'Data Horario Apresentacao']

    if 'index' in df_roteiros_apoios.columns.tolist():

        df_roteiros_apoios = df_roteiros_apoios.drop(columns=['index'])

    return df_servicos, df_roteiros_apoios

def plotar_roteiros_simples(df_servicos, row3, coluna):

    for item in df_servicos['Roteiro'].unique().tolist():

        df_ref_1 = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        horario_inicial_voo = df_ref_1['Horario Voo'].min()

        horario_final_voo = df_ref_1['Horario Voo'].max()

        if horario_inicial_voo == horario_final_voo:

            titulo_voos = f'{horario_inicial_voo}'

        else:

            titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

        lista_nome_voos = df_ref_1['Voo'].unique().tolist()

        voos_unidos = ' + '.join(lista_nome_voos)

        for carro in df_ref_1['Carros'].unique().tolist():

            df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

            modo = df_ref_2.at[0, 'Modo do Servico']

            total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

            paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

            if modo=='REGULAR':
    
                titulo_roteiro = f'Roteiro {item}'

                titulo_carro = f'Veículo {carro}'

                titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

            else:

                reserva = df_ref_2.at[0, 'Reserva']

                titulo_roteiro = f'Roteiro {item}'

                titulo_carro = f'Veículo {carro}'

                titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

            df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'}).sort_values(by='Data Horario Apresentacao').reset_index()

            df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
        
            with row3[coluna]:

                container = st.container(border=True, height=500)

                container.header(titulo_roteiro)

                container.subheader(titulo_carro)

                container.markdown(titulo_modo_voo_pax)

                container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                if coluna==2:

                    coluna=0

                else:

                    coluna+=1

    return coluna

def plotar_roteiros_gerais_com_apoio(df_servicos, df_apoios, df_alternativos, df_apoios_alternativos, coluna, row3):

    for item in df_servicos['Roteiro'].unique().tolist():

        if not item in df_alternativos['Roteiro'].unique().tolist():

            df_ref_1 = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)
    
            horario_inicial_voo = df_ref_1['Horario Voo'].min()
    
            horario_final_voo = df_ref_1['Horario Voo'].max()
    
            if horario_inicial_voo == horario_final_voo:
    
                titulo_voos = f'{horario_inicial_voo}'
    
            else:
    
                titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

            lista_nome_voos = df_ref_1['Voo'].unique().tolist()

            voos_unidos = ' + '.join(lista_nome_voos)
    
            for carro in df_ref_1['Carros'].unique().tolist():
    
                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)
    
                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))
    
                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())
    
                if modo=='REGULAR':
    
                    titulo_roteiro = f'Roteiro {item}'
    
                    titulo_carro = f'Veículo {carro}'
    
                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                else:
    
                    reserva = df_ref_2.at[0, 'Reserva']
    
                    titulo_roteiro = f'Roteiro {item}'
    
                    titulo_carro = f'Veículo {carro}'
    
                    titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                lista_apoios = df_ref_2['Apoios'].unique().tolist()
    
                if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'}).sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:
    
                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'}).sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:
    
                    container = st.container(border=True, height=500)
    
                    container.header(titulo_roteiro)
    
                    container.subheader(titulo_carro)
    
                    container.markdown(titulo_modo_voo_pax)
    
                    if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                    else:
    
                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                    if coluna==2:
    
                        coluna=0
    
                    else:
    
                        coluna+=1
    
                df_ref_apoio = df_apoios[(df_apoios['Roteiro']==item) & (df_apoios['Carros']==carro)].reset_index(drop=True)
    
                if len(df_ref_apoio)>0:
    
                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():
    
                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))
    
                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())
    
                        titulo_roteiro = f'Apoio | Roteiro {item}'
    
                        titulo_carro_principal = f'Veículo Principal {carro}'
    
                        titulo_carro = f'Veículo Apoio {carro_2}'
    
                        titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'}).sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:
    
                            container = st.container(border=True, height=500)
    
                            container.header(titulo_roteiro)
    
                            container.subheader(titulo_carro_principal)
    
                            container.subheader(titulo_carro)
    
                            container.markdown(titulo_modo_voo_pax)
    
                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                            if coluna==2:
    
                                coluna=0
    
                            else:
    
                                coluna+=1

        else:

            if item in  df_alternativos['Roteiro'].unique().tolist():
    
                df_ref_1 = df_alternativos[df_alternativos['Roteiro']==item].reset_index(drop=True)
    
                horario_inicial_voo = df_ref_1['Horario Voo'].min()
    
                horario_final_voo = df_ref_1['Horario Voo'].max()
    
                if horario_inicial_voo == horario_final_voo:
    
                    titulo_voos = f'{horario_inicial_voo}'
    
                else:
    
                    titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

                lista_nome_voos = df_ref_1['Voo'].unique().tolist()

                voos_unidos = ' + '.join(lista_nome_voos)
    
                for carro in df_ref_1['Carros'].unique().tolist():
    
                    df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)
    
                    modo = df_ref_2.at[0, 'Modo do Servico']

                    total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))
    
                    paxs_total = int(df_ref_2['Total ADT | CHD'].sum())
    
                    if modo=='REGULAR':
    
                        titulo_roteiro = f'Opção Alternativa 1 | Roteiro {item}'
    
                        titulo_carro = f'Veículo {carro}'
    
                        titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                    else:
    
                        reserva = df_ref_2.at[0, 'Reserva']
    
                        titulo_roteiro = f'Opção Alternativa 1 | Roteiro {item}'
    
                        titulo_carro = f'Veículo {carro}'
    
                        titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                    lista_apoios = df_ref_2['Apoios'].unique().tolist()
    
                    if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                        df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'}).sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                    else:
    
                        df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'}).sort_values(by='Data Horario Apresentacao').reset_index()
                        
                    df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                
                    with row3[coluna]:
    
                        container = st.container(border=True, height=500)
    
                        container.header(titulo_roteiro)
    
                        container.subheader(titulo_carro)
    
                        container.markdown(titulo_modo_voo_pax)
    
                        if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                            container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                        else:
    
                            container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                        if coluna==2:
    
                            coluna=0
    
                        else:
    
                            coluna+=1
    
                    df_ref_apoio = df_apoios_alternativos[(df_apoios_alternativos['Roteiro']==item) & (df_apoios_alternativos['Carros']==carro)].reset_index(drop=True)
    
                    if len(df_ref_apoio)>0:
    
                        for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():
    
                            df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                            total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))
    
                            paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())
    
                            titulo_roteiro = f'Apoio | Opção Alternativa 1 | Roteiro {item}'
    
                            titulo_carro_principal = f'Veículo Principal {carro}'
    
                            titulo_carro = f'Veículo Apoio {carro_2}'
    
                            titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                            df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'}).sort_values(by='Data Horario Apresentacao').reset_index()
                            
                            df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                            
                            with row3[coluna]:
    
                                container = st.container(border=True, height=500)
    
                                container.header(titulo_roteiro)
    
                                container.subheader(titulo_carro_principal)
    
                                container.subheader(titulo_carro)
    
                                container.markdown(titulo_modo_voo_pax)
    
                                container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                                if coluna==2:
    
                                    coluna=0
    
                                else:
    
                                    coluna+=1

    return coluna

def definir_html(df_ref):

    if 'Data Horario Apresentacao' in df_ref.columns:
        
        df_ref = df_ref.sort_values(by='Data Horario Apresentacao').reset_index(drop=True)

        df_ref['Data Horario Apresentacao'] = df_ref['Data Horario Apresentacao'].dt.strftime('%d/%m/%Y %H:%M:%S')

    html=df_ref.to_html(index=False)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                text-align: center;  /* Centraliza o texto */
            }}
            table {{
                margin: 0 auto;  /* Centraliza a tabela */
                border-collapse: collapse;  /* Remove espaço entre as bordas da tabela */
            }}
            th, td {{
                padding: 8px;  /* Adiciona espaço ao redor do texto nas células */
                border: 1px solid black;  /* Adiciona bordas às células */
                text-align: center;
            }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """

    return html

def definir_html_2(df_ref):

    if 'Data Horario Apresentacao' in df_ref.columns:

        df_ref['Data Horario Apresentacao'] = df_ref['Data Horario Apresentacao'].dt.strftime('%d/%m/%Y %H:%M:%S')

    html=df_ref.to_html(index=False)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                text-align: center;  /* Centraliza o texto */
            }}
            table {{
                margin: 0 auto;  /* Centraliza a tabela */
                border-collapse: collapse;  /* Remove espaço entre as bordas da tabela */
            }}
            th, td {{
                padding: 8px;  /* Adiciona espaço ao redor do texto nas células */
                border: 1px solid black;  /* Adiciona bordas às células */
                text-align: center;
            }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """

    return html

def criar_output_html(nome_html, html):

    if len(st.session_state.df_juncao_voos)>0:

        with open(nome_html, "w", encoding="utf-8") as file:

            nome_regiao = nome_html.split()[2]

            nome_regiao = nome_regiao.replace('.html', '')

            file.write(f'<p style="font-size:50px;">{nome_regiao} | {st.session_state.data_roteiro_ref}</p>\n\n')

            file.write(f'<p style="font-size:40px;">Junção de Voos</p>\n\n')
            
            file.write(html)

        if len(st.session_state.df_horario_esp_ultimo_hotel)>0:

            html = definir_html_2(st.session_state.df_horario_esp_ultimo_hotel)
    
            with open(nome_html, "a", encoding="utf-8") as file:
    
                file.write(f'<p style="font-size:40px;">Antecipações Específicas</p>')
                
                file.write(html)

        with open(nome_html, "a", encoding="utf-8") as file:

            file.write(f'<p style="font-size:40px;">Roteiros</p>\n\n')

    elif len(st.session_state.df_horario_esp_ultimo_hotel)>0:

        html = definir_html_2(st.session_state.df_horario_esp_ultimo_hotel)
    
        with open(nome_html, "w", encoding="utf-8") as file:

            nome_regiao = nome_html.split()[2]

            nome_regiao = nome_regiao.replace('.html', '')

            file.write(f'<p style="font-size:50px;">{nome_regiao} | {st.session_state.data_roteiro_ref}</p>\n\n')
    
            file.write(f'<p style="font-size:40px;">Antecipações Específicas</p>')
            
            file.write(html)

            file.write(f'<p style="font-size:40px;">Roteiros</p>\n\n')

    else:

        with open(nome_html, "w", encoding="utf-8") as file:

            nome_regiao = nome_html.split()[2]

            nome_regiao = nome_regiao.replace('.html', '')

            file.write(f'<p style="font-size:50px;">{nome_regiao} | {st.session_state.data_roteiro_ref}</p>\n\n')

            file.write(f'<p style="font-size:40px;">Roteiros</p>\n\n')

def inserir_html_2(nome_html, df):

    html = definir_html_2(df)

    with open(nome_html, "a", encoding="utf-8") as file:

        file.write('<br><br><br>')

        file.write(f'<p style="font-size:40px;">Mapa de Serviços</p>\n\n')
        
        file.write(html)

def inserir_roteiros_html_com_apoio(nome_html, df_pdf, df_pdf_apoios):

    roteiro = 0

    df_ref = df_pdf[['Roteiro', 'Carros', 'Horario Voo / Menor Horário']].drop_duplicates().reset_index(drop=True)

    for index in range(len(df_ref)):

        roteiro_ref = df_ref.at[index, 'Roteiro']

        carro_ref = df_ref.at[index, 'Carros']

        hv_ref = df_ref.at[index, 'Horario Voo / Menor Horário']

        df_ref_roteiro = df_pdf[(df_pdf['Roteiro']==roteiro_ref) & (df_pdf['Carros']==carro_ref) & 
                          (df_pdf['Horario Voo / Menor Horário']==hv_ref)].reset_index(drop=True)
        
        lista_nome_voos = df_ref_roteiro['Voo'].unique().tolist()

        voos_unidos = ' + '.join(lista_nome_voos)

        if carro_ref==1:

            roteiro+=1

        for carro in df_ref_roteiro['Carros'].unique().tolist():

            df_ref_carro = df_ref_roteiro[df_ref_roteiro['Carros']==carro]\
                [['Roteiro', 'Carros', 'Modo do Servico', 'Voo', 'Horario Voo', 'Junção', 'Est Origem', 'Total ADT | CHD', 
                'Data Horario Apresentacao']].reset_index(drop=True)
            
            total_paxs = df_ref_carro['Total ADT | CHD'].sum()
            
            html = definir_html(df_ref_carro)

            with open(nome_html, "a", encoding="utf-8") as file:

                file.write(f'<p style="font-size:30px;">Roteiro {roteiro} | Carro {carro} | {voos_unidos} | {int(total_paxs)} Paxs</p>\n\n')

                file.write(html)

                file.write('\n\n')

            df_ref_apoio = df_pdf_apoios[(df_pdf_apoios['Roteiro']==roteiro_ref) & (df_pdf_apoios['Carros']==carro_ref)].reset_index(drop=True)

            if len(df_ref_apoio)>0:

                for carro_apoio in df_ref_apoio['Carros Apoios'].unique().tolist():

                    df_ref_carro_apoio = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_apoio]\
                        [['Roteiro', 'Carros Apoios', 'Modo do Servico', 'Voo', 'Horario Voo', 'Junção', 'Est Origem', 'Total ADT | CHD', 
                          'Data Horario Apresentacao']].reset_index(drop=True)
                    
                    total_paxs = df_ref_carro_apoio['Total ADT | CHD'].sum()
            
                    html = definir_html(df_ref_carro_apoio)

                    with open(nome_html, "a", encoding="utf-8") as file:

                        file.write(f'<p style="font-size:30px;">Apoio Roteiro Principal {roteiro} | Carro Principal {carro} | Carro Apoio {carro_apoio} | {voos_unidos} | {int(total_paxs)} Paxs</p>\n\n')

                        file.write(html)

                        file.write('\n\n')

def verificar_rotas_alternativas_ou_plotar_roteiros_com_apoio(df_roteiros_alternativos, row_warning, row3, coluna, df_hoteis_pax_max, df_router_filtrado_2, df_roteiros_apoios, 
                                                    df_roteiros_apoios_alternativos, df_juncao_voos, nome_html):

    if len(st.session_state.df_roteiros_alternativos)>0 or len(st.session_state.df_roteiros_alternativos_2)>0 or len(st.session_state.df_roteiros_alternativos_3)>0 or \
        len(st.session_state.df_roteiros_alternativos_4)>0 or len(st.session_state.df_roteiros_alternativos_5)>0:

        with row_warning[0]:

            st.warning('Existem opções alternativas para algumas rotas. Por favor, informe quais rotas alternativas serão usadas.')

    else:

        lista_dfs = [df_hoteis_pax_max, df_router_filtrado_2, df_roteiros_apoios]

        n_carros = 0

        for df in lista_dfs:
            
            if len(df)>0:

                n_carros += len(df[['Roteiro', 'Carros']].drop_duplicates())

        with row_warning[0]:

            st.header(f'A roteirização usou um total de {n_carros} carros')

        if len(df_hoteis_pax_max)>0:

            coluna = plotar_roteiros_simples(df_hoteis_pax_max, row3, coluna)

        coluna = plotar_roteiros_gerais_com_apoio(df_router_filtrado_2, df_roteiros_apoios, df_roteiros_alternativos, 
                                        df_roteiros_apoios_alternativos, coluna, row3)

        html = definir_html(df_juncao_voos)

        criar_output_html(nome_html, html)

        df_pdf = pd.concat([df_router_filtrado_2, df_hoteis_pax_max], 
                           ignore_index=True)
        
        df_pdf_2 = df_pdf[['Reserva', 'Data Horario Apresentacao']].sort_values(by='Reserva').reset_index(drop=True)

        st.session_state.df_insercao = df_pdf[['Id_Reserva', 'Id_Servico', 'Data Horario Apresentacao', 'Data Horario Apresentacao Original']].reset_index(drop=True)
        
        for index in range(len(df_pdf)):

            tipo_de_servico_ref = df_pdf.at[index, 'Modo do Servico']

            juncao_ref_2 = df_pdf.at[index, 'Junção']

            if tipo_de_servico_ref == 'REGULAR' and not pd.isna(juncao_ref_2):

                df_pdf.at[index, 'Horario Voo / Menor Horário'] = df_pdf.at[index, 'Menor Horário']

            elif (tipo_de_servico_ref == 'REGULAR' and pd.isna(juncao_ref_2)) or (tipo_de_servico_ref != 'REGULAR'):

                df_pdf.at[index, 'Horario Voo / Menor Horário'] = df_pdf.at[index, 'Horario Voo']

        df_pdf = df_pdf.sort_values(by=['Horario Voo / Menor Horário', 'Junção']).reset_index(drop=True)

        inserir_roteiros_html_com_apoio(nome_html, df_pdf, df_roteiros_apoios)

        inserir_html_2(nome_html, df_pdf_2)

        with open(nome_html, "r", encoding="utf-8") as file:

            html_content = file.read()

        salvar_rotas_historico(df_pdf)

        st.download_button(
            label="Baixar Arquivo HTML",
            data=html_content,
            file_name=nome_html,
            mime="text/html"
        )

def plotar_roteiros_gerais_alternativos_com_apoio(df_servicos, df_apoios, df_alternativos, df_alternativos_2, df_alternativos_3, df_alternativos_4, df_alternativos_5, df_apoios_alternativos, 
                                                  df_apoios_alternativos_2, df_apoios_alternativos_3, df_apoios_alternativos_4, df_apoios_alternativos_5, coluna, row3):

    df_rotas_alternativas = pd.concat([df_alternativos['Roteiro'], df_alternativos_2['Roteiro'], df_alternativos_3['Roteiro'], df_alternativos_4['Roteiro'], df_alternativos_5['Roteiro']], 
                                      ignore_index=True).reset_index()

    lista_todas_rotas_alternativas = sorted(df_rotas_alternativas['Roteiro'].unique().tolist())

    for item in lista_todas_rotas_alternativas:

        df_ref_1 = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        horario_inicial_voo = df_ref_1['Horario Voo'].min()

        horario_final_voo = df_ref_1['Horario Voo'].max()

        if horario_inicial_voo == horario_final_voo:

            titulo_voos = f'{horario_inicial_voo}'

        else:

            titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

        lista_nome_voos = df_ref_1['Voo'].unique().tolist()

        voos_unidos = ' + '.join(lista_nome_voos)

        for carro in df_ref_1['Carros'].unique().tolist():

            df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

            modo = df_ref_2.at[0, 'Modo do Servico']

            total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

            paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

            if modo=='REGULAR':

                titulo_roteiro = f'Roteiro {item}'

                titulo_carro = f'Veículo {carro}'

                titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

            else:

                reserva = df_ref_2.at[0, 'Reserva']

                titulo_roteiro = f'Roteiro {item}'

                titulo_carro = f'Veículo {carro}'

                titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

            lista_apoios = df_ref_2['Apoios'].unique().tolist()

            if 'X' in lista_apoios or 'Y' in lista_apoios:

                df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                    .sort_values(by='Data Horario Apresentacao').reset_index()
                
                df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

            else:

                df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                    .sort_values(by='Data Horario Apresentacao').reset_index()
                
            df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
        
            with row3[coluna]:

                container = st.container(border=True, height=500)

                container.header(titulo_roteiro)

                container.subheader(titulo_carro)

                container.markdown(titulo_modo_voo_pax)

                if 'X' in lista_apoios or 'Y' in lista_apoios:

                    container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)

                else:

                    container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                if coluna==2:

                    coluna=0

                else:

                    coluna+=1

            df_ref_apoio = df_apoios[(df_apoios['Roteiro']==item) & (df_apoios['Carros']==carro)].reset_index(drop=True)

            if len(df_ref_apoio)>0:

                for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():

                    df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                    total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))

                    paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                    titulo_roteiro = f'Apoio | Roteiro {item}'

                    titulo_carro_principal = f'Veículo Principal {carro}'

                    titulo_carro = f'Veículo Apoio {carro_2}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                    df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                    
                    with row3[coluna]:

                        container = st.container(border=True, height=500)

                        container.header(titulo_roteiro)

                        container.subheader(titulo_carro_principal)

                        container.subheader(titulo_carro)

                        container.markdown(titulo_modo_voo_pax)

                        container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                        if coluna==2:

                            coluna=0

                        else:

                            coluna+=1

        if item in  df_alternativos['Roteiro'].unique().tolist():

            df_ref_1 = df_alternativos[df_alternativos['Roteiro']==item].reset_index(drop=True)

            coluna = plotar_divisao_de_rotas(coluna, row3)

            horario_inicial_voo = df_ref_1['Horario Voo'].min()

            horario_final_voo = df_ref_1['Horario Voo'].max()

            if horario_inicial_voo == horario_final_voo:

                titulo_voos = f'{horario_inicial_voo}'

            else:

                titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

            lista_nome_voos = df_ref_1['Voo'].unique().tolist()

            voos_unidos = ' + '.join(lista_nome_voos)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':

                    titulo_roteiro = f'Opção Alternativa 1 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 1 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                lista_apoios = df_ref_2['Apoios'].unique().tolist()

                if 'X' in lista_apoios or 'Y' in lista_apoios:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.header(titulo_roteiro)

                    container.subheader(titulo_carro)

                    container.markdown(titulo_modo_voo_pax)

                    if 'X' in lista_apoios or 'Y' in lista_apoios:

                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)

                    else:

                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

                df_ref_apoio = df_apoios_alternativos[(df_apoios_alternativos['Roteiro']==item) & 
                                                                (df_apoios_alternativos['Carros']==carro)].reset_index(drop=True)

                if len(df_ref_apoio)>0:

                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():

                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))

                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                        titulo_roteiro = f'Apoio | Opção Alternativa 1 | Roteiro {item}'

                        titulo_carro_principal = f'Veículo Principal {carro}'

                        titulo_carro = f'Veículo Apoio {carro_2}'

                        titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:

                            container = st.container(border=True, height=500)

                            container.header(titulo_roteiro)

                            container.subheader(titulo_carro_principal)

                            container.subheader(titulo_carro)

                            container.markdown(titulo_modo_voo_pax)

                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                            if coluna==2:

                                coluna=0

                            else:

                                coluna+=1

        if item in  df_alternativos_2['Roteiro'].unique().tolist():

            df_ref_1 = df_alternativos_2[df_alternativos_2['Roteiro']==item].reset_index(drop=True)

            coluna = plotar_divisao_de_rotas(coluna, row3)

            horario_inicial_voo = df_ref_1['Horario Voo'].min()

            horario_final_voo = df_ref_1['Horario Voo'].max()

            if horario_inicial_voo == horario_final_voo:

                titulo_voos = f'{horario_inicial_voo}'

            else:

                titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

            lista_nome_voos = df_ref_1['Voo'].unique().tolist()

            voos_unidos = ' + '.join(lista_nome_voos)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':

                    titulo_roteiro = f'Opção Alternativa 2 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 2 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                lista_apoios = df_ref_2['Apoios'].unique().tolist()

                if 'X' in lista_apoios or 'Y' in lista_apoios:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()

                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.header(titulo_roteiro)

                    container.subheader(titulo_carro)

                    container.markdown(titulo_modo_voo_pax)

                    if 'X' in lista_apoios or 'Y' in lista_apoios:

                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)

                    else:

                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

                df_ref_apoio = df_apoios_alternativos_2[(df_apoios_alternativos_2['Roteiro']==item) & 
                                                                (df_apoios_alternativos_2['Carros']==carro)].reset_index(drop=True)

                if len(df_ref_apoio)>0:

                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():

                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))

                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                        titulo_roteiro = f'Apoio | Opção Alternativa 2 | Roteiro {item}'

                        titulo_carro_principal = f'Veículo Principal {carro}'

                        titulo_carro = f'Veículo Apoio {carro_2}'

                        titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:

                            container = st.container(border=True, height=500)

                            container.header(titulo_roteiro)

                            container.subheader(titulo_carro_principal)

                            container.subheader(titulo_carro)

                            container.markdown(titulo_modo_voo_pax)

                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                            if coluna==2:

                                coluna=0

                            else:

                                coluna+=1

        if item in  df_alternativos_3['Roteiro'].unique().tolist():

            df_ref_1 = df_alternativos_3[df_alternativos_3['Roteiro']==item].reset_index(drop=True)

            coluna = plotar_divisao_de_rotas(coluna, row3)

            horario_inicial_voo = df_ref_1['Horario Voo'].min()

            horario_final_voo = df_ref_1['Horario Voo'].max()

            if horario_inicial_voo == horario_final_voo:

                titulo_voos = f'{horario_inicial_voo}'

            else:

                titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

            lista_nome_voos = df_ref_1['Voo'].unique().tolist()

            voos_unidos = ' + '.join(lista_nome_voos)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':

                    titulo_roteiro = f'Opção Alternativa 3 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 3 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                lista_apoios = df_ref_2['Apoios'].unique().tolist()

                if 'X' in lista_apoios or 'Y' in lista_apoios:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()

                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.header(titulo_roteiro)

                    container.subheader(titulo_carro)

                    container.markdown(titulo_modo_voo_pax)

                    if 'X' in lista_apoios or 'Y' in lista_apoios:

                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)

                    else:

                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

                df_ref_apoio = df_apoios_alternativos_3[(df_apoios_alternativos_3['Roteiro']==item) & 
                                                        (df_apoios_alternativos_3['Carros']==carro)].reset_index(drop=True)

                if len(df_ref_apoio)>0:

                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():

                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))

                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                        titulo_roteiro = f'Apoio | Opção Alternativa 3 | Roteiro {item}'

                        titulo_carro_principal = f'Veículo Principal {carro}'

                        titulo_carro = f'Veículo Apoio {carro_2}'

                        titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:

                            container = st.container(border=True, height=500)

                            container.header(titulo_roteiro)

                            container.subheader(titulo_carro_principal)

                            container.subheader(titulo_carro)

                            container.markdown(titulo_modo_voo_pax)

                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                            if coluna==2:

                                coluna=0

                            else:

                                coluna+=1

        if item in  df_alternativos_4['Roteiro'].unique().tolist():

            df_ref_1 = df_alternativos_4[df_alternativos_4['Roteiro']==item].reset_index(drop=True)

            coluna = plotar_divisao_de_rotas(coluna, row3)

            horario_inicial_voo = df_ref_1['Horario Voo'].min()

            horario_final_voo = df_ref_1['Horario Voo'].max()

            if horario_inicial_voo == horario_final_voo:

                titulo_voos = f'{horario_inicial_voo}'

            else:

                titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

            lista_nome_voos = df_ref_1['Voo'].unique().tolist()

            voos_unidos = ' + '.join(lista_nome_voos)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':

                    titulo_roteiro = f'Opção Alternativa 4 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 4 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                lista_apoios = df_ref_2['Apoios'].unique().tolist()

                if 'X' in lista_apoios or 'Y' in lista_apoios:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.header(titulo_roteiro)

                    container.subheader(titulo_carro)

                    container.markdown(titulo_modo_voo_pax)

                    if 'X' in lista_apoios or 'Y' in lista_apoios:

                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)

                    else:

                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

                df_ref_apoio = df_apoios_alternativos_4[(df_apoios_alternativos_4['Roteiro']==item) & 
                                                        (df_apoios_alternativos_4['Carros']==carro)].reset_index(drop=True)

                if len(df_ref_apoio)>0:

                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():

                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))

                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                        titulo_roteiro = f'Apoio | Opção Alternativa 4 | Roteiro {item}'

                        titulo_carro_principal = f'Veículo Principal {carro}'

                        titulo_carro = f'Veículo Apoio {carro_2}'

                        titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()

                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:

                            container = st.container(border=True, height=500)

                            container.header(titulo_roteiro)

                            container.subheader(titulo_carro_principal)

                            container.subheader(titulo_carro)

                            container.markdown(titulo_modo_voo_pax)

                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                            if coluna==2:

                                coluna=0

                            else:

                                coluna+=1

        if item in  df_alternativos_5['Roteiro'].unique().tolist():

            df_ref_1 = df_alternativos_5[df_alternativos_5['Roteiro']==item].reset_index(drop=True)

            coluna = plotar_divisao_de_rotas(coluna, row3)

            horario_inicial_voo = df_ref_1['Horario Voo'].min()

            horario_final_voo = df_ref_1['Horario Voo'].max()

            if horario_inicial_voo == horario_final_voo:

                titulo_voos = f'{horario_inicial_voo}'

            else:

                titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

            lista_nome_voos = df_ref_1['Voo'].unique().tolist()

            voos_unidos = ' + '.join(lista_nome_voos)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':

                    titulo_roteiro = f'Opção Alternativa 5 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 5 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                lista_apoios = df_ref_2['Apoios'].unique().tolist()

                if 'X' in lista_apoios or 'Y' in lista_apoios:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:

                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.header(titulo_roteiro)

                    container.subheader(titulo_carro)

                    container.markdown(titulo_modo_voo_pax)

                    if 'X' in lista_apoios or 'Y' in lista_apoios:

                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)

                    else:

                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

                df_ref_apoio = df_apoios_alternativos_5[(df_apoios_alternativos_5['Roteiro']==item) & 
                                                        (df_apoios_alternativos_5['Carros']==carro)].reset_index(drop=True)

                if len(df_ref_apoio)>0:

                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():

                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))

                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())

                        titulo_roteiro = f'Apoio | Opção Alternativa 5 | Roteiro {item}'

                        titulo_carro_principal = f'Veículo Principal {carro}'

                        titulo_carro = f'Veículo Apoio {carro_2}'

                        titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()

                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:

                            container = st.container(border=True, height=500)

                            container.header(titulo_roteiro)

                            container.subheader(titulo_carro_principal)

                            container.subheader(titulo_carro)

                            container.markdown(titulo_modo_voo_pax)

                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                            if coluna==2:

                                coluna=0

                            else:

                                coluna+=1

        coluna = plotar_divisao_de_rotas(coluna, row3)

    return coluna

def plotar_roteiros_gerais_final_com_apoio(df_servicos, df_apoios, df_alternativos, df_apoios_alternativos, coluna):

    lista_roteiros = df_servicos['Roteiro'].unique().tolist()

    lista_roteiros.extend(df_alternativos['Roteiro'].unique().tolist())

    lista_roteiros = sorted(lista_roteiros)

    for item in lista_roteiros:

        if not item in df_alternativos['Roteiro'].unique().tolist():

            df_ref_1 = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)
    
            horario_inicial_voo = df_ref_1['Horario Voo'].min()
    
            horario_final_voo = df_ref_1['Horario Voo'].max()
    
            if horario_inicial_voo == horario_final_voo:
    
                titulo_voos = f'{horario_inicial_voo}'
    
            else:
    
                titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

            lista_nome_voos = df_ref_1['Voo'].unique().tolist()

            voos_unidos = ' + '.join(lista_nome_voos)
    
            for carro in df_ref_1['Carros'].unique().tolist():
    
                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)
    
                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))
    
                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())
    
                if modo=='REGULAR':
    
                    titulo_roteiro = f'Roteiro {item}'
    
                    titulo_carro = f'Veículo {carro}'
    
                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                else:
    
                    reserva = df_ref_2.at[0, 'Reserva']
    
                    titulo_roteiro = f'Roteiro {item}'
    
                    titulo_carro = f'Veículo {carro}'
    
                    titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                lista_apoios = df_ref_2['Apoios'].unique().tolist()
    
                if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                    df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                else:
    
                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:
    
                    container = st.container(border=True, height=500)
    
                    container.header(titulo_roteiro)
    
                    container.subheader(titulo_carro)
    
                    container.markdown(titulo_modo_voo_pax)
    
                    if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                        container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                    else:
    
                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                    if coluna==2:
    
                        coluna=0
    
                    else:
    
                        coluna+=1
    
                df_ref_apoio = df_apoios[(df_apoios['Roteiro']==item) & (df_apoios['Carros']==carro)].reset_index(drop=True)
    
                if len(df_ref_apoio)>0:
    
                    for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():
    
                        df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                        total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))
    
                        paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())
    
                        titulo_roteiro = f'Apoio | Roteiro {item}'
    
                        titulo_carro_principal = f'Veículo Principal {carro}'
    
                        titulo_carro = f'Veículo Apoio {carro_2}'
    
                        titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                        df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                        
                        with row3[coluna]:
    
                            container = st.container(border=True, height=500)
    
                            container.header(titulo_roteiro)
    
                            container.subheader(titulo_carro_principal)
    
                            container.subheader(titulo_carro)
    
                            container.markdown(titulo_modo_voo_pax)
    
                            container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                            if coluna==2:
    
                                coluna=0
    
                            else:
    
                                coluna+=1

        else:

            if item in  df_alternativos['Roteiro'].unique().tolist():
    
                df_ref_1 = df_alternativos[df_alternativos['Roteiro']==item].reset_index(drop=True)
    
                horario_inicial_voo = df_ref_1['Horario Voo'].min()
    
                horario_final_voo = df_ref_1['Horario Voo'].max()
    
                if horario_inicial_voo == horario_final_voo:
    
                    titulo_voos = f'{horario_inicial_voo}'
    
                else:
    
                    titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

                lista_nome_voos = df_ref_1['Voo'].unique().tolist()

                voos_unidos = ' + '.join(lista_nome_voos)
    
                for carro in df_ref_1['Carros'].unique().tolist():
    
                    df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)
    
                    modo = df_ref_2.at[0, 'Modo do Servico']

                    total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))
    
                    paxs_total = int(df_ref_2['Total ADT | CHD'].sum())
    
                    if modo=='REGULAR':
    
                        titulo_roteiro = f'Opção Alternativa | Roteiro {item}'
    
                        titulo_carro = f'Veículo {carro}'
    
                        titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                    else:
    
                        reserva = df_ref_2.at[0, 'Reserva']
    
                        titulo_roteiro = f'Opção Alternativa | Roteiro {item}'
    
                        titulo_carro = f'Veículo {carro}'
    
                        titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                    lista_apoios = df_ref_2['Apoios'].unique().tolist()
    
                    if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                        df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first', 'Apoios': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                        df_ref_3.loc[df_ref_3['Apoios']=='Y', 'Apoios']='X'

                    else:
    
                        df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                    df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                
                    with row3[coluna]:
    
                        container = st.container(border=True, height=500)
    
                        container.header(titulo_roteiro)
    
                        container.subheader(titulo_carro)
    
                        container.markdown(titulo_modo_voo_pax)
    
                        if 'X' in lista_apoios or 'Y' in lista_apoios:
    
                            container.dataframe(df_ref_3[['Apoios', 'Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                        else:
    
                            container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                        if coluna==2:
    
                            coluna=0
    
                        else:
    
                            coluna+=1
    
                    df_ref_apoio = df_apoios_alternativos[(df_apoios_alternativos['Roteiro']==item) & 
                                                                    (df_apoios_alternativos['Carros']==carro)].reset_index(drop=True)
    
                    if len(df_ref_apoio)>0:
    
                        for carro_2 in df_ref_apoio['Carros Apoios'].unique().tolist():
    
                            df_ref_apoio_2 = df_ref_apoio[df_ref_apoio['Carros Apoios']==carro_2].reset_index(drop=True)

                            total_hoteis = int(len(df_ref_apoio_2['Est Origem'].unique().tolist()))
    
                            paxs_total = int(df_ref_apoio_2['Total ADT | CHD'].sum())
    
                            titulo_roteiro = f'Apoio | Opção Alternativa | Roteiro {item}'
    
                            titulo_carro_principal = f'Veículo Principal {carro}'
    
                            titulo_carro = f'Veículo Apoio {carro_2}'
    
                            titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                            df_ref_apoio_3 = df_ref_apoio_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                                .sort_values(by='Data Horario Apresentacao').reset_index()
                            
                            df_ref_apoio_3 = df_ref_apoio_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                            
                            with row3[coluna]:
    
                                container = st.container(border=True, height=500)
    
                                container.header(titulo_roteiro)
    
                                container.subheader(titulo_carro_principal)
    
                                container.subheader(titulo_carro)
    
                                container.markdown(titulo_modo_voo_pax)
    
                                container.dataframe(df_ref_apoio_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                                if coluna==2:
    
                                    coluna=0
    
                                else:
    
                                    coluna+=1

    return coluna

def gerar_horarios_apresentacao_2(df_servicos):

    for index in range(len(df_servicos)):

        if index==0:

            df_servicos.at[index, 'Data Horario Apresentacao']=\
                definir_horario_primeiro_hotel(df_servicos, index)
            
            if not pd.isna(df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                paxs_hotel = df_servicos[df_servicos['Hoteis Juntos p/ Carro Principal']==df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                    ['Total ADT | CHD'].sum()
                
            else:

                paxs_hotel = df_servicos[df_servicos['Est Origem']==df_servicos.at[index, 'Est Origem']]['Total ADT | CHD'].sum()


        elif (df_servicos.at[index, 'Est Origem']==df_servicos.at[index-1, 'Est Origem']) | \
            (df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']==df_servicos.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

            df_servicos.at[index, 'Data Horario Apresentacao']=\
                df_servicos.at[index-1, 'Data Horario Apresentacao']

        else:

            bairro=df_servicos.at[index, 'Região']

            if not pd.isna(df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                paxs_hotel = df_servicos[df_servicos['Hoteis Juntos p/ Carro Principal']==df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                    ['Total ADT | CHD'].sum()
                
            else:

                paxs_hotel = df_servicos[df_servicos['Est Origem']==df_servicos.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

            if bairro!='':

                intervalo_ref = definir_intervalo_ref(df_servicos, index)
                
            if paxs_hotel>=st.session_state.pax_cinco_min:

                intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

            data_horario_hotel = df_servicos.at[index-1, 'Data Horario Apresentacao']-\
                intervalo_ref

            df_servicos.at[index, 'Data Horario Apresentacao']=data_horario_hotel

    return df_servicos

def roteirizar_natal_apenas_primeiros_hoteis(df_router_filtrado_2, sequencia_marsol):

    if len(df_router_filtrado_2)>0:

        df_roteiro_carro = df_router_filtrado_2[['Roteiro', 'Carros']].drop_duplicates().reset_index(drop=True)

        for index in range(len(df_roteiro_carro)):

            roteiro_ref = df_roteiro_carro.at[index, 'Roteiro']

            carro_ref = df_roteiro_carro.at[index, 'Carros']

            df_ref = df_router_filtrado_2[(df_router_filtrado_2['Roteiro']==roteiro_ref) & (df_router_filtrado_2['Carros']==carro_ref) & 
                                          (df_router_filtrado_2['Apoios']=='')].reset_index()

            n_max_hotel = df_ref['Sequência'].max()

            if n_max_hotel<=sequencia_marsol and len(df_ref)>1:

                df_ref_ordenado = df_ref.sort_values(by='Sequência').reset_index(drop=True)

                df_ref_ordenado = gerar_horarios_apresentacao_2(df_ref_ordenado)

                for index_2, value in df_ref_ordenado['index'].items():

                    df_router_filtrado_2.at[value, 'Data Horario Apresentacao']=df_ref_ordenado.at[index_2, 'Data Horario Apresentacao']

    return df_router_filtrado_2

def roteirizar_natal_maioria_praia_dos_artistas(df_router_filtrado_2):

    if len(df_router_filtrado_2)>0:

        df_roteiro_carro = df_router_filtrado_2[['Roteiro', 'Carros']].drop_duplicates().reset_index(drop=True)

        for index in range(len(df_roteiro_carro)):

            roteiro_ref = df_roteiro_carro.at[index, 'Roteiro']

            carro_ref = df_roteiro_carro.at[index, 'Carros']

            df_ref = df_router_filtrado_2[(df_router_filtrado_2['Roteiro']==roteiro_ref) & (df_router_filtrado_2['Carros']==carro_ref)].reset_index()

            paxs_praia_dos_artistas = df_ref[df_ref['Região']=='PRAIA DOS ARTISTAS']['Total ADT | CHD'].sum()

            paxs_total = df_ref['Total ADT | CHD'].sum()

            razao_ref = paxs_praia_dos_artistas / paxs_total

            if razao_ref>0.5 and len(df_ref['Est Origem'].unique().tolist())>1:

                df_ref = df_ref.drop(columns='Sequência')

                df_ref = pd.merge(df_ref, st.session_state.df_ln[['Est Origem', 'Sequência']], on='Est Origem', how='left')

                df_ref_ordenado = df_ref.sort_values(by='Sequência', ascending=False).reset_index(drop=True)

                df_ref_ordenado = gerar_horarios_apresentacao_2(df_ref_ordenado)

                for index_2, value in df_ref_ordenado['index'].items():

                    df_router_filtrado_2.at[value, 'Data Horario Apresentacao']=df_ref_ordenado.at[index_2, 'Data Horario Apresentacao']

    return df_router_filtrado_2

def roteirizar_pos_apoios(df_roteiros_apoios, df_router_filtrado_2):

    if len(df_roteiros_apoios)>0:

        df_roteiros_carros = df_roteiros_apoios[['Roteiro', 'Carros']].drop_duplicates().reset_index(drop=True)

        for index in range(len(df_roteiros_carros)):

            roteiro_ref = df_roteiros_carros.at[index, 'Roteiro']

            carro_ref = df_roteiros_carros.at[index, 'Carros']

            df_ref = df_router_filtrado_2[(df_router_filtrado_2['Roteiro']==roteiro_ref) & 
                                        (df_router_filtrado_2['Carros']==carro_ref) & 
                                        (df_router_filtrado_2['Apoios']=='')].reset_index()

            df_ref = gerar_horarios_apresentacao_2(df_ref)

            for index_2, value in df_ref['index'].items():

                df_router_filtrado_2.at[value, 'Data Horario Apresentacao']=df_ref.at[index_2, 'Data Horario Apresentacao']

    return df_router_filtrado_2

def verificar_cadeirante(observacao):
    palavra = "CADEIRANTE"
    observacao_upper = str(observacao).upper()

    # Contador de letras da palavra 'CADEIRANTE'
    contador_cadeirante = Counter(palavra)

    # Divide a observação em palavras
    palavras_observacao = observacao_upper.split()

    # Verifica cada palavra individualmente
    for palavra_observacao in palavras_observacao:
        contador_palavra = Counter(palavra_observacao)

        # Verifica se todas as letras de 'CADEIRANTE' estão presentes na palavra
        for letra, quantidade in contador_cadeirante.items():
            if contador_palavra[letra] < quantidade:
                break  # Se faltar uma letra, passa para a próxima palavra
        else:
            # Se a palavra passou pela verificação, retorna True
            return True

    # Se nenhuma palavra contém todas as letras de 'CADEIRANTE', retorna False
    return False

def inserir_coluna_horario_ultimo_hotel(df_router_filtrado_2):
    
    df_router_filtrado_2['Antecipação Último Hotel'] = pd.NaT

    lista_horarios_esp = st.session_state.df_horario_esp_ultimo_hotel['Junção/Voo/Reserva'].unique().tolist()

    for index in range(len(df_router_filtrado_2)):

        voo_ref = df_router_filtrado_2.at[index, 'Voo']

        juncao_ref = df_router_filtrado_2.at[index, 'Junção']

        reserva_ref = df_router_filtrado_2.at[index, 'Reserva']

        if voo_ref in lista_horarios_esp:
            intervalor_inicial_ref = st.session_state.df_horario_esp_ultimo_hotel.loc[
                st.session_state.df_horario_esp_ultimo_hotel['Junção/Voo/Reserva'] == voo_ref, 
                'Antecipação Último Hotel'
            ].iloc[0]

            # Converter para timedelta, assumindo que o valor é uma string no formato "HH:MM:SS"
            df_router_filtrado_2.at[index, 'Antecipação Último Hotel'] = intervalor_inicial_ref

        elif juncao_ref in lista_horarios_esp:
            intervalor_inicial_ref = st.session_state.df_horario_esp_ultimo_hotel.loc[
                st.session_state.df_horario_esp_ultimo_hotel['Junção/Voo/Reserva'] == juncao_ref, 
                'Antecipação Último Hotel'
            ].iloc[0]

            # Converter para timedelta corretamente
            df_router_filtrado_2.at[index, 'Antecipação Último Hotel'] = intervalor_inicial_ref

        elif reserva_ref in lista_horarios_esp:
            intervalor_inicial_ref = st.session_state.df_horario_esp_ultimo_hotel.loc[
                st.session_state.df_horario_esp_ultimo_hotel['Junção/Voo/Reserva'] == reserva_ref, 
                'Antecipação Último Hotel'
            ].iloc[0]

            # Converter para timedelta corretamente
            df_router_filtrado_2.at[index, 'Antecipação Último Hotel'] = intervalor_inicial_ref

    df_router_filtrado_2['Antecipação Último Hotel'] = df_router_filtrado_2['Antecipação Último Hotel'].dt.time

    return df_router_filtrado_2

def atualizar_banco_dados(df_exportacao, base_luck):

    st.session_state.df_insercao = st.session_state.df_insercao.drop(st.session_state.df_insercao.index)

    config = {
    'user': 'user_automation',
    'password': 'auto_luck_2024',
    'host': 'comeia.cixat7j68g0n.us-east-1.rds.amazonaws.com',
    'database': base_luck
    }
    # Conexão ao banco de dados
    conexao = mysql.connector.connect(**config)
    cursor = conexao.cursor()
    
    # Coluna para armazenar o status da atualização
    df_exportacao['Status Serviço'] = ''
    df_exportacao['Status Auditoria'] = ''
    
    # Placeholder para exibir o DataFrame e atualizar em tempo real
    placeholder = st.empty()
    for idx, row in df_exportacao.iterrows():
        id_reserva = row['Id_Reserva']
        id_servico = row['Id_Servico']
        currentPresentationHour = str(row['Data Horario Apresentacao Original'])
        newPresentationHour = str(row['Data Horario Apresentacao'])
        
        data = '{"presentation_hour":["' + currentPresentationHour + '","' + newPresentationHour + ' Roteirizador"]}'
        
        #Horário atual em string

        hora_execucao = datetime.now()
    
        hora_execucao_menos_3h = hora_execucao - timedelta(hours=3)

        current_timestamp = int(hora_execucao_menos_3h.timestamp())
        
        try:
            # Atualizar o banco de dados se o ID já existir
            query = "UPDATE reserve_service SET presentation_hour = %s WHERE id = %s"
            cursor.execute(query, (newPresentationHour, id_servico))
            conexao.commit()
            df_exportacao.at[idx, 'Status Serviço'] = 'Atualizado com sucesso'
            
        except Exception as e:
            df_exportacao.at[idx, 'Status Serviço'] = f'Erro: {e}'
        
        try:
            # Adicionar registro de edição na tabela de auditoria
            query = "INSERT INTO changelogs (relatedObjectType, relatedObjectId, parentId, data, createdAt, type, userId, module, hostname) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, null)"
            cursor.execute(query, ('ReserveService', id_servico, id_reserva, data, current_timestamp, 'update', st.query_params["userId"], 'router'))
            conexao.commit()
            df_exportacao.at[idx, 'Status Auditoria'] = 'Atualizado com sucesso'
        except Exception as e:
            df_exportacao.at[idx, 'Status Auditoria'] = f'Erro: {e}'
            
        # Define o estilo para coloração condicional
        styled_df = df_exportacao.style.applymap(
            lambda val: 'background-color: green; color: white' if val == 'Atualizado com sucesso' 
            else ('background-color: red; color: white' if val != '' else ''),
            subset=['Status Serviço', 'Status Auditoria']
        )
        
        # Atualiza o DataFrame na interface em tempo real
        placeholder.dataframe(styled_df, hide_index=True, use_container_width=True)
        # time.sleep(0.5)
    
    cursor.close()
    conexao.close()
    return df_exportacao

def getUser(userId):

    config = {
    'user': 'user_automation',
    'password': 'auto_luck_2024',
    'host': 'comeia.cixat7j68g0n.us-east-1.rds.amazonaws.com',
    'database': 'test_phoenix_general'
    }
    
    # Conexão às Views usando o config modificado
    conexao = mysql.connector.connect(**config)
    cursor = conexao.cursor()

    request_name = f'SELECT * FROM user WHERE ID = {userId}'

    # Script MySQL para requests
    cursor.execute(request_name)
    # Coloca o request em uma variavel
    resultado = cursor.fetchall()
    # Busca apenas os cabeçalhos do Banco
    cabecalho = [desc[0] for desc in cursor.description]

    # Fecha a conexão
    cursor.close()
    conexao.close()

    # Coloca em um dataframe e converte decimal para float
    df = pd.DataFrame(resultado, columns=cabecalho)
    df = df.applymap(lambda x: float(x) if isinstance(x, decimal.Decimal) else x)
    return df

def objetos_parametros(row1):

    with row1[0]:

        intervalo_inicial_natal = objeto_intervalo('Antecipação Último Hotel | Natal e Genipabu', time(3, 0), 'intervalo_inicial_natal')
        
        intervalo_inicial_pipa = objeto_intervalo('Antecipação Último Hotel | Pipa e Touros', time(4, 0), 'intervalo_inicial_pipa')
        
        intervalo_hoteis_bairros_iguais = objeto_intervalo('Intervalo Entre Hoteis de Mesmo Bairro', time(0, 5), 'intervalo_hoteis_bairros_iguais')

        intervalo_hoteis_bairros_diferentes = objeto_intervalo('Intervalo Entre Hoteis de Bairros Diferentes', time(0, 10), 'intervalo_hoteis_bairros_diferentes')

    with row1[1]:

        intervalo_inicial_sao_miguel = objeto_intervalo('Antecipação Último Hotel | São Miguel e Baia Formosa', time(4, 30), 'intervalo_inicial_sao_miguel')
        
        intervalo_inicial_galinhos = objeto_intervalo('Antecipação Último Hotel | Galinhos', time(5, 0), 'intervalo_inicial_galinhos')
        
        pax_max = st.number_input('Máximo de Paxs por Carro', step=1, value=50, key='pax_max')

        pax_cinco_min = st.number_input('Paxs Extras', step=1, value=15, key='pax_cinco_min', help='Número de paxs para aumentar intervalo entre hoteis em 5 minutos')
    
    with row1[2]:

        intervalo_inicial_camurupim = objeto_intervalo('Antecipação Último Hotel | Camurupim e Pirangi', time(3, 30), 'intervalo_inicial_camurupim')

        intervalo_pu_hotel = objeto_intervalo('Intervalo Hoteis | Primeiro vs Último', time(0, 40), 'intervalo_pu_hotel')

        max_hoteis = st.number_input('Máximo de Hoteis por Carro', step=1, value=8, key='max_hoteis')

def ajustar_data_execucao_voos_internacionais_madrugada():

    st.session_state.df_router['Horario Voo'] = pd.to_datetime(st.session_state.df_router['Horario Voo'], format='%H:%M:%S').dt.time

    mask_voos_inter_madrugada = (st.session_state.df_router['Tipo do Translado']=='Internacional') & (st.session_state.df_router['Horario Voo']<=time(0,59))

    st.session_state.df_router['Data Execucao'] = pd.to_datetime(st.session_state.df_router['Data Execucao'], format='%Y-%m-%d').dt.date

    st.session_state.df_router.loc[mask_voos_inter_madrugada, 'Data Execucao'] = st.session_state.df_router['Data Execucao'] - timedelta(days=1)

def verificar_voos_undefined():

    if len(st.session_state.df_router[st.session_state.df_router['Horario Voo']=='undefined']['Voo'].unique())>0:

        nome_voos_undefined = ', '.join(st.session_state.df_router[st.session_state.df_router['Horario Voo']=='undefined']['Voo'].unique())

        st.error(f'Os voos {nome_voos_undefined} foram cadastrados com horário vazio para alguma data específica. Por favor, entre nos cadastros deles, elimine essas agendas com horário vazio, comunique Thiago e tente novamente')

        st.stop()
        
def puxar_dados_phoenix():

    st.session_state.df_router = gerar_df_phoenix('vw_router', 'test_phoenix_natal')

    verificar_voos_undefined()

    dict_nomes_servicos = {'OUT Touros - hotéis Parceiros': 'OUT - Touros', 'OUT Natal - Hotéis Parceiros ': 'OUT - Natal', 
                            'OUT Pipa - Hotéis Parceiros': 'OUT - Pipa', 'Black - OUT Natal': 'OUT - Natal'}

    st.session_state.df_router['Servico'] = st.session_state.df_router['Servico'].replace(dict_nomes_servicos)

    st.session_state.df_router = st.session_state.df_router[(st.session_state.df_router['Servico']!='OUT - Tripulacao') & 
                                                            (st.session_state.df_router['Status da Reserva']!='RASCUNHO') & 
                                                            (st.session_state.df_router['Status da Reserva']!='CANCELADO') & 
                                                            (st.session_state.df_router['Status da Reserva']!='PENDENCIA DE IMPORTAÇÃO') & 
                                                            ~(pd.isna(st.session_state.df_router['Status da Reserva']))]\
        .reset_index(drop=True)
    
    st.session_state.df_router['Data Horario Apresentacao Original'] = st.session_state.df_router['Data Horario Apresentacao']

    ajustar_data_execucao_voos_internacionais_madrugada()

def verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos):

    lista_roteiros = df_router_filtrado_2['Roteiro'].unique().tolist()

    for roteiro_referencia in lista_roteiros:

        df_servicos_principal = df_router_filtrado_2[(df_router_filtrado_2['Roteiro']==roteiro_referencia)][['Id_Servico', 'Data Horario Apresentacao', 'Roteiro', 'Carros']].reset_index(drop=True)

        df_servicos_alternativo = df_roteiros_alternativos[(df_roteiros_alternativos['Roteiro']==roteiro_referencia)][['Id_Servico', 'Data Horario Apresentacao', 'Roteiro', 'Carros']].reset_index(drop=True)

        df_servicos_alternativo['Id_Servico'] = df_servicos_alternativo['Id_Servico'].astype('int64')

        df_servicos_alternativo['Roteiro'] = df_servicos_alternativo['Roteiro'].astype('int64')

        df_servicos_alternativo['Carros'] = df_servicos_alternativo['Carros'].astype('int64')

        df_servicos_principal['Id_Servico'] = df_servicos_principal['Id_Servico'].astype('int64')

        df_servicos_principal['Roteiro'] = df_servicos_principal['Roteiro'].astype('int64')

        df_servicos_principal['Carros'] = df_servicos_principal['Carros'].astype('int64')

        if df_servicos_principal.equals(df_servicos_alternativo):

            df_roteiros_alternativos = df_roteiros_alternativos[(df_roteiros_alternativos['Roteiro']!=roteiro_referencia)].reset_index(drop=True)

    return df_roteiros_alternativos

def gerar_roteiros_alternativos_5(df_servicos, pax_max_utilitario, pax_max_van, pax_max_micro, max_hoteis):

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())

    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        n_carro_ref = 0

        while len(df_ref)>0:

            df_ref_group_hotel = df_ref.groupby('Est Origem')['Total ADT | CHD'].sum().reset_index()

            if n_carro_ref==0:

                df_ref_group_carro = df_ref.groupby('Carros')['Total ADT | CHD'].sum().reset_index()

                carro_max = df_ref_group_carro['Total ADT | CHD'].max()

                if carro_max > pax_max_micro:

                    target = st.session_state.pax_max

                elif carro_max > pax_max_van:

                    target = pax_max_micro

                elif carro_max > pax_max_utilitario:

                    target = pax_max_van

            else:

                paxs_total_roteiro = df_ref_group_hotel['Total ADT | CHD'].sum()

                if paxs_total_roteiro > pax_max_micro:

                    target = st.session_state.pax_max

                elif paxs_total_roteiro > pax_max_van:

                    target = pax_max_micro

                elif paxs_total_roteiro > pax_max_utilitario:

                    target = pax_max_van

            n_carro_ref+=1

            df_agrupado_qtd_paxs = df_ref_group_hotel.groupby('Total ADT | CHD')['Est Origem'].count().reset_index()

            df_agrupado_qtd_paxs['Paxs Grupo Hotel'] = df_agrupado_qtd_paxs['Total ADT | CHD'] * df_agrupado_qtd_paxs['Est Origem']

            if len(df_agrupado_qtd_paxs)>=max_hoteis:

                lim_combinacoes = max_hoteis

            else:

                lim_combinacoes = len(df_agrupado_qtd_paxs)

            closest_sum = None
            closest_indices = []

            for r in range(1, lim_combinacoes+1):

                for comb in combinations(df_agrupado_qtd_paxs.index, r):

                    current_sum = df_agrupado_qtd_paxs.loc[list(comb), 'Paxs Grupo Hotel'].sum()

                    n_hoteis = df_agrupado_qtd_paxs.loc[list(comb), 'Est Origem'].sum()
                    
                    # Se for igual ao target, já encontramos a combinação perfeita
                    if current_sum == target and n_hoteis<=lim_combinacoes:
                        closest_sum = current_sum
                        closest_indices = list(comb)
                        encontrou_solucao = 1
                        break

                    else:

                        encontrou_solucao = 0

            if encontrou_solucao==1:
            
                ref_result_df = df_agrupado_qtd_paxs.loc[closest_indices]
            
                result_df = df_ref_group_hotel[df_ref_group_hotel['Total ADT | CHD'].isin(ref_result_df['Total ADT | CHD'].unique())]

            else:

                if len(df_ref_group_hotel)>=max_hoteis:

                    lim_combinacoes = max_hoteis

                else:

                    lim_combinacoes = len(df_ref_group_hotel)

                for r in range(lim_combinacoes, 0, -1):

                    for comb in combinations(df_ref_group_hotel.index, r):

                        current_sum = df_ref_group_hotel.loc[list(comb), 'Total ADT | CHD'].sum()
                        
                        # Se for igual ao target, já encontramos a combinação perfeita
                        if current_sum == target:
                            closest_sum = current_sum
                            closest_indices = list(comb)
                            break
                        
                        # Se estiver mais próximo do que a combinação anterior, atualizamos
                        if closest_sum is None or abs(target - current_sum) < abs(target - closest_sum):
                            closest_sum = current_sum
                            closest_indices = list(comb)
                    
                    # Parar o loop se a combinação exata foi encontrada
                    if closest_sum == target:
                        break

                result_df = df_ref_group_hotel.loc[closest_indices]

            lista_hoteis_melhor_comb = result_df['Est Origem'].tolist()

            df_rota_alternativa = df_ref[df_ref['Est Origem'].isin(lista_hoteis_melhor_comb)].sort_values(by='Sequência', ascending=False).reset_index(drop=True)

            df_rota_alternativa['Carros'] = n_carro_ref

            df_rota_alternativa = gerar_horarios_apresentacao_2(df_rota_alternativa)

            df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_rota_alternativa], ignore_index=True)

            df_ref = df_ref[~df_ref['Est Origem'].isin(lista_hoteis_melhor_comb)].reset_index(drop=True)

    return df_roteiros_alternativos

def recalcular_horarios_menor_horario(df_router_filtrado_2):

    df_roteiros_carros = df_router_filtrado_2[['Roteiro', 'Carros', 'Junção']].drop_duplicates().reset_index(drop=True)

    df_roteiros_carros = df_roteiros_carros[~pd.isna(df_roteiros_carros['Junção'])].reset_index(drop=True)

    for index in range(len(df_roteiros_carros)):

        roteiro_referencia = df_roteiros_carros.at[index, 'Roteiro']

        carro_referencia = df_roteiros_carros.at[index, 'Carros']

        df_ref = df_router_filtrado_2[(df_router_filtrado_2['Roteiro']==roteiro_referencia) & (df_router_filtrado_2['Carros']==carro_referencia)].reset_index()

        horario_voo_mais_cedo = df_ref['Horario Voo'].min()

        horario_menor_horario = df_ref['Menor Horário'].min()

        if horario_voo_mais_cedo!=horario_menor_horario:

            df_ref['Menor Horário'] = horario_voo_mais_cedo

            df_ref = gerar_horarios_apresentacao_2(df_ref)

            for index_2, index_principal in df_ref['index'].items():

                df_router_filtrado_2.at[index_principal, 'Data Horario Apresentacao'] = df_ref.at[index_2, 'Data Horario Apresentacao']

    return df_router_filtrado_2

def verificar_preenchimento_df_hoteis(df_hoteis_ref):

    hoteis_sem_regiao = df_hoteis_ref[df_hoteis_ref['Região']=='']['Est Origem'].unique().tolist()

    hoteis_sem_sequencia = df_hoteis_ref[pd.isna(df_hoteis_ref['Sequência'])]['Est Origem'].unique().tolist()

    hoteis_sem_acessibilidade = df_hoteis_ref[df_hoteis_ref[['Bus', 'Micro', 'Van', 'Utilitario']].isna().all(axis=1)]['Est Origem'].unique().tolist()

    hoteis_unificados = list(set(hoteis_sem_regiao + hoteis_sem_sequencia + hoteis_sem_acessibilidade))

    if len(hoteis_unificados)>0:

        nome_hoteis = ', '.join(hoteis_unificados)

        st.error(f'Os hoteis {nome_hoteis} estão com cadastro errado. Pode estar faltando o número da sequência, o nome da região ou o preenchimento da acessibilidade. Verifique, ajuste e tente novamente.')

        st.stop()

def puxar_historico(id_gsheet, lista_abas, lista_nomes_df_hoteis):

    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(id_gsheet)

    for index in range(len(lista_abas)):

        aba = lista_abas[index]

        df_hotel = lista_nomes_df_hoteis[index]
        
        sheet = spreadsheet.worksheet(aba)

        sheet_data = sheet.get_all_values()

        st.session_state[df_hotel] = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

def inserir_df_rotas_geradas(aba_excel, df_insercao):
    
    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)
    
    # Abertura da planilha e aba
    spreadsheet = client.open_by_key('1ch1NfOKeK008ZeqexQTzOqXuCZ2Q6sL8hY2sPqQegLQ')
    sheet = spreadsheet.worksheet(aba_excel)
    
    # Limpeza do intervalo A2:Z10000
    sheet.batch_clear(["A2:AR10000"])
    
    def format_value(value):
        if isinstance(value, pd.Timestamp):  # Para colunas datetime no DataFrame
            return value.strftime('%Y-%m-%d %H:%M:%S')
        elif type(value) is datetime:  # Para objetos do tipo datetime
            return value.strftime('%Y-%m-%d')
        elif isinstance(value, float):  # Formatação opcional para floats
            return f"{value:.2f}"
        else:
            return str(value)  # Para outros tipos
    
    # Aplicando formatação aos valores do DataFrame
    data = df_insercao.applymap(format_value).values.tolist()
    start_cell = "A2"  # Sempre insere a partir da segunda linha
    sheet.update(start_cell, data)

def salvar_rotas_historico(df_pdf):

    puxar_historico('1ch1NfOKeK008ZeqexQTzOqXuCZ2Q6sL8hY2sPqQegLQ', ['Histórico Roteiros'], ['df_historico_roteiros'])

    st.session_state.df_historico_roteiros['Data Execucao'] = pd.to_datetime(st.session_state.df_historico_roteiros['Data Execucao']).dt.date

    st.session_state.df_historico_roteiros = st.session_state.df_historico_roteiros[~((st.session_state.df_historico_roteiros['Servico']==st.session_state.servico_roteiro) & 
                                                                                      (st.session_state.df_historico_roteiros['Data Execucao']==st.session_state.data_roteiro))].reset_index(drop=True)
    
    st.session_state.df_historico_roteiros = pd.concat([st.session_state.df_historico_roteiros, df_pdf], ignore_index=True)

    inserir_df_rotas_geradas('Histórico Roteiros', st.session_state.df_historico_roteiros)

def plotar_divisao_de_rotas(coluna, row3):

    if coluna==0:

        with row3[0]:

            container_ref = st.container(border=True, height=500)

        with row3[1]:

            container_ref = st.container(border=True, height=500)

        with row3[2]:

            container_ref = st.container(border=True, height=500)

    elif coluna==1:

        with row3[1]:

            container_ref = st.container(border=True, height=500)

        with row3[2]:

            container_ref = st.container(border=True, height=500)

        with row3[0]:

            container_ref = st.container(border=True, height=500)

        with row3[1]:

            container_ref = st.container(border=True, height=500)

        with row3[2]:

            container_ref = st.container(border=True, height=500)

    elif coluna==2:

        with row3[2]:

            container_ref = st.container(border=True, height=500)

        with row3[0]:

            container_ref = st.container(border=True, height=500)

        with row3[1]:

            container_ref = st.container(border=True, height=500)

        with row3[2]:

            container_ref = st.container(border=True, height=500)

    coluna=0

    return coluna

st.set_page_config(layout='wide')

st.title('Roteirizador de Transfer Out - Natal')

st.divider()

st.header('Parâmetros')

row1 = st.columns(3)

if not st.query_params or not st.query_params["userId"]:

    st.error("Usuário não autenticado")

    st.stop()

if not 'df_user' in st.session_state:
    
    st.session_state.df_user = getUser(st.query_params["userId"])

if not 'df_router' in st.session_state:

    with st.spinner('Puxando dados do Phoenix...'):

        puxar_dados_phoenix()

if 'df_juncao_voos' not in st.session_state:

    st.session_state.df_juncao_voos = pd.DataFrame(columns=['Servico', 'Voo', 'Horário', 'Tipo do Translado', 'Junção'])

if 'df_horario_esp_ultimo_hotel' not in st.session_state:

    st.session_state.df_horario_esp_ultimo_hotel = pd.DataFrame(columns=['Junção/Voo/Reserva', 'Antecipação Último Hotel'])

objetos_parametros(row1)

st.divider()

st.header('Juntar Voos')

st.markdown('*os voos internacionais entre 00:00 e 00:59, na verdade serão executados em D+1, porém, pela antecedência de 1h a mais, eles aparecem no dia selecionado*')

row2 = st.columns(3)

row21 = st.columns(2)

# Botões Atualizar Hoteis, Atualizar Dados Phoenix, campos de Data e botões de roteirizar e visualizar voos

with row2[0]:

    atualizar_phoenix = st.button('Atualizar Dados Phoenix')

    if atualizar_phoenix:

        with st.spinner('Puxando dados do Phoenix...'):

            puxar_dados_phoenix()

        if 'df_servico_voos_horarios' in st.session_state:
            
            st.session_state['df_servico_voos_horarios'] = pd.DataFrame(columns=['Servico', 'Voo', 'Horario Voo'])

    # Campo de data

    container_roteirizar = st.container(border=True)

    data_roteiro = container_roteirizar.date_input('Data do Roteiro', value=None, format='DD/MM/YYYY', key='data_roteiro')

    df_router_data_roteiro = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                        (st.session_state.df_router['Tipo de Servico']=='OUT') & 
                                                        (st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                        (st.session_state.df_router['Status da Reserva']!='CANCELADO')]\
                                                            .reset_index(drop=True)

    lista_servicos = df_router_data_roteiro['Servico'].unique().tolist()

    lista_voos_data_roteiro = df_router_data_roteiro['Voo'].unique().tolist()

    servico_roteiro = container_roteirizar.selectbox('Serviço', lista_servicos, index=None, placeholder='Escolha um Serviço', 
                                                     key='servico_roteiro')  

    row_container = container_roteirizar.columns(2)

    # Botão roteirizar

    with row_container[0]:

        roteirizar = st.button('Roteirizar')

# Gerar dataframe com os voos da data selecionada e imprimir na tela o dataframe

if servico_roteiro:

    if servico_roteiro!='OUT - Natal':

        df_router_filtrado = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                        (st.session_state.df_router['Tipo de Servico']=='OUT') & 
                                                        (st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                        (st.session_state.df_router['Servico']==servico_roteiro)]\
                                                            .reset_index(drop=True)
        
    else:

        df_router_filtrado = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                        (st.session_state.df_router['Tipo de Servico']=='OUT') & 
                                                        (st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                        ((st.session_state.df_router['Servico']==servico_roteiro) | 
                                                         (st.session_state.df_router['Servico']=='OUT - Camurupim'))]\
                                                            .reset_index(drop=True)
    
    st.session_state.df_servico_voos_horarios = df_router_filtrado[['Servico', 'Voo', 'Horario Voo', 'Tipo do Translado']]\
    .sort_values(by=['Horario Voo']).drop_duplicates().reset_index(drop=True)

    df_router_filtrado = df_router_filtrado[~df_router_filtrado['Observacao'].str.upper().str.contains('CLD', na=False)]

    st.session_state.df_servico_voos_horarios['Paxs Regular']=0

    for index in range(len(st.session_state.df_servico_voos_horarios)):

        servico = st.session_state.df_servico_voos_horarios.at[index, 'Servico']

        voo = st.session_state.df_servico_voos_horarios.at[index, 'Voo']

        h_voo = st.session_state.df_servico_voos_horarios.at[index, 'Horario Voo']

        total_paxs_ref = \
            df_router_filtrado[(df_router_filtrado['Servico']==servico) & (df_router_filtrado['Voo']==voo) & 
                               (df_router_filtrado['Horario Voo']==h_voo) & (df_router_filtrado['Modo do Servico']=='REGULAR')]\
                                ['Total ADT'].sum() + \
                                    df_router_filtrado[(df_router_filtrado['Servico']==servico) & 
                                                       (df_router_filtrado['Voo']==voo) & 
                                                       (df_router_filtrado['Horario Voo']==h_voo) & 
                                                       (df_router_filtrado['Modo do Servico']=='REGULAR')]['Total CHD'].sum()
        
        st.session_state.df_servico_voos_horarios.at[index, 'Paxs Regular'] = total_paxs_ref

    st.session_state.df_servico_voos_horarios['Horario Voo'] = pd.to_datetime(st.session_state.df_servico_voos_horarios['Horario Voo'], 
                                                                          format='%H:%M:%S')

    for index in range(len(st.session_state.df_servico_voos_horarios)):

        tipo_translado = st.session_state.df_servico_voos_horarios.at[index, 'Tipo do Translado']

        if tipo_translado=='Internacional':

            st.session_state.df_servico_voos_horarios.at[index, 'Horario Voo Ajustado'] = \
                st.session_state.df_servico_voos_horarios.at[index, 'Horario Voo'] - transformar_timedelta(time(1,0))
            
        else:

            st.session_state.df_servico_voos_horarios.at[index, 'Horario Voo Ajustado'] = \
                st.session_state.df_servico_voos_horarios.at[index, 'Horario Voo']
            
    st.session_state.df_servico_voos_horarios['Horario Voo'] = pd.to_datetime(st.session_state.df_servico_voos_horarios['Horario Voo'], 
                                                                              format='%H:%M:%S').dt.time
    
    st.session_state.df_servico_voos_horarios['Horario Voo Ajustado'] = pd.to_datetime(st.session_state.df_servico_voos_horarios['Horario Voo Ajustado'], 
                                                                              format='%H:%M:%S').dt.time
    
    st.session_state.df_servico_voos_horarios = st.session_state.df_servico_voos_horarios.sort_values(by='Horario Voo Ajustado').reset_index(drop=True)

# Botão pra limpar todos os dataframes

with row2[1]:

    container_botao = st.container()

    limpar_tudo = container_botao.button('Limpar Tudo', use_container_width=True)

if limpar_tudo:

    st.session_state.df_juncao_voos = st.session_state.df_juncao_voos.iloc[0:0]

    st.session_state.df_servico_voos_horarios = st.session_state.df_servico_voos_horarios.iloc[0:0]

    st.session_state.df_horario_esp_ultimo_hotel = st.session_state.df_horario_esp_ultimo_hotel.iloc[0:0]

    st.session_state.df_router_filtrado_2 = st.session_state.df_router_filtrado_2.iloc[0:0]

# Plotar voos do serviço/dia na tela

if servico_roteiro and 'df_servico_voos_horarios' in st.session_state:

    with row2[0]:

        st.dataframe(st.session_state.df_servico_voos_horarios, hide_index=True) 

# Formulário de Junção de Voos

with row2[1]:

    with st.form('juntar_voos_form_novo'):

        # Captando intervalo entre voos

        horario_inicial = st.time_input('Horário Inicial Voo (Ajustado)', value=None, key='horario_inicial', step=300)

        horario_final = st.time_input('Horário Final Voo (Ajustado)', value=None, key='horario_final', step=300) 

        lancar_juncao = st.form_submit_button('Lançar Junção')

        # Lançando junção

        if lancar_juncao and horario_inicial and horario_final:

            # Filtrando dataframe por Horario Voo e Servico

            if horario_inicial and horario_final and servico_roteiro:

                if servico_roteiro!='OUT - Natal':

                    df_voos_hi_hf = st.session_state.df_servico_voos_horarios\
                        [(st.session_state.df_servico_voos_horarios['Horario Voo Ajustado']>=horario_inicial) & 
                        (st.session_state.df_servico_voos_horarios['Horario Voo Ajustado']<=horario_final) & 
                        (st.session_state.df_servico_voos_horarios['Servico']==servico_roteiro)]\
                            [['Servico', 'Voo', 'Horario Voo', 'Tipo do Translado', 'Paxs Regular']].reset_index(drop=True)
                    
                else:

                    df_voos_hi_hf = st.session_state.df_servico_voos_horarios\
                        [(st.session_state.df_servico_voos_horarios['Horario Voo Ajustado']>=horario_inicial) & 
                        (st.session_state.df_servico_voos_horarios['Horario Voo Ajustado']<=horario_final) & 
                        ((st.session_state.df_servico_voos_horarios['Servico']==servico_roteiro) | 
                        (st.session_state.df_servico_voos_horarios['Servico']=='OUT - Camurupim'))]\
                            [['Servico', 'Voo', 'Horario Voo', 'Tipo do Translado', 'Paxs Regular']].reset_index(drop=True)
                
                df_voos_hi_hf = df_voos_hi_hf.rename(columns={'Horario Voo': 'Horário'})

                df_voos_hi_hf = df_voos_hi_hf[df_voos_hi_hf['Paxs Regular']!=0].reset_index(drop=True)

                df_voos_hi_hf = df_voos_hi_hf[['Servico', 'Voo', 'Horário', 'Tipo do Translado']]
            
                if len(st.session_state.df_juncao_voos)>0:

                    juncao_max = st.session_state.df_juncao_voos['Junção'].max()

                    df_voos_hi_hf['Junção'] = juncao_max+1

                else:

                    df_voos_hi_hf['Junção'] = 1  

            st.session_state.df_juncao_voos = pd.concat([st.session_state.df_juncao_voos, df_voos_hi_hf], ignore_index=True)

# Voos não operantes e multiselect p/ horários específicos de último hotel em junções ou voos

with row2[1]:

    voos_nao_operantes = st.multiselect('Voos s/ Operar', sorted(lista_voos_data_roteiro))

    horario_ultimo_hotel_especifico = st.multiselect('Usar antecipação específica de último hotel p/ voo, junção ou reserva privativa?', ['Sim'])

# Plotando formulário para lançamento de horários específicos de último hotel em junções ou voos

if len(horario_ultimo_hotel_especifico)>0:

    with row2[1]:

        with st.form('horario_ph_especifico'):

            if servico_roteiro!='OUT - Natal':

                df_router_filtrado = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                                (st.session_state.df_router['Tipo de Servico']=='OUT') & 
                                                                (st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                                (st.session_state.df_router['Servico']==servico_roteiro)]\
                                                                    .reset_index(drop=True)
                
            else:

                df_router_filtrado = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                                (st.session_state.df_router['Tipo de Servico']=='OUT') & 
                                                                (st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                                ((st.session_state.df_router['Servico']==servico_roteiro) | 
                                                                (st.session_state.df_router['Servico']=='OUT - Camurupim'))]\
                                                                    .reset_index(drop=True)
                
            df_router_filtrado = df_router_filtrado[~df_router_filtrado['Observacao'].str.upper().str.contains('CLD', na=False)]

            lista_juncoes = st.session_state.df_juncao_voos['Junção'].unique().tolist()

            lista_voos_com_juncao = st.session_state.df_juncao_voos['Voo'].unique().tolist()

            lista_voos_sem_juncao = [item for item in st.session_state.df_servico_voos_horarios['Voo'].unique().tolist() if not item in lista_voos_com_juncao]

            lista_juncoes.extend(lista_voos_sem_juncao)

            lista_reservas_pvt = df_router_filtrado[df_router_filtrado['Modo do Servico']!='REGULAR']['Reserva'].unique().tolist()

            lista_juncoes.extend(lista_reservas_pvt)

            juncao_ou_voo = st.selectbox('Escolha a Junção/Voo/Reserva Privativa', lista_juncoes, index=None)

            intervalo_inicial_especifico = objeto_intervalo('Antecipação Último Hotel', time(3, 0), 'intervalo_inicial_especifico')

            intervalo_inicial_especifico_str = str(intervalo_inicial_especifico)

            if len(intervalo_inicial_especifico_str)==7:

                intervalo_inicial_especifico_str = f'0{intervalo_inicial_especifico_str}'

            lancar_h_esp = st.form_submit_button('Lançar Antecipação Específica')

            if lancar_h_esp:

                lista_dados = [juncao_ou_voo, intervalo_inicial_especifico_str]

                st.session_state.df_horario_esp_ultimo_hotel.loc[len(st.session_state.df_horario_esp_ultimo_hotel)]=lista_dados

# Botões pra limpar junções

with row2[2]:

    row2_1 = st.columns(2)

    # Limpar todas as junções

    with row2_1[0]:

        limpar_juncoes = st.button('Limpar Todas as Junções')

    # Limpar junções específicas

    with row2_1[1]:

        limpar_juncao_esp = st.button('Limpar Junção Específica')

        juncao_limpar = st.number_input('Junção', step=1, value=None, key='juncao_limpar')

    # Se for pra limpar todas as junções

    if limpar_juncoes:

        voo=None

        st.session_state.df_juncao_voos = pd.DataFrame(columns=['Servico', 'Voo', 'Horário', 'Tipo do Translado', 'Junção'])

    # Se for limpar junções específicas

    if limpar_juncao_esp and juncao_limpar==1: # se a exclusão for da junção 1

        st.session_state.df_juncao_voos = st.session_state.df_juncao_voos[st.session_state.df_juncao_voos['Junção']!=juncao_limpar]\
        .reset_index(drop=True)

        for index, value in st.session_state.df_juncao_voos['Junção'].items():

            st.session_state.df_juncao_voos.at[index, 'Junção']-=1

    elif limpar_juncao_esp and juncao_limpar: # se a exclusão não for da junção 1

        st.session_state.df_juncao_voos = st.session_state.df_juncao_voos[st.session_state.df_juncao_voos['Junção']!=juncao_limpar].reset_index(drop=True)

        juncao_ref=1

        for juncao in st.session_state.df_juncao_voos['Junção'].unique().tolist():

            if juncao>1:

                juncao_ref+=1

                st.session_state.df_juncao_voos.loc[st.session_state.df_juncao_voos['Junção']==juncao, 'Junção']=juncao_ref   

    container_df_juncao_voos = st.container()     

    container_df_juncao_voos.dataframe(st.session_state.df_juncao_voos, hide_index=True, use_container_width=True)

# Plotar botão de limpar lançamentos de horários específicos p/ junções/voos e plotar dataframe com os lançamentos

if servico_roteiro and 'df_horario_esp_ultimo_hotel' in st.session_state:

    with row2[2]:

        limpar_lancamentos = st.button('Limpar Lançamentos')

        if limpar_lancamentos:

            st.session_state.df_horario_esp_ultimo_hotel = pd.DataFrame(columns=['Junção/Voo/Reserva', 'Antecipação Último Hotel'])

        st.dataframe(st.session_state.df_horario_esp_ultimo_hotel, hide_index=True)

# Roteirizando Regiões

if roteirizar:

    with st.spinner('Puxando sequências de hoteis...'):

        puxar_sequencias_hoteis('1ch1NfOKeK008ZeqexQTzOqXuCZ2Q6sL8hY2sPqQegLQ', 
                                ['Hoteis Natal', 'Hoteis Pipa', 'Hoteis Touros', 'Hoteis Sao Miguel', 'Hoteis Galinhos', 'Hoteis Camurupim', 'Hoteis Genipabu', 
                                'Hoteis Pirangi', 'Hoteis Baia Formosa', 'Hoteis Passeio Litoral Norte'], 
                                ['df_natal', 'df_pipa', 'df_touros', 'df_sao_miguel', 'df_galinhos', 'df_camurupim', 'df_genipabu', 'df_pirangi', 'df_baia_formosa', 'df_ln'])
        
    with st.spinner('Gerando roteiros...'):

        st.session_state.dict_regioes_hoteis = \
            {'OUT - Natal': ['df_natal', 'Natal', 'Hoteis Natal', 'Natal'], 
            'OUT - Pipa': ['df_pipa', 'Pipa', 'Hoteis Pipa', 'Pipa'], 
            'OUT - Touros': ['df_touros', 'Touros', 'Hoteis Touros', 'Touros'], 
            'OUT - São Miguel Gostoso': ['df_sao_miguel', 'Sao Miguel', 'Hoteis Sao Miguel', 'São Miguel'], 
            'Out - Galinhos': ['df_galinhos', 'Galinhos', 'Hoteis Galinhos', 'Galinhos'], 
            'OUT - Camurupim': ['df_camurupim', 'Camurupim', 'Hoteis Camurupim', 'Camurupim'], 
            'Out - Genipabu': ['df_genipabu', 'Genipabu', 'Hoteis Genipabu', 'Genipabu'], 
            'OUT - Pirangi': ['df_pirangi', 'Pirangi', 'Hoteis Pirangi', 'Pirangi'], 
            'OUT - Baia Formosa': ['df_baia_formosa', 'Baia Formosa', 'Hoteis Baia Formosa', 'Baia Formosa']}

        nome_df_hotel = st.session_state.dict_regioes_hoteis[servico_roteiro][0]

        nome_html_ref = st.session_state.dict_regioes_hoteis[servico_roteiro][1]

        nome_aba_excel = st.session_state.dict_regioes_hoteis[servico_roteiro][2]

        nome_regiao = st.session_state.dict_regioes_hoteis[servico_roteiro][3]

        df_hoteis_ref = st.session_state[nome_df_hotel]

        verificar_preenchimento_df_hoteis(df_hoteis_ref)

        # Filtrando apenas data especificada, OUTs e Status do Serviço diferente de 'CANCELADO' e retirando os hoteis de piedade pra fazer o roteiro em separado

        if servico_roteiro!='OUT - Natal':

            df_router_filtrado = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                            (st.session_state.df_router['Tipo de Servico']=='OUT') &  
                                                            (st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                            (st.session_state.df_router['Servico']==servico_roteiro) & 
                                                            ~(st.session_state.df_router['Voo'].isin(voos_nao_operantes))].reset_index(drop=True)
            
        else:

            df_router_filtrado = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                            (st.session_state.df_router['Tipo de Servico']=='OUT') &  
                                                            (st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                            ((st.session_state.df_router['Servico']==servico_roteiro) | 
                                                            (st.session_state.df_router['Servico']=='OUT - Camurupim')) & 
                                                            ~(st.session_state.df_router['Voo'].isin(voos_nao_operantes))].reset_index(drop=True)
            
            df_router_filtrado['Servico']='OUT - Natal'
            
            sequencia_marsol = df_hoteis_ref.loc[df_hoteis_ref['Est Origem'] == 'Marsol Beach Resort', 'Sequência'].values[0]

        # Categorizando serviços com 'CADEIRANTE' na observação
        
        df_router_filtrado['Modo do Servico'] = df_router_filtrado.apply(
            lambda row: 'CADEIRANTE' if verificar_cadeirante(row['Observacao']) else row['Modo do Servico'], axis=1)
        
        # Excluindo linhas onde exite 'CLD' na observação

        df_router_filtrado = df_router_filtrado[~df_router_filtrado['Observacao'].str.upper().str.contains('CLD', na=False)]

        if len(df_router_filtrado)==0:
        
            st.error('Depois de filtrar as reservas com CLD na observação não sobraram serviços para roteirizar.')

            st.stop()
        
        # Verificando se todos os hoteis estão na lista da sequência
    
        itens_faltantes, lista_hoteis_df_router = gerar_itens_faltantes(df_router_filtrado, df_hoteis_ref)

        itens_faltantes_passeios, lista_hoteis_df_router_passeios = gerar_itens_faltantes(df_router_filtrado, st.session_state.df_ln)

        pax_max_utilitario = 4

        pax_max_van = 18

        pax_max_micro = 25

        if (servico_roteiro=='OUT - Natal' and len(itens_faltantes)==0 and len(itens_faltantes_passeios)==0) or (servico_roteiro!='OUT - Natal' and len(itens_faltantes)==0):

            # Mensagens de andamento do script informando como foi a verificação dos hoteis cadastrados

            st.success('Todos os hoteis estão cadastrados na lista de sequência de hoteis')

            df_router_filtrado_2 = criar_df_servicos_2(df_router_filtrado, st.session_state.df_juncao_voos, df_hoteis_ref)

            # Inserir coluna com horários específicos de junções/voos

            df_router_filtrado_2 = inserir_coluna_horario_ultimo_hotel(df_router_filtrado_2)

            roteiro = 0

            df_router_filtrado_2['Horario Voo'] = pd.to_datetime(df_router_filtrado_2['Horario Voo'], format='%H:%M:%S').dt.time

            # Criando dataframe que vai receber os hoteis que tem mais paxs que a capacidade máxima da frota

            lista_colunas = ['index']

            df_hoteis_pax_max = pd.DataFrame(columns=lista_colunas.extend(df_router_filtrado_2.columns.tolist()))

            # Roteirizando hoteis que podem receber ônibus com mais paxs que a capacidade máxima da frota

            df_router_filtrado_2, df_hoteis_pax_max, roteiro = \
                roteirizar_hoteis_mais_pax_max(df_router_filtrado_2, roteiro, df_hoteis_pax_max)

            # Gerando horários de apresentação

            df_router_filtrado_2, roteiro = gerar_horarios_apresentacao(df_router_filtrado_2, roteiro, st.session_state.max_hoteis)

        else:

            inserir_hoteis_faltantes(itens_faltantes, df_hoteis_ref, nome_aba_excel, nome_regiao)

            if servico_roteiro=='OUT - Natal' and len(itens_faltantes_passeios)!=0:

                inserir_hoteis_faltantes(itens_faltantes_passeios, st.session_state.df_ln, 'Hoteis Passeio Litoral Norte', 'Passeios Litoral Norte')

            st.stop()

        df_router_filtrado_2 = recalcular_horarios_menor_horario(df_router_filtrado_2)

        df_router_filtrado_2 = roteirizar_natal_maioria_praia_dos_artistas(df_router_filtrado_2)

        # Identificando serviços das rotas primárias que vão precisar de apoios

        df_router_filtrado_2 = identificar_apoios_em_df(df_router_filtrado_2, pax_max_utilitario, pax_max_van, pax_max_micro)

        # Gerando rotas de apoios de rotas primárias

        df_router_filtrado_2, df_roteiros_apoios = gerar_roteiros_apoio(df_router_filtrado_2)

        # Roteirizando carro principal desconsiderando os hoteis do apoio

        df_router_filtrado_2 = roteirizar_pos_apoios(df_roteiros_apoios, df_router_filtrado_2)

        # Gerando roteiros alternativos

        df_roteiros_alternativos = gerar_roteiros_alternativos(df_router_filtrado_2)

        df_roteiros_alternativos = recalcular_horarios_menor_horario(df_roteiros_alternativos)

        df_roteiros_alternativos = roteirizar_natal_maioria_praia_dos_artistas(df_roteiros_alternativos)

        # Gerando roteiros alternativos 2

        max_hoteis_2 = 10

        max_hoteis_4 = 16

        intervalo_pu_hotel_2 = pd.Timedelta(hours=1)

        df_roteiros_alternativos_2 = gerar_roteiros_alternativos_2(df_router_filtrado_2, max_hoteis_2, intervalo_pu_hotel_2)

        df_roteiros_alternativos_2 = recalcular_horarios_menor_horario(df_roteiros_alternativos_2)

        df_roteiros_alternativos_2 = roteirizar_natal_maioria_praia_dos_artistas(df_roteiros_alternativos_2)

        df_roteiros_alternativos_3 = gerar_roteiros_alternativos_3(df_router_filtrado_2)

        df_roteiros_alternativos_3 = recalcular_horarios_menor_horario(df_roteiros_alternativos_3)

        df_roteiros_alternativos_3 = roteirizar_natal_maioria_praia_dos_artistas(df_roteiros_alternativos_3)

        df_roteiros_alternativos_4 = gerar_roteiros_alternativos_4(df_router_filtrado_2, max_hoteis_4)

        df_roteiros_alternativos_4 = recalcular_horarios_menor_horario(df_roteiros_alternativos_4)

        df_roteiros_alternativos_4 = roteirizar_natal_maioria_praia_dos_artistas(df_roteiros_alternativos_4)

        df_roteiros_alternativos_5 = gerar_roteiros_alternativos_5(df_router_filtrado_2, pax_max_utilitario, pax_max_van, pax_max_micro, max_hoteis_2)

        df_roteiros_alternativos_5 = recalcular_horarios_menor_horario(df_roteiros_alternativos_5)

        df_roteiros_alternativos_5 = roteirizar_natal_maioria_praia_dos_artistas(df_roteiros_alternativos_5)
        
        # Identificando serviços das rotas alternativas que vão precisar de apoios

        df_roteiros_alternativos = identificar_apoios_em_df(df_roteiros_alternativos, pax_max_utilitario, pax_max_van, pax_max_micro)

        # Gerando rotas de apoios de rotas alternativas

        df_roteiros_alternativos, df_roteiros_apoios_alternativos = gerar_roteiros_apoio(df_roteiros_alternativos)

        # Roteirizando carro principal desconsiderando os hoteis do apoio

        df_roteiros_alternativos = roteirizar_pos_apoios(df_roteiros_apoios_alternativos, df_roteiros_alternativos)

        # Identificando serviços das rotas alternativas 2 que vão precisar de apoios

        df_roteiros_alternativos_2 = identificar_apoios_em_df(df_roteiros_alternativos_2, pax_max_utilitario, pax_max_van, pax_max_micro)

        # Gerando rotas de apoios de rotas alternativas 2

        df_roteiros_alternativos_2, df_roteiros_apoios_alternativos_2 = gerar_roteiros_apoio(df_roteiros_alternativos_2)

        # Roteirizando carro principal desconsiderando os hoteis do apoio

        df_roteiros_alternativos_2 = roteirizar_pos_apoios(df_roteiros_apoios_alternativos_2, df_roteiros_alternativos_2)

        # Identificando serviços das rotas alternativas 3 que vão precisar de apoios

        df_roteiros_alternativos_3 = identificar_apoios_em_df(df_roteiros_alternativos_3, pax_max_utilitario, pax_max_van, pax_max_micro)

        # Gerando rotas de apoios de rotas alternativas 3

        df_roteiros_alternativos_3, df_roteiros_apoios_alternativos_3 = gerar_roteiros_apoio(df_roteiros_alternativos_3)

        # Roteirizando carro principal desconsiderando os hoteis do apoio

        df_roteiros_alternativos_3 = roteirizar_pos_apoios(df_roteiros_apoios_alternativos_3, df_roteiros_alternativos_3)

        # Gerando rotas de apoios de rotas alternativas 4

        df_roteiros_alternativos_4 = identificar_apoios_em_df_4(df_roteiros_alternativos_4, pax_max_utilitario, pax_max_van, pax_max_micro)

        # Gerando rotas de apoios de rotas alternativas 4

        df_roteiros_alternativos_4, df_roteiros_apoios_alternativos_4 = gerar_roteiros_apoio(df_roteiros_alternativos_4)

        # Roteirizando carro principal desconsiderando os hoteis do apoio

        df_roteiros_alternativos_4 = roteirizar_pos_apoios(df_roteiros_apoios_alternativos_4, df_roteiros_alternativos_4)

        # Gerando rotas de apoios de rotas alternativas 4

        df_roteiros_alternativos_5 = identificar_apoios_em_df(df_roteiros_alternativos_5, pax_max_utilitario, pax_max_van, pax_max_micro)

        # Gerando rotas de apoios de rotas alternativas 4

        df_roteiros_alternativos_5, df_roteiros_apoios_alternativos_5 = gerar_roteiros_apoio(df_roteiros_alternativos_5)

        # Roteirizando carro principal desconsiderando os hoteis do apoio

        df_roteiros_alternativos_5 = roteirizar_pos_apoios(df_roteiros_apoios_alternativos_5, df_roteiros_alternativos_5)

        # Roteirizando de forma invertida quando só tem hoteis até o Marsol

        if servico_roteiro=='OUT - Natal':

            df_router_filtrado_2 = roteirizar_natal_apenas_primeiros_hoteis(df_router_filtrado_2, sequencia_marsol)

            df_roteiros_alternativos = roteirizar_natal_apenas_primeiros_hoteis(df_roteiros_alternativos, sequencia_marsol)

            df_roteiros_alternativos_2 = roteirizar_natal_apenas_primeiros_hoteis(df_roteiros_alternativos_2, sequencia_marsol)

            df_roteiros_alternativos_3 = roteirizar_natal_apenas_primeiros_hoteis(df_roteiros_alternativos_3, sequencia_marsol)

            df_roteiros_alternativos_4 = roteirizar_natal_apenas_primeiros_hoteis(df_roteiros_alternativos_4, sequencia_marsol)

            df_roteiros_alternativos_5 = roteirizar_natal_apenas_primeiros_hoteis(df_roteiros_alternativos_5, sequencia_marsol)

        df_roteiros_alternativos = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos)

        df_roteiros_alternativos_2 = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos_2)

        df_roteiros_alternativos_2 = verificar_rotas_identicas(df_roteiros_alternativos, df_roteiros_alternativos_2)

        df_roteiros_alternativos_3 = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos_3)

        df_roteiros_alternativos_3 = verificar_rotas_identicas(df_roteiros_alternativos_2, df_roteiros_alternativos_3)

        df_roteiros_alternativos_3 = verificar_rotas_identicas(df_roteiros_alternativos, df_roteiros_alternativos_3)

        df_roteiros_alternativos_4 = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos_4)

        df_roteiros_alternativos_4 = verificar_rotas_identicas(df_roteiros_alternativos_3, df_roteiros_alternativos_4)

        df_roteiros_alternativos_4 = verificar_rotas_identicas(df_roteiros_alternativos_2, df_roteiros_alternativos_4)

        df_roteiros_alternativos_4 = verificar_rotas_identicas(df_roteiros_alternativos, df_roteiros_alternativos_4)

        df_roteiros_alternativos_5 = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos_5)

        df_roteiros_alternativos_5 = verificar_rotas_identicas(df_roteiros_alternativos_4, df_roteiros_alternativos_5)

        df_roteiros_alternativos_5 = verificar_rotas_identicas(df_roteiros_alternativos_3, df_roteiros_alternativos_5)

        df_roteiros_alternativos_5 = verificar_rotas_identicas(df_roteiros_alternativos_2, df_roteiros_alternativos_5)

        df_roteiros_alternativos_5 = verificar_rotas_identicas(df_roteiros_alternativos, df_roteiros_alternativos_5)

        # Plotando roteiros de cada carro

        st.divider()

        row_warning = st.columns(1)

        row3 = st.columns(3)

        coluna = 0
        
        hora_execucao = datetime.now()
        
        hora_execucao_menos_3h = hora_execucao - timedelta(hours=3)

        hora_execucao = hora_execucao_menos_3h.strftime("%d-%m-%Y %Hh%Mm")

        st.session_state.nome_html = f"{hora_execucao} {nome_html_ref}.html"

        st.session_state.data_roteiro_ref = data_roteiro.strftime("%d/%m/%Y")

        st.session_state.df_hoteis_pax_max = df_hoteis_pax_max

        st.session_state.df_router_filtrado_2 = df_router_filtrado_2

        st.session_state.df_roteiros_alternativos = df_roteiros_alternativos

        st.session_state.df_roteiros_alternativos_2 = df_roteiros_alternativos_2

        st.session_state.df_roteiros_alternativos_3 = df_roteiros_alternativos_3

        st.session_state.df_roteiros_alternativos_4 = df_roteiros_alternativos_4

        st.session_state.df_roteiros_alternativos_5 = df_roteiros_alternativos_5

        st.session_state.df_roteiros_apoios = df_roteiros_apoios

        st.session_state.df_roteiros_apoios_alternativos = df_roteiros_apoios_alternativos

        st.session_state.df_roteiros_apoios_alternativos_2 = df_roteiros_apoios_alternativos_2

        st.session_state.df_roteiros_apoios_alternativos_3 = df_roteiros_apoios_alternativos_3

        st.session_state.df_roteiros_apoios_alternativos_4 = df_roteiros_apoios_alternativos_4

        st.session_state.df_roteiros_apoios_alternativos_5 = df_roteiros_apoios_alternativos_5

    verificar_rotas_alternativas_ou_plotar_roteiros_com_apoio(df_roteiros_alternativos, row_warning, row3, coluna, df_hoteis_pax_max, df_router_filtrado_2, df_roteiros_apoios, 
                                                    df_roteiros_apoios_alternativos, st.session_state.df_juncao_voos, 
                                                    st.session_state.nome_html)

# Gerar roteiros finais

if 'nome_html' in st.session_state and (len(st.session_state.df_roteiros_alternativos)>0 or len(st.session_state.df_roteiros_alternativos_2)>0 or len(st.session_state.df_roteiros_alternativos_3)>0 or \
        len(st.session_state.df_roteiros_alternativos_4)>0 or len(st.session_state.df_roteiros_alternativos_5)>0):

    st.divider()

    row_rotas_alternativas = st.columns(1)

    row3 = st.columns(3)

    coluna = 0

    lista_rotas_alternativas = st.session_state.df_roteiros_alternativos['Roteiro'].unique().tolist()

    lista_rotas_alternativas_2 = st.session_state.df_roteiros_alternativos_2['Roteiro'].unique().tolist()

    lista_rotas_alternativas_3 = st.session_state.df_roteiros_alternativos_3['Roteiro'].unique().tolist()

    lista_rotas_alternativas_4 = st.session_state.df_roteiros_alternativos_4['Roteiro'].unique().tolist()

    lista_rotas_alternativas_5 = st.session_state.df_roteiros_alternativos_5['Roteiro'].unique().tolist()

    if len(st.session_state.df_router_filtrado_2)>0:

        with row_rotas_alternativas[0]:

            st.markdown('*Rotas Alternativas 1 são rotas que buscam equilibrar a quantidade de hoteis em cada carro.*')

            rotas_alternativas = st.multiselect('Selecione as Rotas Alternativas 1 que serão usadas', lista_rotas_alternativas)

            st.markdown('*Rotas Alternativas 2 são rotas que tentam colocar apenas um carro para o roteiro, desde que o número de hoteis da rota não passe de 10 e o intervalo entre o primeiro e último hotel seja menor que 1 hora.*')

            rotas_alternativas_2 = st.multiselect('Selecione as Rotas Alternativas 2 que serão usadas', lista_rotas_alternativas_2)

            st.markdown('*Rotas Alternativas 3 são rotas que evitam que dois carros de um roteiro estejam buscando um mesmo bairro/micro região.*')

            rotas_alternativas_3 = st.multiselect('Selecione as Rotas Alternativas 3 que serão usadas', lista_rotas_alternativas_3)

            st.markdown('*Rotas Alternativas 4 são rotas que tentam colocar menos carros, compensando com mais apoios.*')

            rotas_alternativas_4 = st.multiselect('Selecione as Rotas Alternativas 4 que serão usadas', lista_rotas_alternativas_4)

            st.markdown('*Rotas Alternativas 5 são rotas que tentam colocar menos carros, lotando os carros ao máximo e importando-se apenas com a quantidade máxima de 10 hoteis.*')

            rotas_alternativas_5 = st.multiselect('Selecione as Rotas Alternativas 5 que serão usadas', lista_rotas_alternativas_5)
        
            gerar_roteiro_final = st.button('Gerar Roteiro Final')

        if not gerar_roteiro_final:

            coluna = plotar_roteiros_gerais_alternativos_com_apoio(st.session_state.df_router_filtrado_2, st.session_state.df_roteiros_apoios, 
                                                        st.session_state.df_roteiros_alternativos, 
                                                        st.session_state.df_roteiros_alternativos_2, 
                                                        st.session_state.df_roteiros_alternativos_3, 
                                                        st.session_state.df_roteiros_alternativos_4,
                                                        st.session_state.df_roteiros_alternativos_5,
                                                        st.session_state.df_roteiros_apoios_alternativos, 
                                                        st.session_state.df_roteiros_apoios_alternativos_2, 
                                                        st.session_state.df_roteiros_apoios_alternativos_3, 
                                                        st.session_state.df_roteiros_apoios_alternativos_4, 
                                                        st.session_state.df_roteiros_apoios_alternativos_5, coluna, row3)
            
        else:

            if (set(rotas_alternativas) & set(rotas_alternativas_2)) or \
            (set(rotas_alternativas) & set(rotas_alternativas_3)) or \
            (set(rotas_alternativas) & set(rotas_alternativas_4)) or \
            (set(rotas_alternativas) & set(rotas_alternativas_5)) or \
            (set(rotas_alternativas_2) & set(rotas_alternativas_3)) or \
            (set(rotas_alternativas_2) & set(rotas_alternativas_4)) or \
            (set(rotas_alternativas_2) & set(rotas_alternativas_5)) or \
            (set(rotas_alternativas_3) & set(rotas_alternativas_4)) or \
            (set(rotas_alternativas_3) & set(rotas_alternativas_5)) or \
            (set(rotas_alternativas_4) & set(rotas_alternativas_5)):

                st.error('Só pode selecionar uma opção alternativa p/ cada roteiro')

            else:

                if 'df_servico_voos_horarios' in st.session_state:
                    
                    st.session_state['df_servico_voos_horarios'] = pd.DataFrame(columns=['Servico', 'Voo', 'Horario Voo'])

                df_hoteis_pax_max = st.session_state.df_hoteis_pax_max

                df_router_filtrado_2 = st.session_state.df_router_filtrado_2

                df_roteiros_apoios = st.session_state.df_roteiros_apoios

                df_roteiros_apoios_alternativos = pd.DataFrame(columns=st.session_state.df_roteiros_apoios_alternativos.columns.tolist())

                if len(rotas_alternativas)>0:

                    df_roteiros_alternativos = st.session_state.df_roteiros_alternativos\
                        [st.session_state.df_roteiros_alternativos['Roteiro'].isin(rotas_alternativas)].reset_index(drop=True)
                    
                    df_roteiros_apoios_alternativos = st.session_state.df_roteiros_apoios_alternativos\
                        [st.session_state.df_roteiros_apoios_alternativos['Roteiro'].isin(rotas_alternativas)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_apoios = df_roteiros_apoios[~df_roteiros_apoios['Roteiro'].isin(rotas_alternativas)]\
                        .reset_index(drop=True)
                    
                else:

                    df_roteiros_alternativos = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos.columns.tolist())

                if len(rotas_alternativas_2)>0:

                    df_roteiros_alternativos_2 = st.session_state.df_roteiros_alternativos_2\
                        [st.session_state.df_roteiros_alternativos_2['Roteiro'].isin(rotas_alternativas_2)].reset_index(drop=True)
                    
                    df_roteiros_apoios_alternativos_2 = st.session_state.df_roteiros_apoios_alternativos_2\
                        [st.session_state.df_roteiros_apoios_alternativos_2['Roteiro'].isin(rotas_alternativas_2)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas_2)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_apoios = df_roteiros_apoios[~df_roteiros_apoios['Roteiro'].isin(rotas_alternativas_2)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_roteiros_alternativos_2], ignore_index=True)

                    df_roteiros_apoios_alternativos = pd.concat([df_roteiros_apoios_alternativos, df_roteiros_apoios_alternativos_2], 
                                                                ignore_index=True)
                    
                else:

                    df_roteiros_alternativos_2 = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos_2.columns.tolist())

                if len(rotas_alternativas_3)>0:

                    df_roteiros_alternativos_3 = st.session_state.df_roteiros_alternativos_3\
                        [st.session_state.df_roteiros_alternativos_3['Roteiro'].isin(rotas_alternativas_3)].reset_index(drop=True)
                    
                    df_roteiros_apoios_alternativos_3 = st.session_state.df_roteiros_apoios_alternativos_3\
                        [st.session_state.df_roteiros_apoios_alternativos_3['Roteiro'].isin(rotas_alternativas_3)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas_3)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_apoios = df_roteiros_apoios[~df_roteiros_apoios['Roteiro'].isin(rotas_alternativas_3)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_roteiros_alternativos_3], ignore_index=True)

                    df_roteiros_apoios_alternativos = pd.concat([df_roteiros_apoios_alternativos, df_roteiros_apoios_alternativos_3], 
                                                                ignore_index=True)
                    
                else:

                    df_roteiros_alternativos_3 = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos_3.columns.tolist())

                if len(rotas_alternativas_4)>0:

                    df_roteiros_alternativos_4 = st.session_state.df_roteiros_alternativos_4\
                        [st.session_state.df_roteiros_alternativos_4['Roteiro'].isin(rotas_alternativas_4)].reset_index(drop=True)
                    
                    df_roteiros_apoios_alternativos_4 = st.session_state.df_roteiros_apoios_alternativos_4\
                        [st.session_state.df_roteiros_apoios_alternativos_4['Roteiro'].isin(rotas_alternativas_4)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas_4)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_apoios = df_roteiros_apoios[~df_roteiros_apoios['Roteiro'].isin(rotas_alternativas_4)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_roteiros_alternativos_4], ignore_index=True)

                    df_roteiros_apoios_alternativos = pd.concat([df_roteiros_apoios_alternativos, df_roteiros_apoios_alternativos_4], 
                                                                ignore_index=True)
                    
                else:

                    df_roteiros_alternativos_4 = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos_4.columns.tolist())

                if len(rotas_alternativas_5)>0:

                    df_roteiros_alternativos_5 = st.session_state.df_roteiros_alternativos_5\
                        [st.session_state.df_roteiros_alternativos_5['Roteiro'].isin(rotas_alternativas_5)].reset_index(drop=True)
                    
                    df_roteiros_apoios_alternativos_5 = st.session_state.df_roteiros_apoios_alternativos_5\
                        [st.session_state.df_roteiros_apoios_alternativos_5['Roteiro'].isin(rotas_alternativas_5)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas_5)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_apoios = df_roteiros_apoios[~df_roteiros_apoios['Roteiro'].isin(rotas_alternativas_5)]\
                        .reset_index(drop=True)
                    
                    df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_roteiros_alternativos_5], ignore_index=True)

                    df_roteiros_apoios_alternativos = pd.concat([df_roteiros_apoios_alternativos, df_roteiros_apoios_alternativos_5], 
                                                                ignore_index=True)
                    
                else:

                    df_roteiros_alternativos_5 = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos_5.columns.tolist())

                lista_dfs = [df_hoteis_pax_max, df_router_filtrado_2, df_roteiros_apoios, df_roteiros_alternativos]

                n_carros = 0

                for df in lista_dfs:
                    
                    if len(df)>0:

                        n_carros += len(df[['Roteiro', 'Carros']].drop_duplicates())

                with row_rotas_alternativas[0]:

                    st.header(f'A roteirização usou um total de {n_carros} carros')

                if len(df_hoteis_pax_max)>0:

                    coluna = plotar_roteiros_simples(df_hoteis_pax_max, row3, coluna)

                coluna = plotar_roteiros_gerais_final_com_apoio(df_router_filtrado_2, df_roteiros_apoios, df_roteiros_alternativos, 
                                                    df_roteiros_apoios_alternativos, coluna)
                
                html = definir_html(st.session_state.df_juncao_voos)

                criar_output_html(st.session_state.nome_html, html)

                df_pdf = pd.concat([df_router_filtrado_2, df_hoteis_pax_max, df_roteiros_alternativos], ignore_index=True)

                df_pdf_apoios = pd.concat([df_roteiros_apoios, df_roteiros_apoios_alternativos], ignore_index=True)

                st.session_state.df_insercao = df_pdf[['Id_Reserva', 'Id_Servico', 'Data Horario Apresentacao', 'Data Horario Apresentacao Original']].reset_index(drop=True)

                df_pdf_2 = df_pdf[['Reserva', 'Data Horario Apresentacao']].sort_values(by='Reserva').reset_index(drop=True)
                
                for index in range(len(df_pdf)):

                    tipo_de_servico_ref = df_pdf.at[index, 'Modo do Servico']

                    juncao_ref_2 = df_pdf.at[index, 'Junção']

                    if tipo_de_servico_ref == 'REGULAR' and not pd.isna(juncao_ref_2):

                        df_pdf.at[index, 'Horario Voo / Menor Horário'] = df_pdf.at[index, 'Menor Horário']

                    elif (tipo_de_servico_ref == 'REGULAR' and pd.isna(juncao_ref_2)) or (tipo_de_servico_ref != 'REGULAR'):

                        df_pdf.at[index, 'Horario Voo / Menor Horário'] = df_pdf.at[index, 'Horario Voo']

                df_pdf = df_pdf.sort_values(by=['Horario Voo / Menor Horário', 'Junção']).reset_index(drop=True)

                inserir_roteiros_html_com_apoio(st.session_state.nome_html, df_pdf, df_pdf_apoios)

                inserir_html_2(st.session_state.nome_html, df_pdf_2)

                with open(st.session_state.nome_html, "r", encoding="utf-8") as file:

                    html_content = file.read()

                salvar_rotas_historico(df_pdf)

                st.download_button(
                    label="Baixar Arquivo HTML",
                    data=html_content,
                    file_name=st.session_state.nome_html,
                    mime="text/html"
                )

if 'df_insercao' in st.session_state and len(st.session_state.df_insercao)>0:

    lancar_horarios = st.button('Lançar Horários')

    if lancar_horarios:

        df_insercao = atualizar_banco_dados(st.session_state.df_insercao, 'test_phoenix_natal')

        # st.rerun()

if servico_roteiro and data_roteiro:

    enviar_informes = st.button(f'Enviar Informativos de Saída - {servico_roteiro} | {data_roteiro.strftime("%d/%m/%Y")}')

    if enviar_informes:

        puxar_historico('1ch1NfOKeK008ZeqexQTzOqXuCZ2Q6sL8hY2sPqQegLQ', ['Histórico Roteiros'], ['df_historico_roteiros'])

        st.session_state.df_historico_roteiros['Data Execucao'] = pd.to_datetime(st.session_state.df_historico_roteiros['Data Execucao']).dt.date

        st.session_state.df_historico_roteiros['Id_Servico'] = pd.to_numeric(st.session_state.df_historico_roteiros['Id_Servico'])

        if servico_roteiro!='OUT - Natal':

            df_ref_thiago = st.session_state.df_historico_roteiros[(st.session_state.df_historico_roteiros['Data Execucao']==data_roteiro) & 
                                                                   (st.session_state.df_historico_roteiros['Servico']==servico_roteiro)].reset_index(drop=True)

            df_verificacao = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                                         (st.session_state.df_router['Servico']==servico_roteiro)].reset_index(drop=True)
            
        else:

            df_ref_thiago = st.session_state.df_historico_roteiros[(st.session_state.df_historico_roteiros['Data Execucao']==data_roteiro) & 
                                                                   ((st.session_state.df_historico_roteiros['Servico']==servico_roteiro) | 
                                                                    (st.session_state.df_historico_roteiros['Servico']=='OUT - Camurupim'))].reset_index(drop=True)

            df_verificacao = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                        ((st.session_state.df_router['Servico']==servico_roteiro) | 
                                                         (st.session_state.df_router['Servico']=='OUT - Camurupim'))].reset_index(drop=True)

        id_servicos_verificacao = set(df_verificacao['Id_Servico'])
        
        id_servicos_ref_thiago = set(df_ref_thiago['Id_Servico'])

        id_servicos_unicos = id_servicos_verificacao - id_servicos_ref_thiago

        reservas_nao_roteirizadas = df_verificacao.loc[~df_verificacao['Id_Servico'].isin(df_ref_thiago['Id_Servico']), 'Reserva'].unique()

        if len(reservas_nao_roteirizadas)>0:

            nome_reservas = ', '.join(reservas_nao_roteirizadas)

            st.warning(f'As reservas {nome_reservas} não foram roteirizadas e, portanto, não foi enviado informativos de saída para elas')
    
        dict_tag_servico = \
            {'OUT - Natal': 'Natal', 
             'OUT - Pipa': 'Pipa', 
             'OUT - Touros': 'Touros', 
             'OUT - São Miguel Gostoso': 'São Miguel do Gostoso', 
             'Out - Galinhos': 'Galinhos', 
             'OUT - Camurupim': 'Camurupim', 
             'Out - Genipabu': 'Genipabu', 
             'OUT - Pirangi': 'Pirangi', 
             'OUT - Baia Formosa': 'Baía Formosa'}
    
        if len(df_ref_thiago)>0:
    
            lista_ids_servicos = df_ref_thiago['Id_Servico'].tolist()
    
            webhook_thiago = "https://conexao.multiatend.com.br/webhook/luckenvioinformativonatal"
            
            data_roteiro_str = data_roteiro.strftime('%Y-%m-%d')
            
            payload = {"data": data_roteiro_str, 
                       "ids_servicos": lista_ids_servicos, 
                       "tag_servico": dict_tag_servico[servico_roteiro]}
            
            response = requests.post(webhook_thiago, json=payload)
            
            if response.status_code == 200:
                
                    st.success(f"Informativos Enviados com Sucesso!")
                
            else:
                
                st.error(f"Erro. Favor contactar o suporte")

                st.error(f"{response}")

        else:

            st.error(f'Não existem roteiros feitos para a data e serviços selecionados')
