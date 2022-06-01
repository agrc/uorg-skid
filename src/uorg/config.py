"""
config.py: Configuration values. Secrets to be handled with Secrets Manager
"""

import logging
import socket

AGOL_ORG = 'https://utah.maps.arcgis.com'
SENDGRID_SETTINGS = {  #: Settings for SendGridHandler
    # 'api_key':
    'from_address': 'noreply@utah.gov',
    'to_addresses': 'jdadams@utah.gov',
    'prefix': f'UORG on {socket.gethostname()}: ',
}
LOG_LEVEL = logging.DEBUG
LOG_FILE_NAME = 'log'

FEATURE_LAYER_ITEMID = 'agol_item_id'
JOIN_COLUMN = 'ID'
ATTACHMENT_COLUMN = 'Picture'
