# type: ignore
# flake8: noqa

# Comando:
# python -c "import string as s;from secrets import SystemRandom as SR;print(''.join(SR().choices(s.ascii_letters + s.digits + s.punctuation, k=64)));"
SECRET_KEY = '312]`ng@~yiTPrvwM%{-4$ITB[Xz#gHBdlw)vY0qJnS<C55;B>>{p@[H3}|>4yB'

# DEBUG DEVE SER False em produção
DEBUG = False

# Seu domínio ou IP devem vir aqui
ALLOWED_HOSTS = [
    '34.39.141.209',
    '127.0.0.1',
    'localhost',
]  # Troque * para seu domínio ou IP

# Config para postgresql
