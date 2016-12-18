from infi.pyutils.lazy import cached_function
from .config import Configuration
import requests
try:
    from urlparse import urljoin
except:
    from urllib.parse import urljoin
from .credential_store import ConfluenceCredentialsStore
from requests.auth import HTTPBasicAuth


@cached_function
def get_auth():
    config = Configuration.from_file()
    fqdn = config.confluence_fqdn
    credential_store = ConfluenceCredentialsStore()
    credentials = credential_store.get_credentials(fqdn)
    return HTTPBasicAuth(credentials.get_username(), credentials.get_password())


@cached_function
def get_headers():
    return {'Accept': 'application/json'}


@cached_function
def _get_confluence_uri(path):
    config = Configuration.from_file()
    if config.confluence_fqdn is None:
        raise Exception("Confluence FQDN not set in configuration file. Run 'jirelnotes config set'")
    return urljoin('https://{fqdn}/rest/'.format(fqdn=config.confluence_fqdn), path)


@cached_function
def _get_confluence_global_response(global_label):
    project_params = dict(type='page', label='global:{}'.format(global_label))
    return requests.get(_get_confluence_uri('prototype/1/search/site'),
                        params=project_params,
                        headers=get_headers(),
                        auth=get_auth()).json()


def _extract_id_set(response):
    return set([item['id'] for item in response['result']])


def _intersect_and_extract_single_id(response1, response2):
    intersection = _extract_id_set(response1).intersection(_extract_id_set(response2))
    if len(intersection) != 1:
        raise Exception('Should have found exactly one id, instead found {}'.format(intersection))
    return intersection.pop()


def _intersect_and_extract_single_id_or_none(response1, response2):
    intersection = _extract_id_set(response1).intersection(_extract_id_set(response2))
    if len(intersection) > 1:
        raise Exception('Should have found at most one id, instead found {}'.format(intersection))
    return (list(intersection) + [None])[0]


def get_project_response(project_name):
    return _get_confluence_global_response(project_name.lower())


def get_release_notes_page_id(project_name):
    release_notes_response = _get_confluence_global_response('release-notes')
    project_response = get_project_response(project_name)
    return _intersect_and_extract_single_id(release_notes_response, project_response)


def get_release_notes_header_page_id(project_name):
    release_notes_header_response = _get_confluence_global_response('release-notes-header')
    project_response = get_project_response(project_name)
    return _intersect_and_extract_single_id_or_none(release_notes_header_response, project_response)


def get_release_notes_footer_page_id(project_name):
    release_notes_footer_response = _get_confluence_global_response('release-notes-footer')
    project_response = get_project_response(project_name)
    return _intersect_and_extract_single_id_or_none(release_notes_footer_response, project_response)


def get_page_contents(page_id):
    page = requests.get(_get_confluence_uri('api/content/{}?expand=body.view,version.number'.format(page_id)),
                        auth=get_auth(),
                        headers=get_headers()).json()
    return page['body']['view']['value'].replace(u'\xc3\x82', '').replace(u'\xc2\xa0', '')


def get_page_storage(page_id):
    page = requests.get(_get_confluence_uri('api/content/{}?expand=body.storage,version.number'.format(page_id)),
                        auth=get_auth(),
                        headers=get_headers()).json()
    return page['body']['storage']['value'].replace(u'\xc3\x82', '').replace(u'\xc2\xa0', '')


def update_page_contents(page_id, body):
    page = requests.get(_get_confluence_uri('api/content/{}?expand=body.view,version.number,ancestors'.format(page_id)),
                        auth=get_auth()).json()
    data = dict(version=dict(number=page['version']['number']+1),
                id=page['id'], title=page['title'], type='page',
                body=dict(storage=dict(representation='storage', value=body)))
    if page['ancestors']:
        data['ancestors'] = [dict(id=page['ancestors'][-1]['id'])]
    requests.put(_get_confluence_uri('api/content/{}'.format(page_id)), json=data, auth=get_auth()).raise_for_status()


def iter_attachments(page_id, start=0, limit=50):
    data = requests.get(_get_confluence_uri('api/content/{page_id}/child/attachment'.format(page_id=page_id)),
                        headers=get_headers(),
                        auth=get_auth(),
                        params={'expand': 'id', 'start':start, 'limit':limit}).json()
    for item in data['results']:
        yield dict(title=item['title'], link=item['_links']['download'].split('?')[0] + '?api=v2')
    if len(data['results']) == limit:
        for _tuple in iter_attachments_tuple(page_id, start=start+limit, limit=limit):
            yield _tuple
