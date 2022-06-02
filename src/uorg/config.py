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

FEATURE_LAYER_ITEMID = '4d179d4fc3d745dcad0e91bf4e3dc390'
JOIN_COLUMN = 'ID'
ATTACHMENT_COLUMN = 'Picture'
FIELDS = [
    'Year',
    'ID',
    'Project_Title',
    'Organization',
    'County',
    'Long',
    'Lat',
    'Description',
    'Link_to_',
    'Picture',
]
