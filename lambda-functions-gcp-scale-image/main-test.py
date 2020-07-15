import uuid
import main

from mock import MagicMock, patch
from collections import UserDict


@patch('main.Image')
def test_scale_locally(image_mock, capsys):
    image_mock.return_value = image_mock
    image_mock.__enter__.return_value = image_mock
    image_mock.size = (1600, 900)

    filename = str(uuid.uuid4())
    blob = UserDict()
    blob.name = filename
    blob.bucket = UserDict()
    blob.download_to_filename = MagicMock()

    tmpfile = main._scale_locally(blob)
    out, _ = capsys.readouterr()

    assert f'Image {filename} was downloaded to' in out
    assert f'Image was resized' in out
    assert image_mock.resize.called
    image_mock.resize.assert_called_with(800, 450)
    assert image_mock.save.called
    assert 'tmp' in tmpfile


@patch('main.os')
@patch('main.ds')
def test_update_ds(mock_ds, os_mock, capsys):
    bucket = str(uuid.uuid4())

    os_mock.remove = MagicMock()
    os_mock.path = MagicMock()
    os_mock.path.basename = MagicMock(side_effect=(lambda x: x))
    os_mock.getenv = MagicMock(return_value=bucket)

    filename = str(uuid.uuid4())
    converted_filename = f'converted-{filename}'
    entity = UserDict()
    entity.raw_image_key = filename
    query = MagicMock()
    query.fetch.return_value = [entity]
    mock_ds.query.return_value = query

    main._update_ds(filename, converted_filename)
    out, _ = capsys.readouterr()

    entity.converted_image_key = converted_filename
    assert mock_ds.put.called
    mock_ds.put.assert_called_with(entity)
    assert f'Successfully updated entity for {filename} in datastore' in out


@patch('main._scale_locally')
@patch('main._update_ds')
@patch('main.storage_client')
@patch('main.os')
def test_scale_down(os_mock, storage_mock, update_ds_mock, scale_locally_mock, capsys):
    bucket = str(uuid.uuid4())
    os_mock.remove = MagicMock()
    os_mock.path = MagicMock()
    os_mock.path.basename = MagicMock(side_effect=(lambda x: x))
    os_mock.getenv = MagicMock(return_value=bucket)

    filename = str(uuid.uuid4())
    data = {
      'bucket': 'input-bucket',
      'name': filename
    }

    main.scale_down(data, None)
    out, _ = capsys.readouterr()

    assert scale_locally_mock.called
    assert update_ds_mock.called
    assert f'Uploaded file to converted-{filename}' in out
    assert 'Cleaning up' in out
    assert os_mock.remove.called
