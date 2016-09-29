from infi.pyutils.lazy import cached_function
from .rest import BASE_REST_URI, get_auth
from .config import Configuration
import requests
import urlparse


CONFLUENCE_SEARCH_URI = "prototype/1/search/site"


@cached_function
def _get_confluence_search_uri():
    config = Configuration.from_file()
    if config.confluence_fqdn is None:
        raise Exception("Confluence FQDN not set in configuration file. Run 'jirelnotes config set'")
    return urlparse.join(BASE_REST_URI.format(fqdn=config.confluence_fqdn), CONFLUENCE_SEARCH_URI)


@cached_function
def _get_confluence_global_response(global_label):
    project_params = dict(type='page', label='global:{}'.format(global_label))
    return requests.get(_get_confluence_search_uri(), params=project_params, auth=get_auth()).json()


def _extract_id_set(response):
    return set([item['id'] for item in response['result']])


def _intersect_and_extract_single_id(response1, response2):
    intersection = _extract_id_set(response1).intersection(response2)
    assert len(intersection) == 1
    return intersection.pop()


def _intersect_and_extract_single_id_or_none(response1, response2):
    intersection = _extract_id_set(response1).intersection(response2)
    assert len(intersection) <= 1
    return (list(intersection) + [None])[0]


def get_project_response(project_name):
    return _get_confluence_global_response(project_name, project_name.lower())


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
    page = requests.get(urlparse.join(BASE_REST_URI, '/api/content/{}?expand=body.view,version.number'.format(page_id)))
    return page['body']['view']['value'].replace(u'\xc3\x82', '').replace(u'\xc2\xa0', '')


def get_page_storage(page_id):
    page = requests.get(urlparse.join(BASE_REST_URI, '/api/content/{}?expand=body.storage,version.number'.format(page_id)))
    return page['body']['storage']['value'].replace(u'\xc3\x82', '').replace(u'\xc2\xa0', '')


def update_page_contents(page_id, body):
    page = requests.get(urlparse.join('/api/content/{}?expand=body.view,version.number,ancestors'.format(page_id)))
    data = dict(version=dict(number=page['version']['number']+1),
                id=page['id'], title=page['title'], type='page',
                body=dict(storage=dict(representation='storage', value=body)))
    if page['ancestors']:
        data['ancestors'] = [dict(id=page['ancestors'][-1]['id'])]
    requests.put(urlparse.join(BASE_REST_URI, 'api/content/%s' % page_id), data=data)


def iter_attachments(page_id, start=0, limit=50):
    data = requests.get(urlparse.join(BASE_REST_URI, "/api/content/%s/child/attachment?expand=id,filename,version.number&start=%s&limit=%s" % (page_id, start, limit)))
    for item in data['results']:
        yield dict(title=item['title'], link=item['_links']['download'].split('?')[0] + '?api=v2')
    if len(data['results']) == limit:
        for _tuple in iter_attachments_tuple(page_id, start=start+limit, limit=limit):
            yield _tuple
