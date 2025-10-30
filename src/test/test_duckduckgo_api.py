import requests
from urllib.parse import quote
from bs4 import BeautifulSoup

def duckduckgo_html_search(query, max_results=10):
    """
    Search DuckDuckGo using HTML interface and parse results
    """
    # DuckDuckGo HTML search URL
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    
    # Set headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all search result divs
        results = []
        result_divs = soup.find_all('div', class_='result')
        
        for idx, div in enumerate(result_divs[:max_results]):
            result = {}
            
            # Extract title and link
            title_tag = div.find('a', class_='result__a')
            if title_tag:
                result['title'] = title_tag.get_text(strip=True)
                result['url'] = title_tag.get('href', '')
            
            # Extract snippet/description
            snippet_tag = div.find('a', class_='result__snippet')
            if snippet_tag:
                result['snippet'] = snippet_tag.get_text(strip=True)
            
            if result:
                results.append(result)
        
        return {
            'query': query,
            'num_results': len(results),
            'results': results
        }
        
    except Exception as e:
        return {
            'query': query,
            'error': str(e),
            'results': []
        }

# Test the search
print("Testing DuckDuckGo HTML Search Interface\n")
print("=" * 60)

results = duckduckgo_html_search("python tutorial", max_results=5)

print(f"\nQuery: {results['query']}")
print(f"Number of results: {results.get('num_results', 0)}")

if 'error' in results:
    print(f"\nError: {results['error']}")
else:
    print("\nSearch Results:")
    print("-" * 60)
    for idx, result in enumerate(results['results'], 1):
        print(f"\n{idx}. {result.get('title', 'No title')}")
        print(f"   URL: {result.get('url', 'No URL')}")
        print(f"   Snippet: {result.get('snippet', 'No snippet')[:150]}...")
