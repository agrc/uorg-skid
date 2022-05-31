#!/usr/bin/env python
# * coding: utf8 *
"""
Run the UORG updater script as a cloud function.
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import arcgis
from palletjack import (
    FeatureServiceAttachmentsUpdater, FeatureServiceInlineUpdater, GoogleDriveDownloader, GSheetLoader
)
from supervisor.message_handlers import SendGridHandler
from supervisor.models import MessageDetails, Supervisor

#: This makes it work when calling with just `python <file>`/installing via pip and in the gcf framework, where
#: the relative imports fail because of how it's calling the function.
try:
    from . import config, version
except ImportError:
    import config
    import version


def _get_secrets():
    secret_folder = Path('/secrets')

    #: Try to get the secrets from the Cloud Function mount point
    if secret_folder.exists():
        return json.loads(Path('/secrets/app/secrets.json').read_text(encoding='utf-8'))

    #: Otherwise, try to load a local copy for local development
    secret_folder = (Path(__file__).parent / 'secrets')
    if secret_folder.exists():
        return json.loads((secret_folder / 'secrets.json').read_text(encoding='utf-8'))

    raise FileNotFoundError('Secrets folder not found; secrets not loaded.')


def _initialize(log_path, sendgrid_api_key):

    skid_logger = logging.getLogger('erap')
    skid_logger.setLevel(config.LOG_LEVEL)
    palletjack_logger = logging.getLogger('palletjack')
    palletjack_logger.setLevel(config.LOG_LEVEL)

    cli_handler = logging.StreamHandler(sys.stdout)
    cli_handler.setLevel(config.LOG_LEVEL)
    formatter = logging.Formatter(
        fmt='%(levelname)-7s %(asctime)s %(name)15s:%(lineno)5s %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    )
    cli_handler.setFormatter(formatter)

    log_handler = logging.FileHandler(log_path, mode='w')
    log_handler.setLevel(config.LOG_LEVEL)
    log_handler.setFormatter(formatter)

    skid_logger.addHandler(cli_handler)
    skid_logger.addHandler(log_handler)
    palletjack_logger.addHandler(cli_handler)
    palletjack_logger.addHandler(log_handler)

    #: Log any warnings at logging.WARNING
    #: Put after everything else to prevent creating a duplicate, default formatter
    #: (all log messages were duplicated if put at beginning)
    logging.captureWarnings(True)

    skid_logger.debug('Creating Supervisor object')
    skid_supervisor = Supervisor(handle_errors=False)
    sendgrid_settings = config.SENDGRID_SETTINGS
    sendgrid_settings['api_key'] = sendgrid_api_key
    skid_supervisor.add_message_handler(
        SendGridHandler(sendgrid_settings=sendgrid_settings, client_name='erap', client_version=version.__version__)
    )

    return skid_supervisor


def process():


    #: Set up secrets, tempdir, supervisor, and logging
    start = datetime.now()

    secrets = SimpleNamespace(**_get_secrets())

    tempdir = TemporaryDirectory()
    tempdir_path = Path(tempdir.name)
    log_name = f'{config.LOG_FILE_NAME}_{start.strftime("%Y%m%d-%H%M%S")}.txt'
    log_path = tempdir_path / log_name

    uorg_supervisor = _initialize(log_path, secrets.SENDGRID_API_KEY)
    module_logger = logging.getLogger('uorg')

    #: Get our GIS object via the ArcGIS API for Python
    gis = arcgis.gis.GIS(config.AGOL_ORG, secrets.AGOL_USER, secrets.AGOL_PASSWORD)

    #: Use a GSheetLoader to load the google sheet into a single dataframe with a column denoting year:
    module_logger.info('Loading Google Sheet into a single dataframe...')
    gsheetloader = GSheetLoader(secrets.SERVICE_ACCOUNT_JSON)
    worksheets = gsheetloader.load_all_worksheets_into_dataframes(secrets.SHEET_ID)

    #: Not being able to load the dataframes is a fatal error and should bomb out.
    try:
        all_worksheets_dataframe = gsheetloader.combine_worksheets_into_single_dataframe(worksheets)
    except ValueError as error:
        module_logger.error(error)
        module_logger.error('Unable to load Google Sheet into dataframe. Aborting.')
        raise

    #: Update the feature service attribute values themselves
    module_logger.info('Updating AGOL Feature Service with data from Google Sheets...')
    updater = FeatureServiceInlineUpdater(gis, all_worksheets_dataframe, config.JOIN_COLUMN)
    number_of_rows_updated = updater.update_existing_features_in_hosted_feature_layer(
        config.FEATURE_LAYER_ITEMID, config.FIELDS
    )

    #: Use a GoogleDriveDownloader to download all the pictures from a single worksheet dataframe
    module_logger.info('Downloading attachments from Google Drive...')
    out_dir = tempdir_path / 'pics'
    downloader = GoogleDriveDownloader(out_dir)
    downloaded_dataframe = downloader.download_attachments_from_dataframe(
        all_worksheets_dataframe, config.ATTACHMENT_COLUMN, config.JOIN_COLUMN, 'full_file_path'
    )

    #: Create our attachment updater and update attachments using the attachments dataframe
    module_logger.info('Updating Feature Service attachments using downloaded files...')
    attachments_dataframe = downloaded_dataframe[[config.JOIN_COLUMN, config.ATTACHMENT_COLUMN]] \
                                                .copy().dropna(subset=config.ATTACHMENT_COLUMN)
    attachment_updater = FeatureServiceAttachmentsUpdater(gis)
    overwrites, adds = attachment_updater.update_attachments(
        config.FEATURE_LAYER_ITEMID, config.JOIN_COLUMN, 'full_file_path', attachments_dataframe
    )

    end = datetime.now()

    summary_message = MessageDetails()
    summary_message.subject = 'UORG Update Summary'
    summary_rows = [
        f'UORG update {start.strftime("%Y-%m-%d")}',
        '=' * 20,
        '',
        f'Start time: {start.strftime("%H:%M:%S")}',
        f'End time: {end.strftime("%H:%M:%S")}',
        f'Duration: {str(end-start)}',
        f'{number_of_rows_updated} rows updated',
        f'{overwrites} existing attachments overwritten',
        f'{adds} attachments added where none existed',
    ]
    summary_message.message = '\n'.join(summary_rows)
    summary_message.attachments = tempdir_path / log_name

    uorg_supervisor.notify(summary_message)

    #: Try to clean up the tempdir (we don't use a context manager); log any errors as a heads up
    #: This dir shouldn't persist between cloud function calls, but in case it does, we try to clean it up
    try:
        tempdir.cleanup()
    except Exception as error:
        module_logger.error(error)


def main(event, context):  # pylint: disable=unused-argument
    """Entry point for Google Cloud Function triggered by pub/sub event

    Args:
         event (dict):  The dictionary with data specific to this type of
                        event. The `@type` field maps to
                         `type.googleapis.com/google.pubsub.v1.PubsubMessage`.
                        The `data` field maps to the PubsubMessage data
                        in a base64-encoded string. The `attributes` field maps
                        to the PubsubMessage attributes if any is present.
         context (google.cloud.functions.Context): Metadata of triggering event
                        including `event_id` which maps to the PubsubMessage
                        messageId, `timestamp` which maps to the PubsubMessage
                        publishTime, `event_type` which maps to
                        `google.pubsub.topic.publish`, and `resource` which is
                        a dictionary that describes the service API endpoint
                        pubsub.googleapis.com, the triggering topic's name, and
                        the triggering event type
                        `type.googleapis.com/google.pubsub.v1.PubsubMessage`.
    Returns:
        None. The output is written to Cloud Logging.
    """

    process()


if __name__ == '__main__':
    process()
