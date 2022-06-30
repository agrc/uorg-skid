import pandas as pd
import pytest
from arcgis.features import GeoAccessor, GeoSeriesAccessor
from pandas import testing as tm

from uorg import main


def test_get_secrets_from_gcp_location(mocker):
    mocker.patch('pathlib.Path.exists', return_value=True)
    mocker.patch('pathlib.Path.read_text', return_value='{"foo":"bar"}')

    secrets = main._get_secrets()

    assert secrets == {'foo': 'bar'}


def test_get_secrets_from_local_location(mocker):
    exists_mock = mocker.Mock(side_effect=[False, True])
    mocker.patch('pathlib.Path.exists', new=exists_mock)
    mocker.patch('pathlib.Path.read_text', return_value='{"foo":"bar"}')

    secrets = main._get_secrets()

    assert secrets == {'foo': 'bar'}
    assert exists_mock.call_count == 2


def test_prep_dataframe_for_uploading_renames_fields(mocker):
    mock_df = pd.DataFrame({
        'id': [1, 2],
        'Long': [-111.11, -112.22],
        'Lat': [-113.33, -114.44],
    })

    mock_config = mocker.Mock()
    mock_config.FIELDS = {'id': 'oid'}
    mocker.patch('uorg.main.config', mock_config)

    sdf = main._prep_dataframe_for_uploading(mock_df)

    test_df = pd.DataFrame({
        'oid': [1, 2],
        'Long': [-111.11, -112.22],
        'Lat': [-113.33, -114.44],
    })

    test_sdf = pd.DataFrame.spatial.from_xy(test_df, 'Long', 'Lat')
    tm.assert_frame_equal(test_sdf, sdf)


def test_prep_dataframe_for_uploading_replaces_DMS(mocker):
    mock_df = pd.DataFrame({
        'id': [1, 2],
        'Long': [-111.11, 'W 112 22\' 33"'],
        'Lat': [-113.33, -114.44],
    })

    mock_config = mocker.Mock()
    mock_config.FIELDS = {'id': 'id'}
    mocker.patch('uorg.main.config', mock_config)

    sdf = main._prep_dataframe_for_uploading(mock_df)

    test_df = pd.DataFrame({
        'id': [1, 2],
        'Long': [-111.11, 0],
        'Lat': [-113.33, -114.44],
    })

    test_sdf = pd.DataFrame.spatial.from_xy(test_df, 'Long', 'Lat')
    tm.assert_frame_equal(test_sdf, sdf)


def test_prep_dataframe_for_uploading_errors_on_sdf_creation_failure(mocker):
    mock_df = pd.DataFrame({
        'id': [1, 2],
        'Long': [-111.11, -112.22],
        'Lat': [-113.33, -114.44],
    })

    mock_config = mocker.Mock()
    mock_config.FIELDS = {'id': 'oid'}
    mocker.patch('uorg.main.config', mock_config)
    mocker.patch.object(pd.DataFrame.spatial, 'from_xy', side_effect=KeyError('sdf creation error'))

    with pytest.raises(RuntimeError) as exc_info:
        sdf = main._prep_dataframe_for_uploading(mock_df)

    assert exc_info.value.args[0] == 'Failed to create spatial dataframe'
