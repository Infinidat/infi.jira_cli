from infi.pyutils.lazy import cached_function


@cached_function
def get_confluence():
    from .config import Configuration
    from json_rest import JSONRestSender
    config = Configuration.from_file()
    client = JSONRestSender("http://{0}/rest".format(config.confluence_fqdn))
    client.set_basic_authorization(config.username, config.password)
    return client


def get_release_notes_page_id(project_name):
    response = get_confluence().get('/prototype/1/search/site?type=page&label=global:release-notes&label=global:{}'.format(project_name.lower()))
    assert response['totalSize']
    return response['result'][0]['id']


def get_page_contents(page_id):
    page = get_confluence().get('/api/content/{}?expand=body.view,version.number'.format(page_id))
    print page['body']['view']['value']


def update_page_contents(page_id, body):
    page = get_confluence().get('/api/content/{}?expand=body.view,version.number'.format(page_id))
    data = dict(version=dict(number=page['version']['number']+1),
                id=page['id'], title=page['title'], type='page',
                body=dict(representation='storage', storage=dict(value=body)))
    get_confluence().put('api/content/%s' % page_id, data=data)
