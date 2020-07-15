import uuid
import main
import base64

from sendgrid.helpers.mail import *
from mock import MagicMock, patch
from collections import UserDict


@patch('main.os')
@patch('main.ds')
def test_get_users_info(mock_ds, os_mock, capsys):
    os_mock.remove = MagicMock()
    os_mock.path = MagicMock()
    os_mock.path.basename = MagicMock(side_effect=(lambda x: x))
    os_mock.getenv = MagicMock(return_value=str(uuid.uuid4()))

    filename = str(uuid.uuid4())
    email = "random@org.com"
    original_image_name = str(uuid.uuid4())
    discovered_text = "a\nb\nc"
    entity = {}
    entity['raw_image_key'] = filename
    entity['user_email'] = email
    entity['original_image_name'] = original_image_name
    entity['discovered_text'] = discovered_text
    query = MagicMock()
    query.fetch.return_value = [entity]
    mock_ds.query.return_value = query

    em, key, name, text = main._get_users_info(filename)
    out, _ = capsys.readouterr()

    assert 'Restoring user info' in out
    assert 'Entity' in out
    assert em == email
    assert key == filename
    assert name == original_image_name
    assert text == discovered_text


@patch('main.os')
@patch('main.storage')
@patch('main._write_creds')
def test_make_presigned_uri(write_creds_mock, storage_mock, os_mock, capsys):
    os_mock.remove = MagicMock()
    os_mock.path = MagicMock()
    os_mock.path.basename = MagicMock(side_effect=(lambda x: x))
    os_mock.getenv = MagicMock(return_value=str(uuid.uuid4()))

    storage_client_mock = MagicMock()
    storage_mock.Client.from_service_account_json.return_value = storage_client_mock

    bucket = str(uuid.uuid4())
    key = str(uuid.uuid4())
    main._make_presigned_uri(bucket, key)

    assert storage_client_mock.bucket.called
    storage_client_mock.bucket.assert_called_with(bucket)
    assert storage_client_mock.bucket.return_value.blob.called
    storage_client_mock.bucket.return_value.blob.assert_called_with(key)
    assert storage_client_mock.bucket.return_value.blob.return_value.generate_signed_url.called


@patch('main.os')
@patch('main._make_presigned_uri')
def test_prepare_message(presigned_mock, os_mock, capsys):
    os_mock.remove = MagicMock()
    os_mock.path = MagicMock()
    os_mock.path.basename = MagicMock(side_effect=(lambda x: x))
    os_mock.getenv = MagicMock(return_value=str(uuid.uuid4()))

    email = "random@org.com"
    success = "success"
    converted_file_name = str(uuid.uuid4())
    raw_key = str(uuid.uuid4())
    original_file_name = str(uuid.uuid4())
    texts = "a\nb\nc\n"

    msg = main._prepare_message(email, success, converted_file_name, raw_key, original_file_name, texts)
    out, _ = capsys.readouterr()

    assert 'Making message' in out
    assert 'Mail' in str(type(msg))
    assert msg.from_email == From('lambda-functions-gcp@gcp-fmikina.com')
    assert presigned_mock.called
    assert presigned_mock.call_count == 2


@patch('main.sendgrid')
@patch('main.os')
def test_send(os_mock, sendgrid_mock, capsys):
    os_mock.remove = MagicMock()
    os_mock.path = MagicMock()
    os_mock.path.basename = MagicMock(side_effect=(lambda x: x))
    os_mock.getenv = MagicMock(return_value=str(uuid.uuid4()))

    sendgrid_client_mock = MagicMock()
    sendgrid_mock.SendGridAPIClient.return_value = sendgrid_client_mock
    sendgrid_client_mock.send.return_value = UserDict()
    sendgrid_client_mock.send.return_value.status_code = 202
    sendgrid_client_mock.send.return_value.body = "Hello body"
    sendgrid_client_mock.send.return_value.headers = "multi\nline"
    msg_mock = MagicMock()

    main._send(msg_mock)
    out, _ = capsys.readouterr()

    assert 'Attempting to send' in out
    assert sendgrid_mock.SendGridAPIClient.called
    assert sendgrid_client_mock.send.called
    sendgrid_client_mock.send.assert_called_with(msg_mock)
    assert '202' in out
    assert 'Hello body' in out
    assert 'multi' in out
    assert 'line' in out


@patch('main._get_users_info')
@patch('main._prepare_message')
@patch('main._send')
def test_email_user(snd_mock, msg_prep_mock, users_info_mock, capsys):
    event = {'data' : base64.b64encode(b"successful"), 'attributes': {'converted_file_name': "converted"}}

    users_info_mock.return_value = ("email", "raw", "original", "a\nb\nc\n")

    main.email_user(event, None)
    assert users_info_mock.called
    assert msg_prep_mock.called
    assert snd_mock.called
    msg_prep_mock.assert_called_with("email", "successful", "converted", "raw", "original", "a\nb\nc\n")
    snd_mock.assert_called_with(msg_prep_mock.return_value)


@patch('main._get_users_info')
@patch('main._prepare_message')
@patch('main._send')
def test_email_user(snd_mock, msg_prep_mock, users_info_mock, capsys):
    event = {'attributes': {'converted_file_name': "converted"}}

    users_info_mock.return_value = ("email", "raw", "original", "a\nb\nc\n")

    main.email_user(event, None)
    assert users_info_mock.called
    assert msg_prep_mock.called
    assert snd_mock.called
    msg_prep_mock.assert_called_with("email", "unsuccessful", "converted", "raw", "original", "a\nb\nc\n")
    snd_mock.assert_called_with(msg_prep_mock.return_value)


@patch('main._get_users_info')
@patch('main._prepare_message')
@patch('main._send')
def test_email_user(snd_mock, msg_prep_mock, users_info_mock, capsys):
    event = {'attributes': {'converted_file_name': "converted"}}

    users_info_mock.side_effect = Exception("xxx")

    main.email_user(event, None)
    out, err = capsys.readouterr()

    assert users_info_mock.called
    assert not msg_prep_mock.called
    assert not snd_mock.called
    assert 'Cannot proceed' in out

