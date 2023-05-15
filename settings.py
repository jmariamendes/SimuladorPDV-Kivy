
""" Parâmetros para o envio de e-mail, utilizando Djangomail
    As variáveis serão inicializadas com informações recebidas no Login"""

EMAIL_USE_LOCALTIME = True

# for test
# EMAIL_BACKEND = 'djangomail.backends.console.EmailBackend'

EMAIL_USE_SSL = False
EMAIL_HOST = "smtps.uol.com.br"
EMAIL_PORT = 587
EMAIL_HOST_USER = '*****'
EMAIL_HOST_PASSWORD = '*****'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER
