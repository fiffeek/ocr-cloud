import os
import tempfile

from google.cloud import vision, datastore, pubsub_v1


publisher = pubsub_v1.PublisherClient()
vision_client = vision.ImageAnnotatorClient()
ds = datastore.Client()


def _publish_to_topic(data, file_name):
    """
    Publishes data to the topic specified in the environment.
    Publishes file_name as metadata as well in the same message.
    """
    topic_path = publisher.topic_path(os.environ['PROJECT_ID'], os.environ['TOPIC_NAME'])
    data = data.encode("utf-8")
    future = publisher.publish(topic_path, data=data, converted_file_name=file_name)
    print(f'Result of publishing {future.result()}')


def _update_ds_image_text(file_name, texts):
    """
    Updates information in the datastore.
    Adds discovered text to the datastore entity.
    """
    query = ds.query(kind=os.environ['DATASTORE_ENTITY_KEY'])
    query.add_filter('converted_image_key', '=', file_name)
    res = list(query.fetch())
    assert(len(res) == 1)
    res = res[0]
    print('Entity', res.items())
    res['discovered_text'] = texts
    res.exclude_from_indexes = {'discovered_text'}
    ds.put(res)
    print(f'Successfully updated entity for {file_name} in datastore')


def _find_text(data, context):
    """
    Calls Vision API to discover text in the image.
    Publishes a message to a topic whether the call was successful.
    If the call was successful updates data in the datastore.
    """
    print(data, context)
    file_name = data['name']
    bucket_name = data['bucket']

    blob_uri = f'gs://{bucket_name}/{file_name}'
    image = vision.types.Image()
    image.source.image_uri = blob_uri
    print(image)
    print(f'Looking for text in {file_name}.')
    response = vision_client.text_detection(image=image)

    if response.error.message:
        print('Error occured while calling vision API')
        _publish_to_topic('unsuccessful', file_name)
    else:
        texts = response.text_annotations
        text_concat = '\n'.join([text.description for text in texts])
        print(f'Discovered text [{text_concat}] of length {len(text_concat)} in {file_name}')
        print('Updating data in datastore')
        _update_ds_image_text(file_name, text_concat)
        print('Publishing to the topic')
        _publish_to_topic('successful', file_name)


def find_text(data, context):
    """
    Wraps the real function into try-catch block.
    """
    try:
        _find_text(data, context)
    except Exception as err:
        print('Error occured')
        print(err)

