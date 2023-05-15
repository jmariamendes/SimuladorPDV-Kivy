import json
import io
from cryptography.fernet import Fernet
import pickle
import os
from time import sleep
import socket
import datetime
import threading

from djangomail import send_mail
from kivy.network.urlrequest import UrlRequest
from kivy.clock import Clock
from kivy.utils import platform

from msg_json import DadosLogin, DadosInicializaIn, DadosAberturaIn, DadosCancelamento
import settings


class RotinasAuxiliares:
    """ Rotinas auxiliares e variáveis globais """

    def __init__(self, app):
        # super().__init__()
        self.app = app
        # self.URL = f"http://localhost:8000/api/"  # endereço do servidor TEF
        self.URL = f"http://supertef.herokuapp.com/api/"  # endereço do servidor TEF no heroku
        # self.IpPinPad = '192.168.15.7' # endereço IP do Pin Pad Android
        self.IpPinPad = 'localhost'  # endereço IP do Pin Pad Windows
        self.portaPinPad = 50007  # Porta do Pin Pad
        self.socketPin = None
        self.erroPinPad = True  # sem conexão com Pin Pad
        self.loja = 2
        self.empresa = 1
        self.perfilUsuario = 0
        self.NomeUsuarioAtivo = ''
        self.endEmail = ''
        self.passEmail = ''
        self.email_comprovante = ''  # e-mail para envio do comprovante
        self.msg_erro_pin = ''  # msg de erro a ser exibida no Pin Pad
        self.response = None
        self.OK = False  # para o diálogo de mensagens de erro/informação(app.show_alert_dialog)
        self.statusInic = 0  # status da inicialização, para montar o menu: 1= loginOK, 2=inicializaçãoOK, 3=aberturaOK
        # numPDV = os.environ.get("NUMERO_PDV")
        # self.pdv = int(numPDV)
        self.pdv = 2
        self.buffer_envio_servidor = {}  # buffer para envio de msg para o servidor TEF
        self.buffer_receb_servidor = {}  # buffer para recebimento de msg do servidor TEF
        self.reg_atual = {}  # registro de log atual sendo exibido
        self.transHabilitadas = {}  # transações habilitadas no PDV
        self.DadosPinPad = ''  # buffer para envio/recebimento de msg para o Pin Pad
        self.opcao = ''  # opção selecionada no dialogo de tipo de transação
        self.itens_menu = [] # transações habilitadas para a montagem do menu dinâmico
        self.dict_menu_items = {} # dicionário transações habilitadas, para o widget MDDropdownMenu
        self.menu_top_bar = None # menu top bar

        """ Dados do cancelamento """
        self.canc_num_cartao = ""
        self.canc_nsu_tef = ""
        self.canc_valor = 0.0
        self.canc_data = ""
        self.canc_nsu_host = ""

        self.config = ConfigModel(self)  # instancia as rotinas de acesso ao arquivo de configuração
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    def ValidaUsuarioSenha(self, Usuario, Senha):

        """ Valida o login do usuário:
            1. Todos os dados do usuário serão validados pelo servidor. Não é feita nenhuma validação local
            1. Se a loja não estiver inicializada, sinaliza o servidor, e se o usuário for do perfil gerente,
               permite que ele faça a inicialização, após a validação dos dados do login
            2. Monta o JSON de Login para a mensagem de envio dos dados para o servidor, para validação do usuário/senha
            3. Caso a loja já esteja inicializada, a senha do usuário será criptografada antes de enviar a msg
            4. Trata a msg de retorno do servidor
         """

        messagebox = True
        if not self.config.lerDadosLoja():
            """ Primeiro Login neste PDV, ainda não existe o arquivo de configuração """
            DadosLogin['headerIn']['loja'] = 0
            DadosLogin['headerIn']['empresa'] = 0
            DadosLogin['headerIn']['pdv'] = 0
            DadosLogin['senha'] = Senha
            DadosLogin['inicializaLoja'] = 1
            # print(DadosLogin)
        else:
            DadosLogin['headerIn']['loja'] = self.config.loja
            DadosLogin['headerIn']['empresa'] = self.config.empresa
            DadosLogin['headerIn']['pdv'] = self.pdv
            chave = self.config.chave.encode()  # transforma a chave armazenada no arquivo em bytes
            senha = Senha.encode()  # transforma a senha em bytes
            cripto = Fernet(chave)
            senhaCriptoBytes = cripto.encrypt(senha)  # criptografa senha, o resultado é em bytes
            senhaCriptoChar = senhaCriptoBytes.decode()  # transforma a senha em bytes para string, para poder enviar
            # via JSON
            DadosLogin['senha'] = senhaCriptoChar
            DadosLogin['inicializaLoja'] = 0

        DadosLogin['usuario'] = Usuario
        DadosLogin['headerIn']['transação'] = 'Login'

        self.EnviaRecebeMsgServer('entrar', DadosLogin)

        '''self.finished = False
        while not self.finished:
            self.app.show_alert_dialog("Aguarde. Em preocessamento", 2)
            self.response.wait()
            self.app.close_dialog()'''

        if not self.statusComunic:
            self.QMessageBox(
                0,
                "SuperPOS",
                f"Erro no acesso ao servidor - {self.erroComunic}",
            )
            return False

        if self.buffer_receb_servidor['headerOut']['codErro'] != 0:
            self.QMessageBox(
                0,
                "SuperPOS",
                self.buffer_receb_servidor['headerOut']['mensagem'],
            )
            return False
        elif DadosLogin['inicializaLoja'] == 0:  # usuário OK e loja já inicializada
            self.loja = self.config.loja
            self.empresa = self.config.empresa
            self.perfilUsuario = self.buffer_receb_servidor['perfil']
            settings.EMAIL_HOST_USER = self.buffer_receb_servidor['email']
            settings.EMAIL_HOST_PASSWORD = self.buffer_receb_servidor['pass']
            settings.DEFAULT_FROM_EMAIL = self.buffer_receb_servidor['email']
            settings.SERVER_EMAIL = self.buffer_receb_servidor['email']
            self.NomeUsuarioAtivo = Usuario
            self.ConectaPinPad()
            return True
        elif DadosLogin['inicializaLoja'] == 1 and self.buffer_receb_servidor['perfil'] == 3:
            """ Loja não inicializada e usuário é gerente """

            messagebox = self.QMessageBox(
                1,
                "SuperPOS",
                f"POS ainda não inicializado. Deseja faze-lo ?",
            )
            if not messagebox:
                return False
            else:
                # chaveCripto = bytes(self.buffer_receb_servidor['chave'])
                self.config.inicializaLoja(self.buffer_receb_servidor['loja'],
                                           self.buffer_receb_servidor['empresa'],
                                           self.buffer_receb_servidor['codPDV'],
                                           self.buffer_receb_servidor['chave']
                                           )
                self.loja = self.buffer_receb_servidor['loja']
                self.empresa = self.buffer_receb_servidor['empresa']
                self.perfilUsuario = self.buffer_receb_servidor['perfil']
                settings.EMAIL_HOST_USER = self.buffer_receb_servidor['email']
                settings.EMAIL_HOST_PASSWORD = self.buffer_receb_servidor['pass']
                settings.DEFAULT_FROM_EMAIL = self.buffer_receb_servidor['email']
                settings.SERVER_EMAIL = self.buffer_receb_servidor['email']
                self.NomeUsuarioAtivo = Usuario
                self.ConectaPinPad()
                return True
        else:
            self.QMessageBox(
                0,
                "SuperPOS",
                "POS ainda não inicializado !!"
            )
            return False

    def InicializaPDV(self):

        """ Inicializa o PDV no servidor TEF:
            1. O PDV deverá ser inicializado uma única vez no servidor.
            2. A inicialização deverá ser feita antes de qualquer transação no PDV
            3. A inicialização só poderá ser feita pelo usuário com perfil de Gerente de Loja

         """

        if not self.config.lerDadosLoja():  # ler os dados da loja, no arquivo local
            self.QMessageBox(
                0,
                "SuperPOS",
                f"Erro no acesso ao arquivo de configuração do POS",
            )
            return False

        DadosInicializaIn['headerIn']['loja'] = self.config.loja
        DadosInicializaIn['headerIn']['empresa'] = self.config.empresa
        DadosInicializaIn['headerIn']['pdv'] = self.pdv
        DadosInicializaIn['usuario'] = self.NomeUsuarioAtivo
        DadosInicializaIn['headerIn']['transação'] = 'InicializaPDV'

        self.EnviaRecebeMsgServer('inicializaPDV', DadosInicializaIn)

        if not self.statusComunic:
            self.QMessageBox(
                0,
                "SuperPOS",
                f"Erro no acesso ao servidor - {self.erroComunic}",
            )
            return False

        if self.buffer_receb_servidor['headerOut']['codErro'] != 0:
            self.QMessageBox(
                0,
                "SuperPOS",
                self.buffer_receb_servidor['headerOut']['mensagem'],
            )
            return False
        else:
            self.QMessageBox(
                0,
                "SuperPOS",
                self.buffer_receb_servidor['headerOut']['mensagem'],
            )
            return True

    def AberturaPDV(self):

        """ Abre o PDV no servidor TEF:
            1. O PDV deverá ser aberto diariamente, antes de qualquer transação financeira.
            2. A abertura só poderá ser feita pelo usuário com perfil de operador de loja
            3. Se abertura OK, habilita as transações no menu, de acordo com as transações habilitadas para o PDV
         """

        if not self.config.lerDadosLoja():  # ler os dados da loja, no arquivo local
            self.QMessageBox(
                0,
                "SimPOS",
                "Erro no acesso ao arquivo de configuração !!"
            )
            return False

        DadosAberturaIn['headerIn']['loja'] = self.config.loja
        DadosAberturaIn['headerIn']['empresa'] = self.config.empresa
        DadosAberturaIn['headerIn']['pdv'] = self.pdv
        DadosAberturaIn['usuario'] = self.NomeUsuarioAtivo
        DadosAberturaIn['headerIn']['transação'] = 'AberturaPDV'

        self.EnviaRecebeMsgServer('aberturaPDV', DadosAberturaIn)

        if not self.statusComunic:
            self.QMessageBox(
                0,
                "SuperPOS",
                f"Erro no acesso ao servidor - {self.erroComunic}",
            )
            return False

        if self.buffer_receb_servidor['headerOut']['codErro'] != 0:
            self.QMessageBox(
                0,
                "SuperPOS",
                self.buffer_receb_servidor['headerOut']['mensagem'],
            )
            return False
        else:
            self.QMessageBox(
                0,
                "SuperPOS",
                self.buffer_receb_servidor['headerOut']['mensagem'],
            )
            return True

    def EnviaMsgVendaCredito(self, DadosVendaCreditoIn):

        """ Termina de montar a msg de venda crédito e envia ao servidor TEF:
            1. Será montado apenas o header da msg. Os outros dados já foram preenchidos pelo chamador
            2. O cartão será criptografado
            3. Se a transação for aprovada, será exibido o comprovante na tela.
            4. Se o usuário der Confirma, a transação será confirmada no servidor, caso contrário será desfeita

         """

        if not self.config.lerDadosLoja():  # ler os dados da loja, no arquivo local
            self.QMessageBox(
                0,
                "SuperPOS",
                "Erro no acesso ao arquivo de configuração !!"
            )
            return False

        DadosVendaCreditoIn['headerIn']['loja'] = self.config.loja
        DadosVendaCreditoIn['headerIn']['empresa'] = self.config.empresa
        DadosVendaCreditoIn['headerIn']['pdv'] = self.pdv
        DadosVendaCreditoIn['usuario'] = self.NomeUsuarioAtivo

        """ Criptografa o número do cartão """
        chave = self.config.chave.encode()  # transforma a chave armazenada no banco, de string p/ bytes
        cartao = DadosVendaCreditoIn['numCartao'].encode()  # transforma o numero do cartão, de string para bytes
        cripto = Fernet(chave)
        cartaoCriptoBytes = cripto.encrypt(cartao)  # criptografa cartão, o resultado é em bytes
        cartaoCriptoChar = cartaoCriptoBytes.decode()  # transforma o cartão criptografado de bytes para string,
        # para poder enviar via JSON
        DadosVendaCreditoIn['numCartao'] = cartaoCriptoChar

        self.EnviaRecebeMsgServer('vendacredito', DadosVendaCreditoIn)

        if not self.statusComunic:
            self.QMessageBox(
                0,
                "SuperPOS",
                f"Erro no acesso ao servidor - {self.erroComunic}",
            )
            return False

        if self.buffer_receb_servidor['headerOut']['codErro'] != 0:
            self.QMessageBox(
                0,
                "SuperPOS",
                self.buffer_receb_servidor['headerOut']['mensagem'],
            )
            return False
        elif self.buffer_receb_servidor['codRespAdiq'] != 0:
            self.QMessageBox(
                0,
                "SimPDV",
                self.buffer_receb_servidor['msgAdiq'],
            )
            return False
        return True

    def EnviaMsgVendaDebito(self, DadosVendaDebitoIn):

        """ Termina de montar a msg de venda débito e envia ao servidor TEF:
            1. Será montaDO apenas o header da msg. Os outros dados já foram preenchidos pelo chamador
            2. O cartão será criptografado
            3. A senha será criptografada
            3. Se a transação for aprovada, será exibido o comprovante na tela.
            4. Se o usuário der Confirma, a transação será confirmada no servidor, caso contrário será desfeita

         """

        if not self.config.lerDadosLoja():  # ler os dados da loja, no arquivo local
            self.QMessageBox(
                0,
                "SuperPOS",
                "Erro no acesso ao arquivo de configuração !!"
            )
            return False

        DadosVendaDebitoIn['headerIn']['loja'] = self.config.loja
        DadosVendaDebitoIn['headerIn']['empresa'] = self.config.empresa
        DadosVendaDebitoIn['headerIn']['pdv'] = self.pdv
        DadosVendaDebitoIn['usuario'] = self.NomeUsuarioAtivo

        """ Criptografa o número do cartão """
        chave = self.config.chave.encode()  # transforma a chave armazenada no banco, de string p/ bytes
        cartao = DadosVendaDebitoIn['numCartao'].encode()  # transforma o numero do cartão, de string para bytes
        cripto = Fernet(chave)
        cartaoCriptoBytes = cripto.encrypt(cartao)  # criptografa cartão, o resultado é em bytes
        cartaoCriptoChar = cartaoCriptoBytes.decode()  # transforma o cartão criptografado de bytes para string,
        # para poder enviar via JSON
        DadosVendaDebitoIn['numCartao'] = cartaoCriptoChar

        """ Criptografa a senha """
        chave = self.config.chave.encode()  # transforma a chave armazenada no banco, de string p/ bytes
        senha = DadosVendaDebitoIn['senha'].encode()  # transforma o numero do cartão, de string para bytes
        cripto = Fernet(chave)
        senhaCriptoBytes = cripto.encrypt(senha)  # criptografa cartão, o resultado é em bytes
        senhaCriptoChar = senhaCriptoBytes.decode()  # transforma o cartão criptografado de bytes para string,
        # para poder enviar via JSON
        DadosVendaDebitoIn['senha'] = senhaCriptoChar

        self.EnviaRecebeMsgServer('vendadebito', DadosVendaDebitoIn)

        if not self.statusComunic:
            self.QMessageBox(
                0,
                "SuperPOS",
                f"Erro no acesso ao servidor - {self.erroComunic}",
            )
            return False

        if self.buffer_receb_servidor['headerOut']['codErro'] != 0:
            self.QMessageBox(
                0,
                "SuperPOS",
                self.buffer_receb_servidor['headerOut']['mensagem'],
            )
            self.msg_erro_pin = self.buffer_receb_servidor['headerOut']['mensagem']
            return False
        elif self.buffer_receb_servidor['codRespAdiq'] != 0:
            self.QMessageBox(
                0,
                "SimPDV",
                self.buffer_receb_servidor['msgAdiq'],
            )
            self.msg_erro_pin = self.buffer_receb_servidor['msgAdiq']
            return False
        return True

    def EnviaMsgConfirmaDesfaz(self, DadosConfirmacao, oper):

        """ Termina de montar a msg de venda crédito e envia ao servidor TEF:
            1. Será monta apenas o header da msg. Os outros dados já foram preenchidos pelo chamador
            2. O cartão será criptografado
            3. Se a transação for aprovada, será exibido o comprovante na tela.
            4. Se o usuário der Confirma, a transação será confirmada no servidor, caso contrário será desfeita

         """

        if not self.config.lerDadosLoja():  # ler os dados da loja, no arquivo local
            self.QMessageBox(
                0,
                "SuperPOS",
                "Erro no acesso ao arquivo de configuração !!"
            )
            return False

        DadosConfirmacao['headerIn']['loja'] = self.config.loja
        DadosConfirmacao['headerIn']['empresa'] = self.config.empresa
        DadosConfirmacao['headerIn']['pdv'] = self.pdv
        DadosConfirmacao['headerIn']['transação'] = oper
        DadosConfirmacao['usuario'] = self.NomeUsuarioAtivo
        DadosConfirmacao['NSU_Original'] = self.buffer_receb_servidor['NSU_TEF']
        DadosConfirmacao['dataHoraOriginal'] = self.buffer_receb_servidor['dataHoraTrans']

        self.EnviaRecebeMsgServer('confirmadesfaz', DadosConfirmacao)

        if not self.statusComunic:
            self.QMessageBox(
                0,
                "SuperPOS",
                f"Erro no acesso ao servidor - {self.erroComunic}",
            )
            return False

        if self.buffer_receb_servidor['headerOut']['codErro'] != 0:
            self.QMessageBox(
                0,
                "SuperPOS",
                self.buffer_receb_servidor['headerOut']['mensagem'],
            )
            return False
        elif self.buffer_receb_servidor['codRespAdiq'] != 0:
            self.QMessageBox(
                0,
                "SimPDV",
                self.buffer_receb_servidor['msgAdiq'],
            )
            return False
        return True

    def EnviaMsgPesqNSU(self, DadosPesqLog):

        """ Termina de montar a msg de pesquisa de transações e envia ao servidor TEF:
            1. Será montaDO apenas o header da msg. Os outros dados já foram preenchidos pelo chamador

         """

        if not self.config.lerDadosLoja():  # ler os dados da loja, no arquivo local
            self.QMessageBox(
                0,
                "SuperPOS",
                "Erro no acesso ao arquivo de configuração !!"
            )
            return False

        DadosPesqLog['headerIn']['loja'] = self.config.loja
        DadosPesqLog['headerIn']['empresa'] = self.config.empresa
        DadosPesqLog['usuario'] = self.NomeUsuarioAtivo

        self.EnviaRecebeMsgServer('pesqtranslog', DadosPesqLog)

        if not self.statusComunic:
            self.QMessageBox(
                0,
                "SuperPOS",
                f"Erro no acesso ao servidor - {self.erroComunic}",
            )
            return False

        """ Verifica se pelo menos o header faz parte da msg recebida. 
            No caso desta API, se não houver erro, o servidor envia a msg no lay out de serializer, 
            que contem somente os dados de cada registro do Log, sem header 
        """

        if 'headerOut' in self.buffer_receb_servidor:  # ocorreu algum erro
            if self.buffer_receb_servidor['headerOut']['codErro'] != 0:
                self.QMessageBox(
                    0,
                    "SuperPOS",
                    self.buffer_receb_servidor['headerOut']['mensagem'],
                )
                return False
        else:  # Trans. OK -> o registro da NSU a cancelar está em self.buffer_receb_servidor
            return True

    def EnviaMsgCancelamento(self, DadosCancelamento):

        """ Termina de montar a msg de cancelamento e envia ao servidor TEF:
            1. Será montado apenas o header da msg. Os outros dados já foram preenchidos pelo chamador
            2. A senha do supervisor será criptografada
            3. Se a transação for aprovada, será exibido o comprovante na tela.
            4. Se o usuário der Confirma, a transação será confirmada no servidor, caso contrário será desfeita

         """

        if not self.config.lerDadosLoja():  # ler os dados da loja, no arquivo local
            self.QMessageBox(
                0,
                "SuperPOS",
                "Erro no acesso ao arquivo de configuração !!"
            )
            return False

        DadosCancelamento['headerIn']['loja'] = self.config.loja
        DadosCancelamento['headerIn']['empresa'] = self.config.empresa
        DadosCancelamento['headerIn']['pdv'] = self.pdv
        DadosCancelamento['usuario'] = self.NomeUsuarioAtivo

        self.EnviaRecebeMsgServer('cancelamento', DadosCancelamento)

        if not self.statusComunic:
            self.QMessageBox(
                0,
                "SuperPOS",
                f"Erro no acesso ao servidor - {self.erroComunic}",
            )
            return False

        if self.buffer_receb_servidor['headerOut']['codErro'] != 0:
            self.QMessageBox(
                0,
                "SuperPOS",
                self.buffer_receb_servidor['headerOut']['mensagem'],
            )
            return False
        elif self.buffer_receb_servidor['codRespAdiq'] != 0:
            self.QMessageBox(
                0,
                "SimPDV",
                self.buffer_receb_servidor['msgAdiq'],
            )
            return False
        return True

    def EnviaMsgPesqLog(self, DadosPesqLog):

        """ Termina de montar a msg de pesquisa de transações do Log,
            para o relatório de transações, e envia ao servidor TEF:
            1. Será montaDO apenas o header da msg. Os outros dados já foram preenchidos pelo chamador

         """

        if not self.config.lerDadosLoja():  # ler os dados da loja, no arquivo local
            self.QMessageBox(
                0,
                "SuperPOS",
                "Erro no acesso ao arquivo de configuração !!"
            )
            return False

        DadosPesqLog['headerIn']['loja'] = self.config.loja
        DadosPesqLog['headerIn']['empresa'] = self.config.empresa
        DadosPesqLog['usuario'] = self.NomeUsuarioAtivo

        self.EnviaRecebeMsgServer('pesqtranslog', DadosPesqLog)

        if not self.statusComunic:
            self.QMessageBox(
                0,
                "SuperPOS",
                f"Erro no acesso ao servidor - {self.erroComunic}",
            )
            return False

        """ Verifica se pelo menos o header faz parte da msg recebida. 
            No caso desta API, se não houver erro, o servidor envia a msg no lay out de serializer, 
            que contem somente os dados de cada registro do Log, sem header 
            """
        if 'headerOut' in self.buffer_receb_servidor:
            """ O Header está presente na msg, significa que ocorreu algum erro """
            if self.buffer_receb_servidor['headerOut']['codErro'] != 0:
                self.QMessageBox(
                    0,
                    "SuperPOS",
                    self.buffer_receb_servidor['headerOut']['mensagem'],
                )
                return False
        else:  # Trans. OK -> os registros do Log estão em self.buffer_receb_servidor
            return True

    def EnviaRecebeMsgServer(self, Transacao, buffer):

        """ Envia e recebe a mensagem para o servidor de TEF
         """

        enderecoUrl = f"{self.URL}v1/{Transacao}"
        headers = {'Content-type': 'application/json'}
        buffer_json = json.dumps(buffer)

        Clock.start_clock()

        self.response = UrlRequest(enderecoUrl,
                                   on_success=self.msg_ok,
                                   on_error=self.msg_erro,
                                   on_failure=self.msg_erro,
                                   req_body=buffer_json,
                                   req_headers=headers,
                                   timeout=40,
                                   method='PUT'
                                   )

        while not self.response.is_finished:
            sleep(1)
            Clock.tick()

        Clock.stop_clock()

        return

    def EnviaEmail(self, mensagem, endereco_email, assunto):

        receiver = [endereco_email]
        send_mail(subject=assunto,
                  message=mensagem,
                  from_email=settings.DEFAULT_FROM_EMAIL,
                  recipient_list=receiver)

    def msg_ok(self, req, result):
        print('Msg OK')
        print(result)
        self.buffer_receb_servidor = result
        self.statusComunic = True
        self.finished = True
        # print(req)

    def msg_erro(self, req, result):

        print(f"Erro no acesso ao servidor - {self.response.resp_status}"
              '')
        self.statusComunic = False
        self.erroComunic = self.response.resp_status
        self.finished = True

    def QMessageBox(self, tipo, title, msg):
        self.app.show_alert_dialog(msg, tipo)
        return self.OK

    """def QMessageBox1(self, tipo, title, msg):
        self.app.callpopup(tipo, title, msg)
        return self.OK"""

    def ConectaPinPad(self):

        HOST = self.IpPinPad  # Endereço do celular Android
        PORT = self.portaPinPad
        print('Criando socket')

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('Vai conectar')
        try:
            s.connect((HOST, PORT))
        except OSError as msg:
            self.QMessageBox(
                0,
                "SuperPOS",
                f"Erro de conexão com o PinPad.\nTransação com cartão de débito desabilitada",
            )
            self.erroPinPad = True
        else:
            self.socketPin = s
            print('Send')
            self.DadosPinPad = f'geralPin Pad conectado\nLoja = {self.loja} ' \
                               f'PDV = {self.pdv}'
            msg = self.DadosPinPad.encode('utf-8')
            self.socketPin.sendall(msg)
            self.erroPinPad = False

    def CalculoDigitoCartao(self, aux_cartao):

        """O DV corresponde ao número que falta  para inteirar como múltiplo de 10 a soma da multiplicação de cada
                algarismo da base por 2, 1, 2, 1, 2, 1, 2, 1, 2, 1… a partir da unidade até o penúltimo.
                Em cada multiplicação com valores acima de 9, faremos a “regra dos 9”. Veja um exemplo:
                o número do cartão é 2231 1234 1200 345X;
                fazendo a multiplicação de cada algarismo pelo número apontado acima, temos como resultado:
                4 + 2 + 6 + 1 + 2 + 2 + 6 + 4 + 2 + 2 + 0 + 0 + 6 +4 +1 = 42;
                Para chegar até o múltiplo de 10 mais próximo, que seria 50, faltam 8.
        """

        tot = 0
        x = 2

        for i in range(0, len(aux_cartao) - 1):
            y = int(aux_cartao[i]) * x
            if y > 9:
                y -= 9
            tot += y
            if x == 2:
                x = 1
            else:
                x = 2
        dig = 10 - int(tot % 10)
        if dig == int(aux_cartao[len(aux_cartao) - 1]):
            return True
        else:
            return False

    def MontaTelaTransacao(self, tela, reg_atual):
        """ Monta tela do registro do log a ser exibido """

        num_cartao = reg_atual['numCartao']
        num_cartao = f'{num_cartao[-4:]:*>{len(num_cartao)}}'
        num_cartao = self.FormataNumCartao (num_cartao)
        tela.num_cartao.text = num_cartao
        tela.nsu_tef.text = str(reg_atual['NSU_TEF'])
        tela.cod_loja.text = str(reg_atual['codLoja'])
        tela.valor.text = str(reg_atual['valorTrans'])
        tela.pdv.text = str(reg_atual['codPDV'])
        tela.transacao.text = reg_atual['codTRN']
        tela.status.text = reg_atual['statusTRN']
        tela.bandeira.text = reg_atual['nomeBan']
        tela.adiq.text = reg_atual['nomeAdiq']
        data_hora = datetime.datetime.fromisoformat(reg_atual['dataHoraHost'])
        data_hora_aux = data_hora.strftime('%d/%m/%Y %H:%M:%S')
        tela.data_hora.text = data_hora_aux

    def FormataNumCartao(self, num_cartao):

        aux = []
        ret = ''
        for i in range(0, len(num_cartao)):
            aux.append(num_cartao[i])
            if (i + 1) % 4 == 0:
                aux.append('.')

        ret = "".join(aux)
        return ret

    def menu_callback(self, text_item):
        """ Callback para a chamada das rotinas do menu Top Bar """
        self.menu_top_bar.dismiss()

        # match text_item OBS.: Não sei porque, o comando Match não funcionou na compilação para Android

        if text_item == 'Sair':
            self.app.sm.current = 'login'
        elif text_item == 'Relatório':
            self.app.sm.current = 'selecionatransacoes'
        elif text_item == 'Abertura':
            self.app.sm.current = 'abertura'
        elif text_item == 'Inicialização':
            self.app.sm.current = 'inicializa'
        elif text_item == 'Cancelamento':
            self.app.sm.current = 'nsucancelamento'
        elif text_item == 'Débito':
            self.app.sm.current = 'debito'
        elif text_item == 'Crédito':
            self.app.sm.current = 'menucredito'

    def callback(self, button):
        """ Callback para a montagem dos itens do menu da Top Bar """
        self.menu_top_bar.caller = button
        self.menu_top_bar.open()

"""Classe para acesso ao arquivo de configuração do PDV"""


class ConfigModel():

    def __init__(self, parent):

        # super().__init__(parent)
        self.parent = parent
        self.loja = 0
        self.empresa = 0
        self.pdv = 0
        self.chave = ''

    def lerDadosLoja(self):
        """Acessa o arquivo de configuração da loja.
           O arquivo é composto de um único registro """

        try:
            config = io.open('config_pos.dat', 'rb', buffering=0)
        except:
            return False

        # reg = config.read()
        # buf = reg.decode()
        reg = pickle.load(config)
        self.loja = reg[0]
        self.empresa = reg[1]
        self.pdv = reg[2]
        self.chave = reg[3]
        return True

    def inicializaLoja(self, loja, empresa, PDV, chave):
        """Cria o registro de configuração da loja"""

        try:
            config = io.open('config_pos.dat', 'wb', buffering=0)
        except:
            self.parent.app.QMessageBox(
                None,
                "SimPDV",
                "Erro no acesso ao arquivo de configuração",
            )
            return False

        reg = []

        reg.append(loja)
        reg.append(empresa)
        reg.append(PDV)
        reg.append(chave)
        # buf = str(reg).encode()
        # status = config.write(buf)
        pickle.dump(reg, config, pickle.HIGHEST_PROTOCOL)
        config.close()

        return True
