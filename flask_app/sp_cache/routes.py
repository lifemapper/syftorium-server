"""Flask functions for Specify Cache."""
from flask import (
    Blueprint
)
from werkzeug.exceptions import NotFound

import solr_controller as controller


bp = Blueprint('sp_cache', __name__, url_prefix='/sp_cache')


# .....................................................................................
@bp.route('/', methods=('GET'))
def sp_cache_status():
    """Get overall health of the cache."""
    num_collections = 0
    num_records = 0
    system_status = 'In Development'
    return {
        'num_collections': num_collections,
        'num_records': num_records,
        'status': system_status
    }


# .....................................................................................
@bp.route('/collection', methods=('POST'))
def sp_cache_collection_post():
    collection = Collection(request.json)
    controller.post_collection(collection)
    return controller.get_collection(controller.collection_id).serialize_json()


# .....................................................................................
@bp.route('/collection/<string:collection_id>', methods=('GET'))
def sp_cache_collection_get(collection_id):
    """Return information about a cached collection."""
    collection = controller.get_collection(collection_id)
    if collection:
        return collection.serialize_json()
    raise NotFound()



# .....................................................................................
@bp.route('/collection/<string:collection_id>/occurrences/', methods=('DELETE', 'POST', 'PUT'))
def collection_occurrences_modify(collection_id):
    if request.method.lower() == 'delete':
        delete_identifiers = request.json['delete_identifiers']
        controller.delete_collection_occurrences(collection_id, delete_identifiers)
        return
    controller.update_collection_occurrences(collection_id, request.json['specimens'])


# .....................................................................................
@bp.route('/collection/<string:collection_id>/occurrences/<string:identifier>', method='DELETE')
def collection_occurrence_delete(collection_id, identifier):
    controller.delete_collection_occurrences(collection_id, [identifier])


# .....................................................................................
@bp.route('/collection/<string:collection_id>/occurrences/<string:identifier>', method='GET')
def collection_occurrence_get(collection_id, identifier):
    specimen = controller.get_collection_occurrence(collection_id, identifier)
    if specimen:
        return specimen.serialize_json()
    raise NotFound()


# .....................................................................................
@bp.route('/collection/<string:collection_id>/occurrences/<string:identifier>', method='PUT')
def collection_occurrence_put(collection_id, identifier):
    new_specimen_record = SpecimenRecord(request.json)
    controller.update_collection_occurrences(collection_id, [new_specimen_record])
    return controller.get_collection_occurrence(collection_id, identifier).serialize_json()
