"""Structural article metadata extraction shared by discovery generators.

An event's dates do not date an article. Only top-level JSON-LD entities and
entities in @graph are candidates; nested related objects are not page articles.
"""
import json

from generation_support import GenerationError
from iso_dates import iso_datetime


ARTICLE_TYPES = {'Article', 'BlogPosting', 'NewsArticle'}


def types_of(node):
    values = node.get('@type', [])
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ValueError('JSON-LD @type must be a string or a list of strings')
    return {value.rsplit('/', 1)[-1] for value in values}


def structured_entities(soup, path):
    """Parse every head JSON-LD block, accepting objects, arrays and @graph."""
    entities = []

    def visit(value):
        if isinstance(value, list):
            for node in value:
                visit(node)
        elif isinstance(value, dict):
            if '@type' in value:
                types_of(value)
                entities.append(value)
            if '@graph' in value:
                visit(value['@graph'])
        else:
            raise ValueError('JSON-LD entities must be objects or arrays')

    try:
        if soup.head is not None:
            for script in soup.head.find_all('script'):
                if str(script.get('type', '')).strip().lower() == 'application/ld+json':
                    visit(json.loads(script.get_text()))
    except (ValueError, TypeError) as error:
        raise GenerationError(f'{path}: invalid head JSON-LD: {error}') from error
    return entities


def article_entity(soup, path):
    nodes = structured_entities(soup, path)
    articles = [node for node in nodes if types_of(node) & ARTICLE_TYPES]
    if len(articles) > 1:
        primary_ids = set()
        for node in nodes:
            if types_of(node) & {'WebPage', 'CollectionPage'}:
                main = node.get('mainEntity', [])
                for item in main if isinstance(main, list) else [main]:
                    if isinstance(item, dict) and item.get('@id'):
                        primary_ids.add(item['@id'])
                    elif isinstance(item, str):
                        primary_ids.add(item)
        selected = [node for node in articles if node.get('@id') in primary_ids]
        if len(selected) != 1:
            raise GenerationError(f'{path}: multiple article entities without one unambiguous WebPage.mainEntity')
        articles = selected
    if articles:
        return articles[0]
    marked_article = soup.find('article') is not None or any(
        str(meta.get('property', '')).lower() == 'og:type'
        and str(meta.get('content', '')).lower() == 'article'
        for meta in (soup.head.find_all('meta') if soup.head else [])
    )
    if marked_article:
        raise GenerationError(f'{path}: article page is missing an Article/BlogPosting JSON-LD entity')
    return None


def publication_datetime(value, path):
    """RSS requires a time: serialize date-only sources at midnight UTC.

    This is a deterministic serialization convention, not an inferred original
    publication time. Full timestamps must contain their original UTC offset.
    """
    try:
        return iso_datetime(value, allow_date_only=True)
    except ValueError as error:
        raise GenerationError(f'{path}: invalid article datePublished {value!r}: {error}') from error
