__version__ = '1.0'

import time

"""              Simulador do PDV em Abdroid 

            - app para simular o PDV em Android 
            
"""
import copy
import datetime
import re
# import threading
from cryptography.fernet import Fernet

from kivymd.app import MDApp
from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.uix.behaviors.focus import FocusBehavior

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDTextButton, MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.list import OneLineAvatarIconListItem
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.menu import MDDropdownMenu

# from kivy.properties import ListProperty
# from kivy.properties import ObjectProperty
# from kivy.clock import Clock

from Rot_Auxiliares import RotinasAuxiliares
from msg_json import DadosVendaCreditoIn, DadosConfirmacao, \
    DadosPesqLog, DadosCancelamento, DadosVendaDebitoIn


# Declara as screens

class MenuScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_enter(self, *args):

        """ Habilita os botões do menu, de acordo com o status da inicialização e das
            transações habilitadas no servidor para este PDV """

        app.rotaux.itens_menu.clear()  # itens do menu da TopBar
        if app.rotaux.statusInic == 1:  # Login efetuado
            self.ids.botao_abertura.disabled = False
            app.rotaux.itens_menu.append("Abertura")
            self.ids.botao_credito.disabled = True
            self.ids.botao_debito.disabled = True
            self.ids.botao_cancel.disabled = True
            self.ids.botao_pix.disabled = True
            if app.rotaux.perfilUsuario == 3:  # usuário é gerente de loja -> habilita a função InicializaPDV
                self.ids.botao_inicializa.disabled = False
                app.rotaux.itens_menu.append("Inicialização")
            else:
                self.ids.botao_inicializa.disabled = True
        elif app.rotaux.statusInic == 2:  # Inicialização efetuada
            self.ids.botao_inicializa.disabled = True
        elif app.rotaux.statusInic == 3:  # Abertura efetuada
            self.ids.botao_abertura.disabled = True
            # self.ids.botao_credito.disabled = not app.rotaux.transHabilitadas['TransDigitado']
            if app.rotaux.transHabilitadas['TransDigitado']:
                self.ids.botao_credito.disabled = False
                app.rotaux.itens_menu.append("Crédito")
            if app.rotaux.transHabilitadas['TransVendaDebito']:
                self.ids.botao_debito.disabled = False
                app.rotaux.itens_menu.append("Débito")
            if app.rotaux.transHabilitadas['TransCancelamento']:
                self.ids.botao_cancel.disabled = False
                app.rotaux.itens_menu.append("Cancelamento")
            # self.ids.botao_debito.disabled = not app.rotaux.transHabilitadas['TransVendaDebito']
            # self.ids.botao_cancel.disabled = not app.rotaux.transHabilitadas['TransCancelamento']

        app.rotaux.itens_menu.append("Relatório")
        app.rotaux.itens_menu.append("Configuração")
        app.rotaux.itens_menu.append("Sair")

        """ Monta o menu Top Bar 
            
            Como os itens do menu não se alteram após o Login e Abertura,
            o menu será definido como variável global e todas as outras telas
            utilizarão as mesmas variveis """

        app.rotaux.dict_menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": i,
                "height": dp(40),
                "on_release": lambda x=i: app.rotaux.menu_callback(x),
            } for i in app.rotaux.itens_menu
        ]

        app.rotaux.menu_top_bar = MDDropdownMenu(
            items=app.rotaux.dict_menu_items,
            width_mult=3,
            background_color='skyblue',
            border_margin=dp(6),
        )

        if platform == 'android':
            self.ids.label_menu.pos_hint = {"center_x": .5, "center_y": .65}
            self.ids.label_menu.font_size = 60
        else:
            self.ids.label_menu.pos_hint = {"center_x": .5, "center_y": .3}


class LoginScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.menu = MenuScreen()

    def on_enter(self, *args):

        """ Inicializa os campos da tela """

        self.ids.username.text = ''
        self.ids.password.text = ''
        self.ids.entra.text = 'Entrar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"
        self.ids.entra.disabled = False

    def login(self):

        # print ('Login')

        if not self.ids.username.text:
            app.show_alert_dialog('Você precisa informar o usuário', 0)
            self.habilita_botoes()
            return

        if not self.ids.password.text:
            app.show_alert_dialog('Você precisa informar a senha', 0)
            self.habilita_botoes()
            return

        usuario = self.ids.username.text
        senha = self.ids.password.text

        if app.rotaux.ValidaUsuarioSenha(usuario, senha):  # Login OK
            app.rotaux.QMessageBox(
                0,
                "SuperPOS",
                app.rotaux.buffer_receb_servidor['headerOut']['mensagem'],
            )

            app.rotaux.statusInic = 1  # login OK
            app.sm.current = 'menu'
        else:
            self.habilita_botoes()
            app.sm.current = 'login'

    def aguarde(self):
        """ Disabilita os botões após o usuário confirmar a transação para evitar que ele
         aperte de novo o botão Confirmar, enquanto o servidor não responde """

        print('Em preocessamento ...')
        self.ids.entra.disabled = True
        self.ids.entra.color = "black"
        self.ids.entra.text = "Aguarde ..."

    def habilita_botoes(self):

        self.ids.entra.disabled = False
        self.ids.entra.text = 'Entrar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"


class InicializaScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.menu = MenuScreen()

    def on_enter(self, *args):
        if app.rotaux.InicializaPDV():
            app.rotaux.statusInic = 2  # inicialização OK

        app.sm.current = 'menu'

    pass


class AberturaScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.menu = MenuScreen()

    def on_enter(self, *args):
        if app.rotaux.AberturaPDV():
            app.rotaux.statusInic = 3  # abertura OK
            app.rotaux.transHabilitadas = copy.copy(app.rotaux.buffer_receb_servidor['TransHabilitadas'])

        app.sm.current = 'menu'


class MenuCreditoScreen(MDScreen):

    def on_enter(self, *args):
        """ Habilita os botões do menu de venda crédito, de acordo com as
            transações habilitadas no servidor para este PDV """

        trans_habilitadas = []

        if app.rotaux.transHabilitadas['TransVendaCreditoVista']:
            self.ids.botao_avista.disabled = False
            trans_habilitadas.append("À vista")
        if app.rotaux.transHabilitadas['TransVendaCreditoParc']:
            self.ids.botao_comjuros.disabled = False
            trans_habilitadas.append("Parc. com juros")
        if app.rotaux.transHabilitadas['TransVendaCreditoSemJuros']:
            self.ids.botao_semjuros.disabled = False
            trans_habilitadas.append("Parc. sem juros")
        trans_habilitadas.append("Voltar")

        """ Monta o menu Top Bar, das transações de crédito habilitadas  """

        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": i,
                "height": dp(40),
                "on_release": lambda x=i: self.menu_callback(x),
            } for i in trans_habilitadas
        ]

        self.menu = MDDropdownMenu(
            items=menu_items,
            width_mult=3,
            background_color='skyblue',
            border_margin=dp(6),
        )

        if platform == 'android':
            self.ids.label_menu.pos_hint = {"center_x": .5, "center_y": .65}
            self.ids.label_menu.font_size = 60
        else:
            self.ids.label_menu.pos_hint = {"center_x": .5, "center_y": .3}

    def callback(self, button):
        """ Callback para a montagem dos itens do menu da Top Bar """
        self.menu.caller = button
        self.menu.open()

    def menu_callback(self, text_item):
        """ Callback para a chamada das rotinas do menu Top Bar """
        self.menu.dismiss()

        # match text_item - OBS.: O comando Match não funcionou na compilação para Android

        if text_item == 'Voltar':
            app.sm.current = 'menu'
        elif text_item == 'À vista':
            app.sm.current = 'credito'
        elif text_item == 'Parc. com juros':
            app.sm.current = 'creditocomjuros'
        elif text_item == 'Parc. sem juros':
            app.sm.current = 'creditosemjuros'


class CreditoScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.menu = MenuScreen()
        self.centavos = False
        self.tam_centavos = 0

    def on_enter(self, *args):
        if self.name == 'credito':
            self.ids.num_parcelas.disabled = True
            self.ids.num_parcelas.disabled_foreground_color = 'lightgray'
            self.ids.num_parcelas.hint_text_color_normal = 'lightgray'
            self.ids.num_parcelas.hint_text_color_focus = 'lightgray'
            self.ids.label_credito.text = "Crédito a vista"
        elif self.name == 'creditocomjuros':
            self.ids.num_parcelas.disabled = False
            self.ids.label_credito.text = "Parcelado com juros"
        else:
            self.ids.num_parcelas.disabled = False
            self.ids.label_credito.text = "Parcelado sem juros"

        """ Inicializa os campos da tela """

        self.ids.num_cartao.text = ''
        self.ids.val_cartao.text = ''
        self.ids.cod_seg.text = ''
        self.ids.valor.text = ''
        self.ids.num_parcelas.text = ''
        self.ids.end_email.text = ''
        self.ids.entra.text = 'Confirmar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"
        self.ids.cancela.background_normal = ""
        self.ids.cancela.background_color = "lightskyblue"
        self.ids.entra.disabled = False
        self.ids.cancela.disabled = False
        self.centavos = False
        self.tam_centavos = 0

        if platform == 'android':
            self.ids.tela_credito.pos_hint = {"center_x": .35, "center_y": .65}
        else:
            self.ids.tela_credito.pos_hint = {"center_x": .5, "center_y": .65}

    def credito(self):

        if not self.ids.num_cartao.text:
            app.show_alert_dialog('Número do cartão inválido', 0)
            self.habilita_botoes()
            return

        if not self.ids.val_cartao.text:
            app.show_alert_dialog('Validade inválida', 0)
            self.habilita_botoes()
            return

        if not self.ids.cod_seg.text:
            app.show_alert_dialog('Código segurança inválido', 0)
            self.habilita_botoes()
            return

        if not self.ids.valor.text:
            app.show_alert_dialog('Valor inválido', 0)
            self.habilita_botoes()
            return

        if not self.ids.num_parcelas.text and \
                self.ids.label_credito.text != "Crédito a vista":
            app.show_alert_dialog('Num. parcelas inválido', 0)
            self.habilita_botoes()
            return

        aux_cartao = re.sub("\.", "", self.ids.num_cartao.text)
        if not app.rotaux.CalculoDigitoCartao(aux_cartao):
            app.rotaux.QMessageBox(
                0,
                "SuperPOS",
                f"Cartão inválido - dígito",
            )
            self.habilita_botoes()
            return

        validade = self.ids.val_cartao.text
        val_cartao = validade[-2:] + '/' + validade[0:2]
        data = f'{datetime.date.today():%y/%m}'
        if data > val_cartao or int(validade[0:2]) == 0 or int(validade[0:2]) > 12:
            app.rotaux.QMessageBox(
                0,
                "SuperPPOS",
                f"Data validade do cartão inválida",
            )
            self.habilita_botoes()
            return

        if self.ids.end_email.text and self.ids.end_email.error:
            app.rotaux.QMessageBox(
                0,
                "SuperPPOS",
                f"E-mail inválido",
            )
            self.habilita_botoes()
            app.rotaux.email_comprovante = ''
            return
        elif self.ids.end_email.text:
            app.rotaux.email_comprovante = self.ids.end_email.text
        else:
            app.rotaux.email_comprovante = ''

        valor = re.sub(",", ".", self.ids.valor.text)
        DadosVendaCreditoIn['numCartao'] = aux_cartao
        DadosVendaCreditoIn['validadeCartao'] = self.ids.val_cartao.text
        DadosVendaCreditoIn['codSeg'] = self.ids.cod_seg.text
        DadosVendaCreditoIn['valorTrans'] = float(valor)

        if self.ids.label_credito.text == "Crédito a vista":
            DadosVendaCreditoIn['numParcelas'] = 0
            DadosVendaCreditoIn['headerIn']['transação'] = 'CredVista'
        elif self.ids.label_credito.text == "Parcelado com juros":
            DadosVendaCreditoIn['numParcelas'] = int(self.ids.num_parcelas.text)
            DadosVendaCreditoIn['headerIn']['transação'] = 'CredParcComJuros'
        else:
            DadosVendaCreditoIn['numParcelas'] = int(self.ids.num_parcelas.text)
            DadosVendaCreditoIn['headerIn']['transação'] = 'CredParc'

        if app.rotaux.EnviaMsgVendaCredito(DadosVendaCreditoIn):
            ''' Transação aprovada, exibe o comprovante na tela  '''
            app.rotaux.QMessageBox(
                0,
                "SuperPOS",
                app.rotaux.buffer_receb_servidor['headerOut']['mensagem'],
            )
            app.sm.current = 'comprovante'
        else:
            self.habilita_botoes()
            return

    def check_validade(self, caracter, undo):
        """ Consiste e formata a data de validade do cartão: MM/YY.
            Retorna a nova substring, e se a string de entrada é válida ou não
            """

        # print(caracter)
        # print(self.ids.val_cartao.text)
        if not caracter.isdecimal() or len(self.ids.val_cartao.text + caracter) > 5:
            return ''
        elif len(self.ids.val_cartao.text + caracter) == 2:
            return caracter + "/"
        else:
            return caracter

    def check_cartao(self, caracter, undo):
        """ Consiste e formata o número do cartão: 9999.9999.9999.9999.
            Retorna a nova substring, e se a string de entrada é válida ou não
            """

        # print(caracter)
        # print(self.ids.num_cartao.text)
        if not caracter.isdecimal() or len(self.ids.num_cartao.text + caracter) > 19:
            return ''
        elif len(self.ids.num_cartao.text + caracter) == 4 or \
                len(self.ids.num_cartao.text + caracter) == 9 or \
                len(self.ids.num_cartao.text + caracter) == 14:
            return caracter + "."
        else:
            return caracter

    def check_codseg(self, caracter, undo):
        """ Consiste o tamanho do código de segurança.
            Retorna a nova substring, e se a string de entrada é válida ou não
            """

        # print(caracter)
        # print(self.ids.num_cartao.text)
        if not caracter.isdecimal() or len(self.ids.cod_seg.text + caracter) > 3:
            return ''
        else:
            return caracter

    def check_valor(self, caracter, undo):
        """ Consiste o valor.
            Retorna a nova substring, e se a string de entrada é válida ou não
            """

        # print(caracter)
        # print(self.ids.num_cartao.text)
        if len(self.ids.valor.text) == 0:
            self.centavos = False
            self.tam_centavos = 0

        if self.centavos and caracter.isdecimal() and self.tam_centavos < 2:
            self.tam_centavos += 1
            return caracter
        elif caracter.isdecimal() \
                and len(self.ids.valor.text + caracter) < 10 \
                and not self.centavos:
            return caracter
        elif caracter == ',' and len(self.ids.valor.text + caracter) < 9:
            self.centavos = True
            return caracter
        else:
            return ''

    def check_parcelas(self, caracter, undo):
        """ Consiste o numero de parcelas.
            Retorna a nova substring, e se a string de entrada é válida ou não
            """

        if not caracter.isdecimal() or len(self.ids.num_parcelas.text + caracter) > 2:
            return ''
        else:
            return caracter

    def aguarde(self):
        """ Disabilita os botões após o usuário confirmar a transação para evitar que ele
         aperte de novo o botão Confirmar, enquanto o servidor não responde """

        print('Em preocessamento ...')
        self.ids.entra.disabled = True
        self.ids.cancela.disabled = True
        self.ids.entra.color = "black"
        self.ids.entra.text = "Aguarde ..."

    def habilita_botoes(self):

        self.ids.entra.disabled = False
        self.ids.cancela.disabled = False
        self.ids.entra.text = 'Confirmar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"


class ComprovanteScreen(MDScreen):

    def __init__(self, prox_tela, **kwargs):
        super().__init__(**kwargs)
        self.prox_tela = prox_tela
        self.menu = MenuScreen()

    def on_enter(self, *args):

        self.ids.entra.text = 'Confirmar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"
        self.ids.cancela.background_normal = ""
        self.ids.cancela.background_color = "lightskyblue"
        self.ids.entra.disabled = False
        self.ids.cancela.disabled = False

        if platform == 'android':
            self.ids.label_comprovante.font_size = 35
            self.ids.label_comprovante.pos_hint = {"center_x": .6, "center_y": .65}
            self.ids.botoes.pos_hint = {"center_x": .35, "center_y": .65}
        else:
            self.ids.label_comprovante.font_size = 15
            self.ids.label_comprovante.pos_hint = {"center_x": .8, "center_y": .65}
            self.ids.botoes.pos_hint = {"center_x": .5, "center_y": .65}

        self.ids.label_comprovante.text = app.rotaux.buffer_receb_servidor['cupomTrans']

    def confirma_trans(self):

        """ Confirma a transação no servidor TEF (3a. perna) e envia o comprovante por e-mail,
            caso tenha sido informado """

        if app.rotaux.email_comprovante:
            """ Envia o e-mail antes da confirmação, pois o buffer de resposta com o comprovante
                será utilizado no resposta da msg de confirmação 
                """
            app.rotaux.EnviaEmail(app.rotaux.buffer_receb_servidor['cupomTrans'],
                                  app.rotaux.email_comprovante,
                                  'SuperTEF - Comprovante de pagamento')

        app.rotaux.EnviaMsgConfirmaDesfaz(DadosConfirmacao, 'Confirma')

        app.sm.current = self.prox_tela
        # app.sm.current = 'menucredito'

    def cancela_trans(self):

        """ Cancela a transação no servidor TEF (3a. perna/dezfazimento)
        """

        app.rotaux.EnviaMsgConfirmaDesfaz(DadosConfirmacao, 'Desfazimento')
        app.sm.current = 'menucredito'

    def aguarde_confirmacao(self):
        """ Disabilita os botões após o usuário confirmar a transação para evitar que ele
         aperte de novo o botão Confirmar, enquanto o servidor não responde """

        print('Em preocessamento ...')
        self.ids.entra.disabled = True
        self.ids.cancela.disabled = True
        self.ids.entra.color = "black"
        self.ids.entra.text = "Aguarde ..."

    def aguarde_cancelamento(self):
        """ Disabilita os botões após o usuário cancelar a transação para evitar que ele
         aperte de novo o botão Cancelar, enquanto o servidor não responde """

        print('Em preocessamento ...')
        self.ids.entra.disabled = True
        self.ids.cancela.disabled = True
        self.ids.cancela.color = "black"
        self.ids.cancela.text = "Aguarde ..."


class DebitoScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.menu = MenuScreen()
        self.centavos = False
        self.tam_centavos = 0
        self.msg_pin_OK = False

    def on_enter(self, *args):

        """ Inicializa os campos da tela """

        self.ids.num_cartao.text = ''
        self.ids.valor.text = ''
        self.ids.entra.text = 'Confirmar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"
        self.ids.cancela.background_normal = ""
        self.ids.cancela.background_color = "lightskyblue"
        self.ids.entra.disabled = False
        self.ids.cancela.disabled = False
        self.centavos = False
        self.tam_centavos = 0

        if platform == 'android':
            self.ids.tela_debito.pos_hint = {"center_x": .35, "center_y": .65}
        else:
            self.ids.tela_debito.pos_hint = {"center_x": .5, "center_y": .65}

    def debito(self):

        if not self.ids.valor.text:
            app.show_alert_dialog('Valor inválido', 0)
            self.habilita_botoes()
            return

        valor = re.sub(",", ".", self.ids.valor.text)
        DadosVendaDebitoIn['valorTrans'] = float(valor)

        ''' Pede para o cliente informar o número do cartão e a senha no PinPad'''

        """app.rotaux.QMessageBox1(
            0,
            "SuperPOS",
            "Solicite a digitação do cartão no Pin Pad",
        )"""

        self.msg_pin_OK = False
        app.rotaux.DadosPinPad = f'card Digite o número do cartão\nValor={self.ids.valor.text} - Débito'
        msg = app.rotaux.DadosPinPad.encode('utf-8')
        try:
            app.rotaux.socketPin.sendall(msg)
            cartao = bytes(app.rotaux.socketPin.recv(1024))
        except:
            app.rotaux.QMessageBox(
                0,
                "Erro!",
                f"Erro de comunicação com o PinPad.",
            )
            app.rotaux.erroPinPad = True
            self.msg_pin_OK = True
            self.data = None
            self.habilita_botoes()
            return
        else:
            cartao = cartao.decode()
            print('Cartao = ', repr(cartao))
            if cartao == 'Anula':
                app.rotaux.QMessageBox(
                    0,
                    "Atenção!",
                    f"O cliente anulou a transação",
                )
                self.data = None
                self.msg_pin_OK = True
                self.habilita_botoes()
                return

        self.ids.num_cartao.text = cartao
        aux_cartao = re.sub("\.", "", self.ids.num_cartao.text)
        if not app.rotaux.CalculoDigitoCartao(aux_cartao):
            app.rotaux.QMessageBox(
                0,
                "SuperPOS",
                f"Cartão inválido - dígito",
            )
            self.habilita_botoes()
            self.msg_pin_OK = True
            return

        DadosVendaDebitoIn['numCartao'] = aux_cartao

        """app.rotaux.QMessageBox(
                0,
                "SuperPOS",
                "Solicite a digitação da senha no Pin Pad",
        )"""

        app.rotaux.DadosPinPad = f'senhaDigite a senha\nValor={self.ids.valor.text} - Debito'
        msg = app.rotaux.DadosPinPad.encode('utf-8')
        try:
            app.rotaux.socketPin.sendall(msg)
            senha = bytes(app.rotaux.socketPin.recv(1024))
        except:
            app.rotaux.QMessageBox(
                0,
                "Erro!",
                f"Erro de comunicação com o PinPad.",
            )
            app.rotaux.erroPinPad = True
            self.msg_pin_OK = True
            self.data = None
            self.habilita_botoes()
            return
        else:
            senha = senha.decode()
            print('Senha = ', repr(senha))
            if senha == 'Anula':
                app.rotaux.QMessageBox(
                    0,
                    "Atenção!",
                    f"O cliente anulou a transação",
                )
                self.data = None
                self.msg_pin_OK = True
                self.habilita_botoes()
                return

            DadosVendaDebitoIn['senha'] = senha
            self.msg_pin_OK = True

        app.rotaux.QMessageBox(
            2,
            "SuperPOS",
            "Aguarde. Em processamento...",
        )

        if app.rotaux.EnviaMsgVendaDebito(DadosVendaDebitoIn):
            ''' Transação aprovada, exibe o comprovante na tela  '''
            app.rotaux.QMessageBox(
                0,
                "SuperPOS",
                app.rotaux.buffer_receb_servidor['headerOut']['mensagem'],
            )
            app.rotaux.DadosPinPad = f"aviso{app.rotaux.buffer_receb_servidor['headerOut']['mensagem']}"
            msg = app.rotaux.DadosPinPad.encode('utf-8')
            try:
                app.rotaux.socketPin.sendall(msg)
            except:
                app.rotaux.QMessageBox(
                    0,
                    "Erro!",
                    f"Erro de comunicação com o PinPad.",
                )
                app.rotaux.erroPinPad = True
            app.sm.current = 'comprovantedebito'
        else:
            app.rotaux.DadosPinPad = f"aviso{app.rotaux.msg_erro_pin}"
            msg = app.rotaux.DadosPinPad.encode('utf-8')
            try:
                app.rotaux.socketPin.sendall(msg)
            except:
                app.rotaux.QMessageBox(
                    0,
                    "Erro!",
                    f"Erro de comunicação com o PinPad.",
                )
                app.rotaux.erroPinPad = True

            self.habilita_botoes()
            return

    def check_valor(self, caracter, undo):
        """ Consiste o valor.
            Retorna a nova substring, e se a string de entrada é válida ou não
            """

        # print(caracter)
        # print(self.ids.num_cartao.text)
        if len(self.ids.valor.text) == 0:
            self.centavos = False
            self.tam_centavos = 0

        if self.centavos and caracter.isdecimal() and self.tam_centavos < 2:
            self.tam_centavos += 1
            return caracter
        elif caracter.isdecimal() \
                and len(self.ids.valor.text + caracter) < 10 \
                and not self.centavos:
            return caracter
        elif caracter == ',' and len(self.ids.valor.text + caracter) < 9:
            self.centavos = True
            return caracter
        else:
            return ''

    def aguarde(self):
        """ Disabilita os botões após o usuário confirmar a transação para evitar que ele
         aperte de novo o botão Confirmar, enquanto o servidor não responde """

        print('Em processamento ...')

        app.rotaux.QMessageBox(
            2,
            "SuperPOS",
            "Solicite a digitação do cartão e da senha no Pin Pad",
        )

        # self.evento = Clock.schedule_interval(self.fecha_dialogo, 0.5)

        self.ids.entra.disabled = True
        self.ids.cancela.disabled = True
        self.ids.entra.color = "black"
        self.ids.entra.text = "Aguarde ..."

    def habilita_botoes(self):

        self.ids.entra.disabled = False
        self.ids.cancela.disabled = False
        self.ids.entra.text = 'Confirmar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"

    def fecha_dialogo(self, dt):
        """ Fecha a tela de dialogo, se a senha e cartão já foram lidos no Pin Pad
            A função será chamada a cada 5 segundos """
        print(f'msg pin = {self.msg_pin_OK}')
        print(f'title = {app.dialog.title}')
        if self.msg_pin_OK and app.dialog1.title == "Solicite a digitação do cartão e da senha no Pin Pad":
            app.dialog.dismiss()
            self.msg_pin_OK = False
            # Clock.unschedule(self.evento)


class NsuCancelamentoScreen(MDScreen):
    """ Tela para captura da NSU a ser cancelada.
        Se a NSU for encontrada no Log do servidor, exibe os dados da transação e
        pede a confirmação do cancelamento"""

    def on_enter(self, *args):

        """ Inicializa os campos da tela """

        self.ids.num_nsu.text = ''
        self.ids.entra.text = 'Confirmar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"
        self.ids.cancela.background_normal = ""
        self.ids.cancela.background_color = "lightskyblue"
        self.ids.entra.disabled = False
        self.ids.cancela.disabled = False

        if platform == 'android':
            self.ids.tela_nsu_cancelamento.pos_hint = {"center_x": .35, "center_y": .65}
        else:
            self.ids.tela_nsu_cancelamento.pos_hint = {"center_x": .5, "center_y": .65}

    def nsu_cancelamento(self):

        if not self.ids.num_nsu.text:
            app.show_alert_dialog('NSU inválido', 0)
            self.habilita_botoes()
            return

        DadosPesqLog['NSU'] = int(self.ids.num_nsu.text)

        if app.rotaux.EnviaMsgPesqNSU(DadosPesqLog):
            ''' NSU encontrada. Exibe a tela com os dados para o cancelamento '''
            app.sm.current = 'efetuacancelamento'
        else:
            self.habilita_botoes()
            return

    def aguarde(self):
        """ Disabilita os botões após o usuário confirmar a transação para evitar que ele
         aperte de novo o botão Confirmar, enquanto o servidor não responde """

        print('Em preocessamento ...')
        self.ids.entra.disabled = True
        self.ids.cancela.disabled = True
        self.ids.entra.color = "black"
        self.ids.entra.text = "Aguarde ..."

    def habilita_botoes(self):

        self.ids.entra.disabled = False
        self.ids.cancela.disabled = False
        self.ids.entra.text = 'Confirmar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"


class CancelamentoScreen(MDScreen):
    """ Tela para exibição dos dados da NSU a ser cancelada.
        """

    def on_enter(self, *args):

        """ Exibe a tela com os dados da NSU a ser cancelada """

        app.rotaux.MontaTelaTransacao(self.ids, app.rotaux.buffer_receb_servidor)

        self.ids.entra.text = 'Confirmar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"
        self.ids.cancela.background_normal = ""
        self.ids.cancela.background_color = "lightskyblue"
        self.ids.entra.disabled = False
        self.ids.cancela.disabled = False

        if platform == 'android':
            self.ids.tela_cancelamento.pos_hint = {"center_x": .25, "center_y": .65}
        else:
            self.ids.tela_cancelamento.pos_hint = {"center_x": .45, "center_y": .65}

    def cancelamento(self):

        """ Salva dados do cancelamento """

        app.rotaux.canc_num_cartao = app.rotaux.buffer_receb_servidor['numCartao']
        app.rotaux.canc_nsu_tef = str(app.rotaux.buffer_receb_servidor['NSU_TEF'])
        app.rotaux.canc_valor = app.rotaux.buffer_receb_servidor['valorTrans']
        app.rotaux.canc_data = app.rotaux.buffer_receb_servidor['dataLocal']
        app.rotaux.canc_nsu_host = app.rotaux.buffer_receb_servidor['NSU_HOST']

        app.sm.current = 'autorizacancelamento'


class AutorizaCancelamentoScreen(MDScreen):
    """ Tela para autorização do cancelamento pelo supervisor.
        """

    def on_enter(self, *args):

        """ Exibe a tela com os dados da NSU a ser cancelada """

        num_cartao = app.rotaux.canc_num_cartao
        num_cartao = f'{num_cartao[-4:]:*>{len(num_cartao)}}'
        num_cartao = app.rotaux.FormataNumCartao(num_cartao)
        self.ids.num_cartao.text = num_cartao
        self.ids.nsu_tef.text = app.rotaux.canc_nsu_tef
        self.ids.valor.text = str(app.rotaux.canc_valor)
        self.ids.data.text = app.rotaux.canc_data

        self.ids.supervisor.text = ''
        self.ids.senha.text = ''
        self.ids.entra.text = 'Confirmar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"
        self.ids.cancela.background_normal = ""
        self.ids.cancela.background_color = "lightskyblue"
        self.ids.entra.disabled = False
        self.ids.cancela.disabled = False

        if platform == 'android':
            self.ids.tela_autorizacao.pos_hint = {"center_x": .20, "center_y": .65}
        else:
            self.ids.tela_autorizacao.pos_hint = {"center_x": .45, "center_y": .65}

    def autoriza(self):

        if not self.ids.supervisor.text:
            app.show_alert_dialog('Supervisor inválido', 0)
            self.habilita_botoes()
            return

        if not self.ids.senha.text:
            app.show_alert_dialog('Senha inválida', 0)
            self.habilita_botoes()
            return

        DadosCancelamento['numCartao'] = app.rotaux.canc_num_cartao
        DadosCancelamento['NSU_Original'] = self.ids.nsu_tef.text
        DadosCancelamento['dataOriginal'] = app.rotaux.canc_data
        DadosCancelamento['valorTrans'] = float(self.ids.valor.text)
        DadosCancelamento['NSU_HOST_Original'] = app.rotaux.canc_nsu_host
        DadosCancelamento['supervisor'] = self.ids.supervisor.text

        """ Criptografa a senha do supervisor"""
        app.rotaux.config.lerDadosLoja()
        chave = app.rotaux.config.chave.encode()  # transforma a chave armazenada no banco em bytes
        senha = self.ids.senha.text.encode()  # transforma a senha em bytes
        cripto = Fernet(chave)
        senhaCriptoBytes = cripto.encrypt(senha)  # criptografa senha, o resultado é em bytes
        senhaCriptoChar = senhaCriptoBytes.decode()  # transforma a senha em bytes para string, para poder enviar
        # via JSON
        DadosCancelamento['senha'] = senhaCriptoChar

        if app.rotaux.EnviaMsgCancelamento(DadosCancelamento):
            self.confirma_trans()
            app.rotaux.QMessageBox(
                0,
                "SuperPOS",
                app.rotaux.buffer_receb_servidor['headerOut']['mensagem'],
            )
            app.sm.current = 'menu'
        else:
            self.habilita_botoes()
            return

    def aguarde(self):
        """ Disabilita os botões após o usuário confirmar a transação para evitar que ele
         aperte de novo o botão Confirmar, enquanto o servidor não responde """

        print('Em preocessamento ...')
        self.ids.entra.disabled = True
        self.ids.cancela.disabled = True
        self.ids.entra.color = "black"
        self.ids.entra.text = "Aguarde ..."

    def habilita_botoes(self):

        self.ids.entra.disabled = False
        self.ids.cancela.disabled = False
        self.ids.entra.text = 'Confirmar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"
        self.ids.supervisor.text = ''
        self.ids.senha.text = ''

    def confirma_trans(self):

        """ Confirma a transação no servidor TEF (3a. perna) e envia o comprovante por e-mail,
            caso tenha sido informado """

        if app.rotaux.email_comprovante:
            """ Envia o e-mail antes da confirmação, pois o buffer de resposta com o comprovante
                será utilizado no resposta da msg de confirmação 
                """
            app.rotaux.EnviaEmail(app.rotaux.buffer_receb_servidor['cupomTrans'],
                                  app.rotaux.email_comprovante,
                                  'SuperTEF - Comprovante de pagamento')
            app.rotaux.email_comprovante = ''

        app.rotaux.EnviaMsgConfirmaDesfaz(DadosConfirmacao, 'Confirma')


class SelecaoRelatorioScreen(MDScreen):
    """ Tela para a seleção dos filtros para o relatório:
        - data inicial
        - data final
        - status da transação
        - PDV
    """

    dialog = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.menu = MenuScreen()

    def on_enter(self, *args):

        """ Inicializa os campos da tela """

        data_atual = datetime.date.today().strftime("%d/%m/%Y")
        self.ids.data_inicial.text = data_atual
        self.ids.data_final.text = data_atual
        self.ids.data_inicial.bind(focus=self.seleciona_data)
        self.ids.data_final.bind(focus=self.seleciona_data)
        self.ids.tipo_trans.bind(focus=self.seleciona_status_trans)
        self.ids.tipo_trans.text = 'Todas'
        self.ids.num_pdv.text = str(app.rotaux.pdv)
        self.ids.entra.text = 'Confirmar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"
        self.ids.cancela.background_normal = ""
        self.ids.cancela.background_color = "lightskyblue"
        self.ids.entra.disabled = False
        self.ids.cancela.disabled = False
        self.dialog = None

        if platform == 'android':
            self.ids.tela_selecao.pos_hint = {"center_x": .35, "center_y": .65}
        else:
            self.ids.tela_selecao.pos_hint = {"center_x": .5, "center_y": .65}

    def selecionatransacoes(self):
        """ Valida os campos de entrada da tela
            e faz a pesquisa de transações do Log no servidor TEF """

        if not self.ids.data_inicial.text:
            app.show_alert_dialog('Data inicial inválida', 0)
            self.habilita_botoes()
            return

        if not self.ids.data_final.text:
            app.show_alert_dialog('Data final inválida', 0)
            self.habilita_botoes()
            return

        data_atual = datetime.date.today()
        data_aux = datetime.datetime.strptime(self.ids.data_inicial.text, "%d/%m/%Y")
        data_inicial = datetime.date.isoformat(data_aux)

        if data_inicial > str(data_atual):
            app.show_alert_dialog('Data inicial inválida', 0)
            self.habilita_botoes()
            return

        data_aux = datetime.datetime.strptime(self.ids.data_final.text, "%d/%m/%Y")
        data_final = datetime.date.isoformat(data_aux)

        if data_final > str(data_atual):
            app.show_alert_dialog('Data final inválida', 0)
            self.habilita_botoes()
            return

        if data_inicial > data_final:
            app.show_alert_dialog('Data inicial inválida', 0)
            self.habilita_botoes()
            return

        if not self.ids.tipo_trans.text:
            app.show_alert_dialog('Tipo transação inválido', 0)
            self.habilita_botoes()
            return

        DadosPesqLog['NSU'] = 0
        DadosPesqLog['dataInicial'] = data_inicial
        DadosPesqLog['dataFinal'] = data_final
        DadosPesqLog['statusTrans'] = self.ids.tipo_trans.text
        DadosPesqLog['headerIn']['pdv'] = int(self.ids.num_pdv.text)

        if app.rotaux.EnviaMsgPesqLog(DadosPesqLog):
            ''' Pesquisa OK. Exibe os registros de Log na tela '''
            app.rotaux.QMessageBox(
                0,
                "SuperPOS",
                f"Pesquisa OK",
            )
            app.sm.current = 'relatoriotransacoes'
            return
        else:
            self.habilita_botoes()

    def seleciona_data(self, instance, value):
        """ Exibe o diálogo para a seleção da data """

        if value and instance.hint_text == 'Data inicial':
            # date_dialog = MDDatePicker(input_field_cls=CustomInputField)
            date_dialog = MDDatePicker(max_date=datetime.date(
                datetime.date.today().year,
                datetime.date.today().month,
                datetime.date.today().day,
            ),
                max_year=datetime.date.today().year,
                title_input="Data inicial",
                title="Data inicial"
            )
            date_dialog.bind(on_save=self.on_save, on_cancel=self.on_cancel)
            date_dialog.open()
        elif value and instance.hint_text == 'Data final':
            date_dialog = MDDatePicker(title_input="Data final",
                                       title="Data final",
                                       max_year=datetime.date.today().year,
                                       )
            date_dialog.bind(on_save=self.on_save, on_cancel=self.on_cancel)
            date_dialog.open()

    def on_save(self, instance, value, date_range):
        """ Botão OK da seleção da data """
        data = value.strftime("%d/%m/%Y")
        if instance.title == 'Data inicial':
            self.ids.data_inicial.text = data
        elif instance.title == 'Data final':
            self.ids.data_final.text = data

    def on_cancel(self, instance, value):
        """ Botão Cancel da seleção da data """
        return

    def seleciona_status_trans(self, instance, value):
        """ Exibe o diálogo para a seleção do tipo de transação """
        if not self.dialog:
            self.dialog = MDDialog(
                title="Selecione o tipo de transação",
                md_bg_color='lightskyblue',
                type="confirmation",
                items=[
                    ItemConfirm(text="Todas"),
                    ItemConfirm(text="Efetuada"),
                    ItemConfirm(text="Negada"),
                    ItemConfirm(text="Cancelada"),
                    ItemConfirm(text="Desfeita"),
                    ItemConfirm(text="Pendente"),
                    ItemConfirm(text="TimeOut"),
                ],
                buttons=[
                    MDFlatButton(
                        text="Cancela",
                        theme_text_color="Custom",
                        text_color="black",
                        md_bg_color='deepskyblue',
                        # theme_text_color="Custom",
                        on_release=self.botaoCancela,
                    ),
                    MDFlatButton(
                        text="Confirma",
                        theme_text_color="Custom",
                        text_color="black",
                        md_bg_color='dodgerblue',
                        on_release=self.botaoConfirma
                    ),
                ],
            )
        self.dialog.open()

    def botaoCancela(self, instance):
        if self.dialog:
            self.ids.tipo_trans.text = ''
            self.dialog.dismiss()
        return

    def botaoConfirma(self, instance):
        if self.dialog:
            self.ids.tipo_trans.text = app.rotaux.opcao
            self.dialog.dismiss()
        return

    def aguarde(self):
        """ Disabilita os botões após o usuário confirmar a transação para evitar que ele
         aperte de novo o botão Confirmar, enquanto o servidor não responde """

        print('Em preocessamento ...')
        self.ids.entra.disabled = True
        self.ids.cancela.disabled = True
        self.ids.entra.color = "black"
        self.ids.entra.text = "Aguarde ..."

    def habilita_botoes(self):

        self.ids.entra.disabled = False
        self.ids.cancela.disabled = False
        self.ids.entra.text = 'Confirmar'
        self.ids.entra.background_color = "dodgerblue"
        self.ids.entra.background_normal = ""
        self.ids.entra.color = "white"


class ItemConfirm(OneLineAvatarIconListItem):
    """ Salva a opção escolhida no diálogo de tipo de transação """

    def set_option(self, option):
        app.rotaux.opcao = option

    """divider = None

    def set_icon(self, instance_check):
        instance_check.active = True
        check_list = instance_check.get_widgets(instance_check.group)
        for check in check_list:
            if check != instance_check:
                check.active = False"""


class RelatorioTransacoesScreen(MDScreen):
    """ Tela para a exibição do relatório das transações selecionadas em SelecaoRelatorioScreen:

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.botao = None
        self.menu = MenuScreen()

    def on_enter(self, *args):
        """ Exibe a tela com o resultado da pesquisa de transações """

        if platform == 'android':
            self.ids.label_menu.pos_hint = {"center_x": .6, "center_y": .60}
            self.ids.label_menu.font_size = 55
        else:
            self.ids.label_menu.pos_hint = {"center_x": .5, "center_y": .6}

        """ Monta o header do relatório """

        self.data_tables = MDDataTable(
            size_hint=(None, None),
            # size=(400,350),
            use_pagination=True,
            check=True,
            pagination_menu_height='240dp',
            background_color_header='dodgerblue',
            background_color_cell='lightskyblue',
            column_data=[
                ("NSU", dp(25)),
                ("Data/Hora", dp(35)),
                ("Valor", dp(15)),
            ],
        )

        if platform == 'android':
            self.data_tables.size = (850, 800)
        else:
            self.data_tables.size = (400, 350)

        # self.data_tables.bind(on_row_press=self.detalhe_reg)
        self.data_tables.bind(on_check_press=self.detalhe_reg)
        self.ids.tela_relat.add_widget(self.data_tables)

        dados = []
        aux = []

        """ Exibe os registros selecionados """
        for reg in app.rotaux.buffer_receb_servidor:
            dados.append(str(reg["NSU_TEF"]))
            data_hora = datetime.datetime.fromisoformat(reg['dataHoraHost'])
            data_hora_aux = data_hora.strftime('%d/%m/%Y %H:%M:%S')
            dados.append(data_hora_aux)
            dados.append(str(reg["valorTrans"]))
            aux = copy.copy(dados)  # precisa fazer o copy para uma outra,
            # porque o add_row adiciona o endereço e não os dados.
            # Se for o mesmo endereço ele vai duplicar o mesmo registro

            self.data_tables.add_row(aux)
            dados.clear()

        if self.botao not in self.ids.tela_trans.children:
            self.botao = Button(text='Voltar',
                                background_normal='',
                                background_color='dodgerblue',
                                pos_hint={"center_x": .5, "center_y": .3},
                                # pos_hint=(None, None),
                                size_hint=(None, None),
                                size=(300, 100),
                                on_release=self.voltar
                                )
            self.ids.tela_trans.add_widget(self.botao)

    def detalhe_reg(self, instance_table, current_row):
        """ Chama a tela para exibição dos detalhes de uma transação selecionada no check box"""

        # print(instance_table)
        print(current_row)

        for app.rotaux.reg_atual in app.rotaux.buffer_receb_servidor:
            if app.rotaux.reg_atual["NSU_TEF"] == int(current_row[0]):
                app.sm.current = 'detalhetransacao'
                break

    def voltar(self, instance):
        app.sm.current = 'menu'


class DetalheTransacaoScreen(MDScreen):
    """ Tela para exibição dos detalhes de uma transação selecionada.
        """

    def on_enter(self, *args):

        """ Exibe a tela com os dados da transação """

        app.rotaux.MontaTelaTransacao(self.ids, app.rotaux.reg_atual)

        if platform == 'android':
            self.ids.tela_relatorio.pos_hint = {"center_x": .25, "center_y": .65}
        else:
            self.ids.tela_relatorio.pos_hint = {"center_x": .45, "center_y": .65}


class DialogContent(MDBoxLayout):
    # class DialogContent(ModalView):
    """ Dialogo para as mensagens"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class DialogOKCancel(MDBoxLayout):
    # class DialogOKCancel(ModalView):
    """ Dialogo para as mensagens"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class DialogMsg(MDBoxLayout):
    # class DialogOKCancel(ModalView):
    """ Dialogo para as mensagens"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MainApp(MDApp):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.modal = None
        self.rotaux = RotinasAuxiliares(self)

        """ Desabilita o teclado, para que a inicialização no Android seja mais rápida
            O teclado será habilitado após o on_build """

        # FocusBehavior.keyboard_mode = 'managed'
        # FocusBehavior.hide_keyboard(self.root)

    dialog = None

    def build(self):

        # Create the screen manager
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        self.sm = MDScreenManager()
        self.sm.add_widget(LoginScreen(name='login'))
        self.sm.add_widget(InicializaScreen(name='inicializa'))
        self.sm.add_widget(AberturaScreen(name='abertura'))
        self.sm.add_widget(MenuScreen(name='menu'))
        self.sm.add_widget(MenuCreditoScreen(name='menucredito'))
        self.sm.add_widget(CreditoScreen(name='credito'))
        self.sm.add_widget(CreditoScreen(name='creditosemjuros'))
        self.sm.add_widget(CreditoScreen(name='creditocomjuros'))
        self.sm.add_widget(ComprovanteScreen(name='comprovante', prox_tela='menucredito'))
        self.sm.add_widget(ComprovanteScreen(name='comprovantedebito', prox_tela='menu'))
        self.sm.add_widget(NsuCancelamentoScreen(name='nsucancelamento'))
        self.sm.add_widget(CancelamentoScreen(name='efetuacancelamento'))
        self.sm.add_widget(AutorizaCancelamentoScreen(name='autorizacancelamento'))
        self.sm.add_widget(DebitoScreen(name='debito'))
        self.sm.add_widget(SelecaoRelatorioScreen(name='selecionatransacoes'))
        self.sm.add_widget(RelatorioTransacoesScreen(name='relatoriotransacoes'))
        self.sm.add_widget(DetalheTransacaoScreen(name='detalhetransacao'))
        Window.softinput_mode = 'below_target'

        """ Habilita o teclado. Por um bug do Kivy, talvez, nesta forma os campos que
            tem o atributo focus=True não irão funcionar """
        # FocusBehavior.keyboard_mode = 'auto'

        # Window.keyboard_anim_args = {'d': 0.2, 't': 'in_out_expo'}
        # Builder.load_string(KV)

        return self.sm

    def show_alert_dialog(self, msg, tipo):

        if self.dialog is not None:
            self.dialog.dismiss()

        if tipo == 0:  # Informação
            self.dialog = MDDialog(
                title=msg,
                type="custom",
                content_cls=DialogContent(),
            )
            self.dialog.open()
        elif tipo == 1:  # escolha OK/Cancel
            self.dialog = MDDialog(
                title=msg,
                type="custom",
                content_cls=DialogOKCancel(),
            )
            self.dialog.open()
        elif tipo == 2:  # só mensagem
            self.dialog = MDDialog(
                title=msg,
                type="custom",
                content_cls=DialogMsg(),
            )
            self.dialog.open()

        '''if tipo == 0:
            self.modal = DialogContent(auto_dismiss=False, size_hint=(None, None), size=(400, 400))
            # self.modal.bind(on_dismiss=self.my_callback)
            self.modal.open()
        else:
            self.modal = DialogOKCancel(auto_dismiss=False, size_hint=(None, None), size=(400, 400))
            # self.modal.bind(on_dismiss=self.my_callback)
            self.modal.open()'''

    def botaoOK(self):
        self.rotaux.OK = True
        self.dialog.dismiss()

    def botaoCancel(self):
        self.rotaux.OK = False
        self.dialog.dismiss()

    def close_dialog(self, *args):
        self.dialog.dismiss()
        # self.modal.dismiss()

    def close_app(self, *args):
        app.stop()

    """def callpopup(self, tipo, title, msg):

        if tipo == 0:
            dlg = MessageBox(titleheader=title, message=msg, options={"OK": "botaoOK()"})
        elif tipo == 1:
            dlg = MessageBox(titleheader=title, message=msg, options={"OK": "botaoOK()", "Cancel": "botaoCancel()"})
    """


"""class MessageBox(MainApp):

    def __init__(self, titleheader, message, options, **kwargs):

        super().__init__(**kwargs)

        def popup_callback(instance):
            "callback for button press"
            # print('Popup returns:', instance.text)
            self.retvalue = instance.text
            self.popup.dismiss()

        self.retvalue = None
        self.options = options
        box = MDBoxLayout(orientation='vertical')
        box.add_widget(MDLabel(text=message, font_size=20))
        b_list =  []
        buttonbox = MDBoxLayout(orientation='horizontal')
        for b in options:
            b_list.append(Button(text=b, size_hint=(1,.35), font_size=20))
            b_list[-1].bind(on_press=popup_callback)
            buttonbox.add_widget(b_list[-1])
        box.add_widget(buttonbox)
        self.popup = Popup(title=titleheader, content=box, size_hint=(None, None), size=(400, 400))
        self.popup.open()
        self.popup.bind(on_dismiss=self.OnClose)

    def OnClose(self, event):
        self.popup.unbind(on_dismiss=self.OnClose)
        self.popup.dismiss()
        if self.retvalue is not None:
            command = "super(MessageBox, self)."+self.options[self.retvalue]
            # print "command", command
            exec(command)"""

if __name__ == "__main__":
    app = MainApp()

    app.run()
