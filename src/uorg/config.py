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

# FEATURE_LAYER_ITEMID = '0f3533d259134cbc916634365db8f07f'  #: Jake's testing
FEATURE_LAYER_ITEMID = '9562dd49165642af86b915533632ce46'  #: Zach's production version
JOIN_COLUMN = 'GrantID'
ATTACHMENT_LINK_COLUMN = 'Picture'
ATTACHMENT_PATH_COLUMN = 'full_file_path'
FIELDS = {
    'worksheet': 'GrantYear',
    'GrantID': 'GrantID',
    'Project Title': 'Project_Title',
    'Organization': 'Organization',
    'County': 'County',
    'Long': 'Long',
    'Lat': 'Lat',
    'Description': 'Description',
    'Link to:': 'Link_to_',
    'Picture': 'Picture',
}
