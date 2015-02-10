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
    release_notes = get_confluence().get('/prototype/1/search/site?type=page&label=global:release-notes')
    project = get_confluence().get('/prototype/1/search/site?type=page&label=global:{}'.format(project_name.lower()))
    page = set([item['id'] for item in release_notes['result']]).intersection(set([item['id'] for item in project['result']]))
    assert len(page) == 1
    return page.pop()


def get_page_contents(page_id):
    page = get_confluence().get('/api/content/{}?expand=body.view,version.number'.format(page_id))
    return page['body']['view']['value']


def update_page_contents(page_id, body):
    page = get_confluence().get('/api/content/{}?expand=body.view,version.number,ancestors'.format(page_id))
    data = dict(version=dict(number=page['version']['number']+1),
                id=page['id'], title=page['title'], type='page',
                body=dict(representation='storage', storage=dict(value=body)))
    if page['ancestors']:
        data['ancestors'] = [dict(id=page['ancestors'][-1]['id'])]
    get_confluence().put('api/content/%s' % page_id, data=data)
