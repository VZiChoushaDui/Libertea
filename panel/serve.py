import logging
from waitress import serve
from panel import create_app
from paste.translogger import TransLogger

logger = logging.getLogger('waitress')
logger.setLevel(logging.INFO)

if __name__ == '__main__':
    print('Starting server...')
    serve(TransLogger(create_app(), setup_console_handler=False), 
        host='127.0.0.1', port=1000, threads=10)
