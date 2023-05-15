"""
    Layout das mensagens JSON utilizadas nas API´s com o servidor de TEF.
    Os campos estão inicializados com valores, somente para exemplicaficação dos tipos de dados
"""

DadosLogin = {
            "headerIn": {
                "transação": "Login",
                "empresa": 1,
                "loja": 2,
                "pdv": 2
            },
            "usuario": "operCentro",
            "senha": "**********",
            "inicializaLoja": 1
        }

DadosInicializaIn = {
    "headerIn": {
        "transação": "InicializaPDV",
        "empresa": 1,
        "loja": 2,
        "pdv": 2
    },
    "usuario": "janete"
}

DadosAberturaIn = {
    "headerIn": {
        "transação": "AberturaPDV",
        "empresa": 1,
        "loja": 2,
        "pdv": 2
    },
    "usuario": "operCentro"
}

DadosVendaCreditoIn = {
    "headerIn": {
        "transação": "CredVista",
        "empresa": 1,
        "loja": 2,
        "pdv": 2
    },
    "usuario": "operCentro",
    "numCartao": "553622222222222222222",
    "validadeCartao": "07/23",
    "codSeg": "445",
    "valorTrans": 10.50,
    "numParcelas": 0
}

DadosVendaCreditoOut = {
    "headerOut": {
        "codErro": 99,
        "mensagem": 'string',
    },
    "codRespAdiq": 99,
    "msgAdiq": "string",
    "bandeira": "string",
    "adquirente": "string",
    "codAut": "string",
    "NSUTef": "string",
    "NSUHost": "string",
    "dataHoraTrans": "data/hora aprovação",
    "cupomTrans": "comprovante",
}

DadosVendaDebitoIn = {
    "headerIn": {
        "transação": "Debito",
        "empresa": 1,
        "loja": 2,
        "pdv": 2
    },
    "usuario": "operCentro",
    "numCartao": "5536360607552502",
    "valorTrans": 10.50,
    "senha": "senha"
}

DadosConfirmacao = {
    "headerIn": {
        "transação": "Confirma/Desfazimento",
        "empresa": 1,
        "loja": 2,
        "pdv": 2
    },
    "usuario": "operCentro",
    "NSU_Original": "1234567890",
    "dataHoraOriginal": "data/hora trans original"
}

DadosPesqLog = {
    "headerIn": {
        "transação": "PesqLog",
        "empresa": 1,
        "loja": 2,
        "pdv": 2
    },
    "usuario": "operCentro",
    "NSU": 273,
    "dataInicial": "data inicial para pesquisa",
    "dataFinal": "data final para pesquisa",
    "statusTrans": "status da transação"
}

DadosCancelamento = {
    "headerIn": {
        "transação": "Cancelamento",
        "empresa": 1,
        "loja": 2,
        "pdv": 2
    },
    "usuario": "operCentro",
    "NSU_Original": "1234567890",
    "dataOriginal": "data trans original",
    "numCartao": "5536360607552502",
    "valorTrans": 10.50,
    "validadeCartao": "07/23",
    "NSU_HOST_Original": "1234567890",
    "supervisor": "janete",
    "senha": "*******"
}



