import os
import tempfile

from google.cloud import storage, vision, datastore
from wand.image import Image


storage_client = storage.Client()
ds = datastore.Client()


def _scale_locally(blob):
    """
    Downloads blob from a bucket to a local file.

    Scales local file down by multiplying both width
    and height by 1/2. In case the image after
    scaling is too big, there is a boundary
    of 800 pixels per width.
    Ratio is being preserved.

    Returns the local file path.
    """
    file_name = blob.name
    _, temp_local_filename = tempfile.mkstemp()
    blob.download_to_filename(temp_local_filename)

    print(f'Image {file_name} was downloaded to {temp_local_filename}.')

    with Image(filename=temp_local_filename) as image:
        width, height = image.size
        to_resize_width = min(800, int(width / 2))
        to_resize_height = int((height / width) * to_resize_width)
        image.resize(to_resize_width, to_resize_height)
        image.save(filename=temp_local_filename)

    print(f'Image was resized')

    return temp_local_filename


def _update_ds(file_name, converted_file_name):
    """
    Updates an entry in a datastore.
    For the specific filename adds the converted file name.
    """
    query = ds.query(kind=os.environ['DATASTORE_ENTITY_KEY'])
    query.add_filter('raw_image_key', '=', file_name)
    res = list(query.fetch())
    assert(len(res) == 1)
    res = res[0]
    print('Entity', res.items())
    res['converted_image_key'] = converted_file_name
    ds.put(res)
    print(f'Successfully updated entity for {file_name} in datastore')


def scale_down(data, context):
    """
    Scales down the image.
    Pushes scaled image to a bucket specified by the environment.
    Updates datastore with the scaled image filename.
    """
    try:
        PUSH_TO_BUCKET = os.environ['BUCKET_NAME']
        file_name = data['name']
        bucket_name = data['bucket']
        blob = storage_client.bucket(bucket_name).get_blob(file_name)

        local_path = _scale_locally(blob)

        converted_file_name = f'converted-{file_name}'
        bucket_for_conversions = storage_client.bucket(PUSH_TO_BUCKET)
        new_blob = bucket_for_conversions.blob(converted_file_name)
        new_blob.upload_from_filename(local_path)
        print(f'Uploaded file to {converted_file_name}')
        _update_ds(file_name, converted_file_name)
        print('Cleaning up')
        os.remove(local_path)
    except Exception as err:
        print(f'Cannot proceed due to {err}')

