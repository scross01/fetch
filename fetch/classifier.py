"""Page type detection and classification for intelligent content extraction."""

import re
from bs4 import BeautifulSoup
from .types import PageType


def classify_page(html_content, url):
    """Determine the type of page based on URL and HTML structure.
    
    Args:
        html_content: Raw HTML content
        url: The URL of the page
        
    Returns:
        PageType enum value indicating the detected page type
    """
    # URL-based classification first (fastest)
    url_type = classify_by_url(url)
    if url_type != PageType.UNKNOWN:
        return url_type
    
    # HTML structure-based classification
    html_type = classify_by_html_structure(html_content)
    if html_type != PageType.UNKNOWN:
        return html_type
    
    # Schema.org-based classification
    schema_type = classify_by_schema(html_content)
    if schema_type != PageType.UNKNOWN:
        return schema_type
    
    # Default to article
    return PageType.ARTICLE


def classify_by_url(url):
    """Classify page type based on URL patterns.
    
    Args:
        url: The URL to analyze
        
    Returns:
        PageType enum value or UNKNOWN if no pattern matches
    """
    if not url:
        return PageType.UNKNOWN
    
    url_lower = url.lower()
    
    # Forum patterns
    forum_patterns = [
        r'/forum/',
        r'/thread/',
        r'/discussion/',
        r'/topic/',
        r'/post/',
        r'/message/',
        r'/board/',
        r'/community/',
    ]
    
    for pattern in forum_patterns:
        if re.search(pattern, url_lower):
            return PageType.FORUM
    
    # Q&A patterns
    qa_patterns = [
        r'/question',
        r'/questions/',
        r'/q/',
        r'/answer',
        r'/answers/',
        r'/qa/',
        r'/stackexchange',
        r'/stackoverflow',
        r'/superuser',
        r'/askubuntu',
    ]
    
    for pattern in qa_patterns:
        if re.search(pattern, url_lower):
            return PageType.QA
    
    # Article patterns
    article_patterns = [
        r'/blog/',
        r'/article/',
        r'/news/',
        r'/post/',
        r'/story/',
        r'/tutorial/',
        r'/guide/',
    ]
    
    for pattern in article_patterns:
        if re.search(pattern, url_lower):
            return PageType.ARTICLE
    
    return PageType.UNKNOWN


def classify_by_html_structure(html_content):
    """Classify page type based on HTML structure and element patterns.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        PageType enum value or UNKNOWN if no pattern matches
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
    except Exception:
        return PageType.UNKNOWN
    
    # Count elements with comment-related classes
    comment_classes = [
        'comment', 'comments', 'reply', 'replies', 'post', 'posts',
        'message', 'messages', 'thread', 'discussion', 'answer', 'answers'
    ]
    
    comment_elements = 0
    for class_name in comment_classes:
        # Find elements with class containing the keyword
        elements = soup.find_all(class_=lambda x: x and class_name in x.lower())
        comment_elements += len(elements)
    
    # If we find many comment-like elements, it's likely a forum or Q&A
    if comment_elements > 5:
        # Further distinguish between forum and Q&A
        qa_indicators = soup.find_all(class_=lambda x: x and any(
            word in x.lower() for word in ['answer', 'question', 'accepted', 'vote']
        ))
        
        if len(qa_indicators) > 2:
            return PageType.QA
        else:
            return PageType.FORUM
    
    # Look for forum-specific patterns
    forum_patterns = [
        {'tag': 'div', 'class': lambda x: x and 'forum' in x.lower()},
        {'tag': 'div', 'class': lambda x: x and 'thread' in x.lower()},
        {'tag': 'ul', 'class': lambda x: x and 'posts' in x.lower()},
    ]
    
    for pattern in forum_patterns:
        elements = soup.find_all(pattern['tag'], class_=pattern['class'])
        if len(elements) > 0:
            return PageType.FORUM
    
    # Look for Q&A specific patterns
    qa_patterns = [
        {'tag': 'div', 'class': lambda x: x and 'question' in x.lower()},
        {'tag': 'div', 'class': lambda x: x and 'answer' in x.lower()},
        {'tag': 'div', 'itemprop': 'answer'},
        {'tag': 'div', 'itemprop': 'suggestedAnswer'},
    ]
    
    for pattern in qa_patterns:
        if 'itemprop' in pattern:
            elements = soup.find_all(pattern['tag'], itemprop=pattern['itemprop'])
        else:
            elements = soup.find_all(pattern['tag'], class_=pattern['class'])
        if len(elements) > 0:
            return PageType.QA
    
    return PageType.UNKNOWN


def classify_by_schema(html_content):
    """Classify page type based on Schema.org structured data.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        PageType enum value or UNKNOWN if no schema matches
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
    except Exception:
        return PageType.UNKNOWN
    
    # Look for Schema.org types
    schema_mappings = {
        'DiscussionForumPosting': PageType.FORUM,
        'Question': PageType.QA,
        'QAPage': PageType.QA,
        'Article': PageType.ARTICLE,
        'BlogPosting': PageType.ARTICLE,
        'NewsArticle': PageType.ARTICLE,
    }
    
    # Check itemscope and itemtype attributes
    schema_elements = soup.find_all(attrs={"itemtype": True})
    
    for element in schema_elements:
        itemtype = element.get('itemtype', '')
        for schema_type, page_type in schema_mappings.items():
            if schema_type in itemtype:
                return page_type
    
    # Also check JSON-LD structured data
    json_scripts = soup.find_all('script', type='application/ld+json')
    
    for script in json_scripts:
        try:
            import json
            data = json.loads(script.string)
            
            # Handle both single objects and arrays
            if isinstance(data, list):
                items = data
            else:
                items = [data]
            
            for item in items:
                if '@type' in item:
                    schema_type = item['@type']
                    if isinstance(schema_type, list):
                        schema_type = schema_type[0]
                    
                    for st, page_type in schema_mappings.items():
                        if st in schema_type:
                            return page_type
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue
    
    return PageType.UNKNOWN