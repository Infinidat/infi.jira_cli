from infi.pyutils.lazy import cached_function


@cached_function
def get_confluence():
    from .config import Configuration
    from json_rest import JSONRestSender
    config = Configuration.from_file()
    client = JSONRestSender("https://{0}/rest".format(config.confluence_fqdn))
    client.set_basic_authorization(config.username, config.password)
    return client


def get_release_notes_page_id(project_name):
    release_notes = get_confluence().get('/prototype/1/search/site?type=page&label=global:release-notes')
    project = get_confluence().get('/prototype/1/search/site?type=page&label=global:{}'.format(project_name.lower()))
    page = set([item['id'] for item in release_notes['result']]).intersection(set([item['id'] for item in project['result']]))
    assert len(page) == 1
    return page.pop()


def get_release_notes_header_page_id(project_name):
    release_notes = get_confluence().get('/prototype/1/search/site?type=page&label=global:release-notes-header')
    project = get_confluence().get('/prototype/1/search/site?type=page&label=global:{}'.format(project_name.lower()))
    page = set([item['id'] for item in release_notes['result']]).intersection(set([item['id'] for item in project['result']]))
    assert len(page) <= 1
    return (list(page) + [None])[0]


def get_release_notes_footer_page_id(project_name):
    release_notes = get_confluence().get('/prototype/1/search/site?type=page&label=global:release-notes-footer')
    project = get_confluence().get('/prototype/1/search/site?type=page&label=global:{}'.format(project_name.lower()))
    page = set([item['id'] for item in release_notes['result']]).intersection(set([item['id'] for item in project['result']]))
    assert len(page) <= 1
    return (list(page) + [None])[0]


def get_page_contents(page_id):
    page = get_confluence().get('/api/content/{}?expand=body.view,version.number'.format(page_id))
    return page['body']['view']['value'].replace(u'\xc3\x82', '').replace(u'\xc2\xa0', '')


def update_page_contents(page_id, body):
    page = get_confluence().get('/api/content/{}?expand=body.view,version.number,ancestors'.format(page_id))
    data = dict(version=dict(number=page['version']['number']+1),
                id=page['id'], title=page['title'], type='page',
                body=dict(representation='storage', storage=dict(value=body)))
    if page['ancestors']:
        data['ancestors'] = [dict(id=page['ancestors'][-1]['id'])]
    get_confluence().put('api/content/%s' % page_id, data=data)


def iter_attachments(page_id, start=0, limit=50):
    data = get_confluence().get("/api/content/%s/child/attachment?expand=id,filename,version.number&start=%s&limit=%s" % (page_id, start, limit))
    for item in data['results']:
        yield dict(title=item['title'], link=item['_links']['download'].split('?')[0] + '?api=v2')
    if len(data['results']) == limit:
        for _tuple in iter_attachments_tuple(page_id, start=start+limit, limit=limit):
            yield _tuple
