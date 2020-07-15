import uuid
import main

from mock import MagicMock, patch
from collections import UserDict


@patch('main.publisher')
@patch('main.os')
def test_publish_to_topic(os_mock, publisher_mock, capsys):
    os_mock.environ = {'PROJECT_ID': 'id', 'TOPIC_NAME': 'topic'}
    filename = str(uuid.uuid4())

    main._publish_to_topic("success", filename)

    publisher_mock.publish.assert_called_with(
        publisher_mock.topic_path(),
        data=b"success",
        converted_file_name=filename)


@patch('main.os')
@patch('main.ds')
def test_update_ds_image_text(mock_ds, os_mock, capsys):
    os_mock.remove = MagicMock()
    os_mock.path = MagicMock()
    os_mock.path.basename = MagicMock(side_effect=(lambda x: x))
    os_mock.getenv = MagicMock(return_value=str(uuid.uuid4()))
    texts = ['a', 'b', 'c']

    filename = str(uuid.uuid4())
    entity = UserDict()
    entity.raw_image_key = filename
    entity.exclude_from_indexes = MagicMock()
    query = MagicMock()
    query.fetch.return_value = [entity]
    mock_ds.query.return_value = query

    main._update_ds_image_text(filename, texts)
    out, _ = capsys.readouterr()

    entity.discovered_text = texts
    assert mock_ds.put.called
    assert type(entity.exclude_from_indexes) == set
    mock_ds.put.assert_called_with(entity)
    assert f'Successfully updated entity for {filename} in datastore' in out


@patch('main._publish_to_topic')
@patch('main._update_ds_image_text')
@patch('main.vision_client')
@patch('main.vision')
def test_find_text_unsuccessful(vision_mock, vision_client_mock, update_ds_mock, publish_mock, capsys):
    filename = str(uuid.uuid4())
    data = {
      'bucket': 'input-bucket',
      'name': filename
    }

    response = UserDict()
    vision_client_mock.return_value = response

    main._find_text(data, None)
    out, _ = capsys.readouterr()

    assert 'Looking for text in' in out
    assert vision_client_mock.text_detection.called
    assert 'Error occured' in out
    publish_mock.assert_called_with("unsuccessful", filename)
    assert publish_mock.called


@patch('main._publish_to_topic')
@patch('main._update_ds_image_text')
@patch('main.vision_client')
@patch('main.vision')
def test_find_text_successful(vision_mock, vision_client_mock, update_ds_mock, publish_mock, capsys):
    filename = str(uuid.uuid4())
    data = {
      'bucket': 'input-bucket',
      'name': filename
    }

    response = UserDict()
    msg = UserDict()
    msg.message = None
    response.error = msg
    txt = UserDict()
    txt.description = "A poem"
    response.text_annotations = [txt]
    vision_client_mock.text_detection.return_value = response

    main._find_text(data, None)
    out, _ = capsys.readouterr()

    assert 'Looking for text in' in out
    assert vision_client_mock.text_detection.called
    assert 'Discovered text' in out
    assert txt.description in out
    assert update_ds_mock.called
    publish_mock.assert_called_with("successful", filename)
    assert publish_mock.called