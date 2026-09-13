"""Page-level semantic checks for the site's JSON-LD graph.

These enforce this site's graph/content contract, not Google rich-result
eligibility. Shared entity facts remain owned by check_event_facts.py.
"""
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

from bs4 import BeautifulSoup

SITE = 'https://milanosensualcongress.com'
PAGE_TYPES = {'WebPage', 'ContactPage', 'FAQPage', 'CollectionPage'}
ARTICLE_TYPES = {'Article', 'BlogPosting', 'NewsArticle'}


def values(value):
    return value if isinstance(value, list) else [value] if value is not None else []


def types(node):
    return {value for value in values(node.get('@type')) if isinstance(value, str)}


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def text_key(value):
    """Ignore HTML, whitespace and punctuation, while preserving words/numbers."""
    plain = BeautifulSoup(str(value), 'html.parser').get_text(' ', strip=True)
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', plain).casefold()))


def visible_text(soup):
    body = BeautifulSoup(str(soup.body or ''), 'html.parser')
    # Closed details remain accessible by opening their summary. Explicitly
    # hidden markup is not evidence for structured question/answer content.
    for element in list(body.select('script, style, template, [hidden], [aria-hidden="true"]')):
        element.decompose()
    for element in list(body.select('[style]')):
        if re.search(r'(display\s*:\s*none|visibility\s*:\s*hidden)', element.get('style', ''), re.I):
            element.decompose()
    return text_key(body.get_text(' ', strip=True))


def check_graph(page, soup, data):
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(f'[{page}] {message}')

    require(isinstance(data, dict) and data.get('@context') == 'https://schema.org',
            'JSON-LD needs the https://schema.org context')
    graph = data.get('@graph') if isinstance(data, dict) else None
    if not isinstance(graph, list) or not all(isinstance(n, dict) for n in graph):
        return errors + [f'[{page}] JSON-LD needs an array of graph objects']
    all_nodes = list(nodes(graph))
    definitions = {n['@id']: n for n in all_nodes if isinstance(n.get('@id'), str) and len(n) > 1}
    canonical_tag = soup.select_one('head link[rel="canonical"]')
    if canonical_tag is None:
        return errors + [f'[{page}] cannot identify canonical WebPage']
    canonical = canonical_tag.get('href', '')
    webpage_id = canonical + '#webpage'
    webpage = definitions.get(webpage_id, {})
    require(bool(types(webpage) & PAGE_TYPES), 'canonical #webpage must have a page type')
    require(webpage.get('url') == canonical, 'WebPage.url must match canonical')
    require(webpage.get('isPartOf') == {'@id': SITE + '/#website'}, 'WebPage must belong to the shared WebSite')
    language = soup.html.get('lang') if soup.html else None
    require(str(webpage.get('inLanguage', '')).split('-')[0] == language,
            'WebPage.inLanguage must match HTML language')
    for entity, kind in [('/#organization', 'Organization'), ('/#website', 'WebSite')]:
        require(kind in types(definitions.get(SITE + entity, {})), f'graph must define the shared {kind}')
    # A valid file path does not make an undefined #fragment entity valid.
    for node in all_nodes:
        entity_id = node.get('@id')
        if set(node) == {'@id'} and isinstance(entity_id, str) and entity_id.startswith(canonical + '#'):
            require(entity_id in definitions, f'unresolved local entity reference {entity_id}')

    breadcrumbs = [n for n in graph if 'BreadcrumbList' in types(n)]
    homepage = page in ('index.html', 'it/index.html')
    if not homepage:
        require(len(breadcrumbs) == 1, 'subpage needs exactly one BreadcrumbList')
    for breadcrumb in breadcrumbs:
        items = breadcrumb.get('itemListElement')
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            require(False, 'BreadcrumbList needs ListItem objects')
            continue
        require(len(items) >= 2, 'BreadcrumbList needs at least two items; omit it on homepages')
        require(breadcrumb.get('@id') == canonical + '#breadcrumb', 'breadcrumb ID must belong to this page')
        require(webpage.get('breadcrumb') == {'@id': breadcrumb.get('@id')}, 'WebPage must reference its breadcrumb')
        nav = soup.find('nav', attrs={'aria-label': re.compile('breadcrumb', re.I)})
        html_links = [urljoin(canonical, a['href']) for a in nav.select('a[href]')] if nav else []
        trail_urls = []
        for position, item in enumerate(items, 1):
            require('ListItem' in types(item) and type(item.get('position')) is int and item['position'] == position,
                    'breadcrumb positions must be consecutive integers starting at 1')
            require(bool(item.get('name')), 'breadcrumb item needs a name')
            url = item.get('item')
            if isinstance(url, dict):
                url = url.get('@id')
            if position < len(items):
                require(isinstance(url, str) and url.startswith(SITE + '/'), 'ancestor breadcrumb needs a site URL')
                trail_urls.append(url)
            else:
                require(url in (None, canonical), 'final breadcrumb must identify the canonical page')
            if nav:
                require(text_key(item.get('name', '')) in text_key(nav.get_text(' ', strip=True)),
                        'HTML/schema breadcrumb labels disagree')
        # A final self-link is also valid in the HTML trail.
        require(html_links in (trail_urls, trail_urls + [canonical]), 'HTML/schema breadcrumb links disagree')

    body_text = visible_text(soup)
    for node in all_nodes:
        node_types = types(node)
        if 'Question' in node_types:
            answer = node.get('acceptedAnswer')
            require(bool(node.get('name')) and text_key(node['name']) in body_text,
                    'FAQ question is missing from accessible page content')
            require(isinstance(answer, dict) and 'Answer' in types(answer) and bool(answer.get('text'))
                    and text_key(answer['text']) in body_text,
                    'FAQ answer is missing from accessible page content')
        if node_types & ARTICLE_TYPES:
            require(bool(node.get('@id')), 'article needs its own entity ID')
            require(node.get('mainEntityOfPage') == {'@id': webpage_id}, 'article must identify its own WebPage')
            require(webpage.get('mainEntity') == {'@id': node.get('@id')}, 'WebPage must identify the article as primary')
            for field in ('headline', 'author', 'publisher', 'image', 'datePublished', 'inLanguage'):
                require(bool(node.get(field)), f'article needs {field}')
        if 'ContactPage' in node_types:
            require(node.get('@id') == webpage_id, 'ContactPage must be the canonical page, not a second page entity')
        if 'Course' in node_types:
            require(webpage.get('mainEntity') == {'@id': node.get('@id')}, 'masterclass Course must be the primary entity')
            for field in ('name', 'description', 'provider', 'coursePrerequisites', 'hasCourseInstance', 'timeRequired'):
                require(bool(node.get(field)), f'Course needs {field}')
        if 'CourseInstance' in node_types:
            for field in ('startDate', 'endDate', 'inLanguage', 'location', 'instructor', 'offers', 'superEvent'):
                require(bool(node.get(field)), f'CourseInstance needs {field}')
            location = node.get('location', {})
            require(isinstance(location, dict) and bool(location.get('address')), 'CourseInstance needs the venue address')
            for teacher in values(node.get('instructor')):
                teacher = definitions.get(teacher.get('@id'), teacher) if isinstance(teacher, dict) else {}
                require('Person' in types(teacher), 'CourseInstance instructor must identify an individual Person')
            if node.get('@id') == SITE + '/masterclass#instance':
                offer_id = node.get('offers', {}).get('@id')
                admission = definitions.get(SITE + '/#event', {}).get('offers', {})
                require(offer_id == SITE + '/tickets#masterclass-upgrade' and
                        any(addon.get('@id') == offer_id for addon in values(admission.get('addOn'))
                            if isinstance(addon, dict)),
                        'masterclass upgrade must be linked through the Full Pass Offer.addOn')
        if 'PerformingGroup' in node_types:
            members = values(node.get('member'))
            require(len(members) >= 2 and all(isinstance(member, dict) and
                    'Person' in types(definitions.get(member.get('@id'), member)) for member in members),
                    'dance couple must identify its individual Person members')
            require(not any(field in node for field in ('jobTitle', 'nationality')),
                    'Person-only properties cannot describe a PerformingGroup')
        if 'Person' in node_types:
            require(' y ' not in node.get('name', '').casefold(), 'a dance couple cannot be a single Person')
        if 'ContactPoint' in node_types:
            phone = node.get('telephone')
            if phone:
                require(isinstance(phone, str) and re.fullmatch(r'\+[\d ()-]+', phone) is not None,
                        'contact telephone must include an international country code')
        if 'AggregateOffer' in node_types:
            nested = values(node.get('offers'))
            require(all(isinstance(offer, dict) and offer.get('priceCurrency') == node.get('priceCurrency') for offer in nested),
                    'AggregateOffer cannot mix currencies')
            try:
                prices = [Decimal(str(offer['price'])) for offer in nested if isinstance(offer, dict)]
                require(bool(prices) and Decimal(str(node.get('lowPrice'))) == min(prices)
                        and Decimal(str(node.get('highPrice'))) == max(prices), 'AggregateOffer price range disagrees with offers')
            except (InvalidOperation, KeyError):
                require(False, 'AggregateOffer needs valid prices')
    return errors
