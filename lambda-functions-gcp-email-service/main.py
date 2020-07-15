import base64
import sendgrid
import os
from sendgrid.helpers.mail import *
import datetime
import tempfile
import traceback

from google.cloud import datastore, storage

ds = datastore.Client()


def _write_creds():
    """
    Writes credentials passed in the environment
    to a JSON file.
    """
    _, temp_local_filename = tempfile.mkstemp()
    creds = open(f"{temp_local_filename}.json", "w")
    SERVICE_ACCOUNT_PRIVATE_KEY = os.environ['SERVICE_ACCOUNT_PRIVATE_KEY']
    creds.write(SERVICE_ACCOUNT_PRIVATE_KEY)
    creds.close()
    return f"{temp_local_filename}.json"


def _make_presigned_uri(bucket_name, key):
    """
    Makes a presigned url for a specific bucket and a key.
    """
    print(f"Making presigned uri for {bucket_name}/{key}")
    storage_client = storage.Client.from_service_account_json(_write_creds())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(key)

    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(days=7),
        method="GET"
    )


def _get_users_info(converted_file_name):
    """
    Restores the user's info from the datastore.
    """
    print("Restoring user info")
    DATASTORE_ENTITY_KEY = os.environ['DATASTORE_ENTITY_KEY']
    query = ds.query(kind=DATASTORE_ENTITY_KEY)
    query.add_filter('converted_image_key', '=', converted_file_name)
    res = list(query.fetch())
    assert(len(res) == 1)
    res = res[0]
    print('Entity', res.items())
    return res['user_email'], res['raw_image_key'], res['original_image_name'], res['discovered_text']


def _prepare_message(email, maybe_success, converted_file_name, raw_key, original_file_name, texts):
    """
    Prepares html message for the email.
    """
    print("Making message")
    RAW_BUCKET_NAME = os.environ['RAW_BUCKET_NAME']
    CONVERTED_BUCKET_NAME = os.environ['CONVERTED_BUCKET_NAME']
    raw_uri = _make_presigned_uri(RAW_BUCKET_NAME, raw_key)
    converted_uri = _make_presigned_uri(CONVERTED_BUCKET_NAME, converted_file_name)
    headline = f'<strong>The analysis for {original_file_name} was a {maybe_success}</strong>'
    raw_uri_text = f"<div>To download raw image access <a href='{raw_uri}'>this</a></div>"
    converted_uri_text = f"<div>To download converted image access <a href='{converted_uri}'>this</a></div>"
    _texts = texts.replace('\n', '<br>')
    analysis = f"<div> The vision API found <br> {_texts} </div>"
    return Mail(
        from_email='lambda-functions-gcp@gcp-fmikina.com',
        to_emails=email,
        subject='Your analysis is finished',
        html_content=f"{headline} <br> {raw_uri_text} <br> {converted_uri_text} <br> {analysis}")


def _send(message):
    """
    Sends the message using sendgrid.
    """
    print('Attempting to send email')
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    response = sg.send(message)
    print(response.status_code)
    print(response.body)
    print(response.headers)


def email_user(event, context):
    """
    Gets a message from a topic.
    Gets user's info from the datastore.
    Prepares an email for the user.
    Sends the email to the user.
    """
    try:
        if 'data' in event:
            name = base64.b64decode(event['data']).decode('utf-8')
        else:
            name = 'unsuccessful'
        converted_file_name = event['attributes']['converted_file_name']
        email, raw_key, original_file_name, texts = _get_users_info(converted_file_name)
        msg = _prepare_message(email, name, converted_file_name, raw_key, original_file_name, texts)
        _send(msg)
    except Exception as err:
        print('Cannot proceed', err)
        traceback.print_exc()

   
