"""Content extraction strategies for different types of web pages."""

from html2text import html2text
from readability import Document
from bs4 import BeautifulSoup


def extract_with_trafilatura(html_content, url, include_comments=True):
    """Extract content using Trafilatura library.
    
    Args:
        html_content: Raw HTML content
        url: Base URL for resolving relative links
        include_comments: Whether to include comments in the output
        
    Returns:
        Formatted markdown string with extracted content
    """
    try:
        from trafilatura import extract
        
        # Extract content using Trafilatura
        result = extract(
            html_content,
            include_comments=include_comments,
            output_format="txt",
            url=url
        )
        
        if result:
            # Try to extract title for formatting
            soup = BeautifulSoup(html_content, 'html.parser')
            title = None
            
            # Try various title extraction methods
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            
            # Also try h1 if no title tag
            if not title:
                h1_tag = soup.find('h1')
                if h1_tag:
                    title = h1_tag.get_text().strip()
            
            # Format with title if found
            if title:
                return f"# {title}\n\n{result}"
            else:
                return result
        else:
            # Fallback to readability if Trafilatura returns nothing
            return extract_with_readability(html_content, url)
            
    except ImportError:
        # Trafilatura not available, fallback to readability
        print("Warning: Trafilatura not available, falling back to readability")
        return extract_with_readability(html_content, url)
    except Exception as e:
        print(f"Warning: Trafilatura extraction failed: {e}, falling back to readability")
        return extract_with_readability(html_content, url)


def extract_with_readability(html_content, url):
    """Fallback extraction using readability-lxml.
    
    Args:
        html_content: Raw HTML content
        url: Base URL for resolving relative links
        
    Returns:
        Formatted markdown string with extracted content
    """
    try:
        doc = Document(html_content)
        text = html2text(doc.summary(), baseurl=url, bodywidth=0)
        return f"# {doc.title()}\n\n{text}"
    except Exception as e:
        print(f"Error extracting content with readability: {e}")
        return None


def should_exclude_comments(extracted_text):
    """Determine if comments should be excluded based on content analysis.
    
    Args:
        extracted_text: The extracted text content
        
    Returns:
        bool: True if comments should likely be excluded
    """
    if not extracted_text:
        return True
    
    # Heuristics to determine if comments are valuable content
    lines = extracted_text.split('\n')
    
    # Count lines that look like comments (short, with user-like patterns)
    comment_like_lines = 0
    total_lines = len([line for line in lines if line.strip()])
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Look for patterns typical of user comments
        if (
            (len(line) < 200 and 
             ('@' in line or ':' in line or line.endswith('?') or line.endswith('!'))) or
            (line.startswith(('Posted by', 'Submitted by', 'User:', 'Author:'))) or
            (len(line.split()) < 20 and any(
                word in line.lower()
                for word in ['thanks', 'agree', 'disagree', 'great', 'good', 'bad']
            ))
        ):
            comment_like_lines += 1
    
    # If more than 30% of lines look like comments, they might not be valuable
    if total_lines > 0 and comment_like_lines / total_lines > 0.3:
        return True
    
    # If the text is very long (>5000 chars), it might include too many comments
    if len(extracted_text) > 5000:
        return True
    
    return False