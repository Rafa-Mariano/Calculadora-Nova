import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import os
import json
from dateutil.relativedelta import relativedelta
import pymssql
import locale


def formatar_numero(numero):
    return f'R$ {numero:,.2f}'.replace('.', '#').replace(',', '.').replace('#', ',')

## ---------------------------------------------------------------------------------------------------
def calcular_parcelas_numero(valor_total, numero_parcelas, taxa_juros_mensal, data_inicio, periodicidade):
    # Verificar a diferença de dias entre a data atual e a data de início
    data_atual = datetime.today().date()
    diferenca_dias = (data_inicio - data_atual).days

    # Se a data de início for futura, calcular o juros proporcional
    if diferenca_dias > 0:
        taxa_juros_diaria = (1 + taxa_juros_mensal) ** (1/30) - 1
        juros_proporcional = valor_total * taxa_juros_diaria * diferenca_dias
        valor_total += juros_proporcional  # Ajusta o valor total para incluir os juros proporcionais

    # Cálculo do valor da parcela
    valor_parcela = valor_total * (taxa_juros_mensal / (1 - (1 + taxa_juros_mensal)**(-numero_parcelas)))
    saldo_devedor = valor_total

    if valor_parcela > saldo_devedor:
        valor_parcela = saldo_devedor

    juros_total = valor_parcela * numero_parcelas - valor_total

    # Geração das datas de vencimento
    datas_vencimento = [data_inicio]
    if periodicidade == 'Mensal':
        for i in range(1, numero_parcelas):
            datas_vencimento.append(data_inicio + relativedelta(months=i))
    elif periodicidade == 'Quinzenal':
        for i in range(1, numero_parcelas):
            datas_vencimento.append(datas_vencimento[i-1] + timedelta(days=15))
    elif periodicidade == 'Semanal':
        for i in range(1, numero_parcelas):
            datas_vencimento.append(datas_vencimento[i-1] + timedelta(days=7))
    elif periodicidade == 'A cada 2 dias':
        for i in range(1, numero_parcelas):
            datas_vencimento.append(datas_vencimento[i-1] + timedelta(days=2))

    # Cálculo das parcelas
    parcelas = []
    saldo_devedor = valor_total
    for i in range(numero_parcelas):
        amortizacao = valor_parcela - saldo_devedor * taxa_juros_mensal
        parcelas.append({
            'Parcela': i+1, 
            'Data Vencimento': datas_vencimento[i], 
            'Valor Parcela': valor_parcela, 
            'Saldo Devedor': saldo_devedor,
            'Juros': saldo_devedor * taxa_juros_mensal, 
            'Amortização': amortizacao
        })
        saldo_devedor -= amortizacao

    # Criar DataFrame
    df = pd.DataFrame(parcelas)
    df['Saldo Devedor'] = df['Saldo Devedor'].map(formatar_numero)
    df['Valor Parcela'] = df['Valor Parcela'].map(formatar_numero)
    df['Juros'] = df['Juros'].map(formatar_numero)
    df['Amortização'] = df['Amortização'].map(formatar_numero)

    return valor_parcela, juros_total, df


### ------------------------------------------------------------------------------------------


# def calcular_parcelas_numero(valor_total, numero_parcelas, taxa_juros_mensal, data_inicio, periodicidade):
#     valor_parcela = valor_total * (taxa_juros_mensal / (1 - (1 + taxa_juros_mensal)**(-numero_parcelas)))
#     saldo_devedor = valor_total

#     if valor_parcela > saldo_devedor:
#         valor_parcela = saldo_devedor

#     juros_total = valor_parcela * numero_parcelas - valor_total

#     datas_vencimento = [data_inicio]
#     if periodicidade == 'Mensal':
#         for i in range(1, numero_parcelas):
#             datas_vencimento.append(data_inicio + relativedelta(months=i))
#     elif periodicidade == 'Quinzenal':
#         for i in range(1, numero_parcelas):
#             datas_vencimento.append(datas_vencimento[i-1] + timedelta(days=15))
#     elif periodicidade == 'Semanal':
#         for i in range(1, numero_parcelas):
#             datas_vencimento.append(datas_vencimento[i-1] + timedelta(days=7))
#     elif periodicidade == 'A cada 2 dias':
#         for i in range(1, numero_parcelas):
#             datas_vencimento.append(datas_vencimento[i-1] + timedelta(days=2))

#     parcelas = []
#     saldo_devedor = valor_total
#     # saldo_devedor_anterior = (valor_total + taxa_juros_mensal) - valor_parcela
#     for i in range(numero_parcelas):
#         amortizacao = valor_parcela - saldo_devedor * taxa_juros_mensal
#         # saldo_devedor_anterior = (saldo_devedor + taxa_juros_mensal) - valor_parcela
#         parcelas.append({'Parcela': i+1, 'Data Vencimento': datas_vencimento[i],'Valor Parcela': valor_parcela, 'Saldo Devedor': saldo_devedor, 
#                          'Juros': saldo_devedor * taxa_juros_mensal, 'Amortização': amortizacao})
#         saldo_devedor -= amortizacao

#     df = pd.DataFrame(parcelas)
#     df['Saldo Devedor'] = df['Saldo Devedor'].map(formatar_numero)
#     df['Valor Parcela'] = df['Valor Parcela'].map(formatar_numero)
#     df['Juros'] = df['Juros'].map(formatar_numero)
#     df['Amortização'] = df['Amortização'].map(formatar_numero)
#     # df['Saldo Devedor Anterior'] = df['Saldo Devedor Anterior'].map(formatar_numero)

#     return valor_parcela, juros_total, df

def calcular_parcelas_valor(valor_total, valor_parcela, taxa_juros_mensal, data_inicio, periodicidade):
    parcelas = []
    saldo_devedor = valor_total
    data_vencimento = data_inicio
    while saldo_devedor > 0:
        amortizacao = valor_parcela - saldo_devedor * taxa_juros_mensal
        parcelas.append({'Parcela': len(parcelas) + 1, 'Data Vencimento': data_vencimento, 'Saldo Devedor': saldo_devedor, 
                         'Valor Parcela': valor_parcela, 'Juros': saldo_devedor * taxa_juros_mensal, 'Amortização': amortizacao})
        saldo_devedor -= amortizacao
        if periodicidade == 'Mensal':
            data_vencimento += timedelta(days=30)
        elif periodicidade == 'Quinzenal':
            data_vencimento += timedelta(days=15)
        elif periodicidade == 'Semanal':
            data_vencimento += timedelta(days=7)
        elif periodicidade == 'A cada 2 dias':
            data_vencimento += timedelta(days=2)

    df = pd.DataFrame(parcelas)
    df['Saldo Devedor'] = df['Saldo Devedor'].map(formatar_numero)
    df['Valor Parcela'] = df['Valor Parcela'].map(formatar_numero)
    df['Juros'] = df['Juros'].map(formatar_numero)
    df['Amortização'] = df['Amortização'].map(formatar_numero)

    return df



# Adicione o título com HTML, incluindo a imagem do logo
st.title("Calculadora Financeira da Confiança")

modo_calculo = st.radio("Modo de cálculo:", options=['Número de parcelas', 'Valor mínimo da parcela'])

if modo_calculo == 'Número de parcelas':
    valor_total = st.number_input('Valor da Renegociação:', min_value=0.01, step=0.01)
    numero_parcelas = st.number_input('Número de parcelas:', min_value=1, step=1, format='%d')
    taxa_juros_mensal = st.number_input('Taxa de juros mensal (%):', min_value=0.01, step=0.01)
    periodicidade = st.radio("Periodicidade dos pagamentos:", options=['Mensal', 'Quinzenal', 'Semanal', 'A cada 2 dias'])

    data_inicio = st.date_input('Data de início do financiamento:', min_value=datetime.now())
    
    if st.button('Calcular'):
        
        valor_parcela, juros_total, df = calcular_parcelas_numero(valor_total, numero_parcelas, taxa_juros_mensal / 100, data_inicio, periodicidade)
        soma = valor_total + juros_total

        st.write(f'Valor de cada parcela: R$ {valor_parcela:,.2f}'.replace('.', '#').replace(',', '.').replace('#', ','))
        st.write(f'Total de juros pagos: R$ {juros_total:,.2f}'.replace('.', '#').replace(',', '.').replace('#', ','))
        st.write(f'Valor do financiamento: R$ {soma:,.2f}'.replace('.', '#').replace(',', '.').replace('#', ','))
        st.write(df)

        if st.button('Nova simulação'):
            df.to_excel('resultados_financiamento.xlsx', index=False)
            st.success('Arquivo Excel gerado com sucesso!')


elif modo_calculo == 'Valor mínimo da parcela':
    valor_total = st.number_input('Valor total:', min_value=0.01, step=0.01)
    valor_minimo_parcela = st.number_input('Valor mínimo da parcela:', min_value=0.01, step=0.01)
    taxa_juros_mensal = st.number_input('Taxa de juros mensal (%):', min_value=0.01, step=0.01)
    periodicidade = st.radio("Periodicidade dos pagamentos:", options=['Mensal', 'Quinzenal', 'Semanal', 'A cada 2 dias'])

    

    data_inicio = st.date_input('Data de início do financiamento:', min_value=datetime.now())

    if st.button('Calcular'):
        df = calcular_parcelas_valor(valor_total, valor_minimo_parcela, taxa_juros_mensal / 100, data_inicio, periodicidade)
        # soma = valor_total + juros_total
        # st.write(f'Valor de cada parcela: R$ {valor_minimo_parcela:,.2f}'.replace('.', '#').replace(',', '.').replace('#', ','))
        # st.write(f'Total de juros pagos: R$ {juros_total / 100:,.2f}'.replace('.', '#').replace(',', '.').replace('#', ','))
        # st.write(f'Valor do financiamento: R$ {soma:,.2f}'.replace('.', '#').replace(',', '.').replace('#', ','))
        # st.write(f'Quantidade de parcelas: R$ {}')
        st.write(df)

        total_parcela = df['Valor Parcela'].sum()
        total_juros = df['Juros'].sum()

        if st.button('Nova simulação'):
            df.to_excel('resultados_financiamento.xlsx', index=False)
            st.success('Arquivo Excel gerado com sucesso!')




