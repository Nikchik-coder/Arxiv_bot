import arxiv
import datetime
from typing import List, Dict, Optional
import os
import sys

# Add project root to path for module access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.config import Config

def search_arxiv(topic: str, max_results: int, minutes_back: Optional[int] = None, days_back: Optional[int] = None) -> List[Dict]:
    """
    Search arXiv for articles on a given topic or category.
    
    Args:
        topic: Search query or arXiv category (e.g., "cs.AI", "machine learning")
        max_results: Maximum number of results to return
        minutes_back: Only return articles from the last N minutes (preferred)
        days_back: Only return articles from the last N days (fallback)
        
    Returns:
        List of dictionaries containing article information
    """
    if minutes_back:
        date_threshold = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes_back)
    elif days_back:
        date_threshold = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_back)
    else:
        # Default to a safe fallback if neither is provided
        date_threshold = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)

    # Check if the topic is an arXiv category
    if validate_category(topic):
        query = f"cat:{topic}"
    else:
        # It's a keyword search across title and abstract
        query = f'ti:"{topic}" OR abs:"{topic}"'
    
    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
        
        results = []
        for result in search.results():
            # Ensure the result 'published' datetime is timezone-aware (UTC)
            published_time = result.published.replace(tzinfo=datetime.timezone.utc)
            
            # Only include articles submitted within the date threshold
            if published_time >= date_threshold:
                results.append({
                    'id': result.get_short_id(),
                    'title': result.title.strip(),
                    'authors': [author.name for author in result.authors],
                    'summary': result.summary.replace('\n', ' ').strip(),
                    'pdf_url': result.pdf_url,
                    'published': result.published.strftime('%Y-%m-%d %H:%M'),
                    'categories': result.categories,
                    'primary_category': result.primary_category
                })
            else:
                # Since results are sorted by date, we can stop once we pass the threshold
                break
        
        return results
    
    except Exception as e:
        print(f"Error searching arXiv for topic '{topic}': {e}")
        return []

def get_popular_categories() -> Dict[str, str]:
    """Return a dictionary of popular arXiv categories and their descriptions."""
    return {
        # Computer Science
        'cs.AI': 'Artificial Intelligence',
        'cs.LG': 'Machine Learning', 
        'cs.CV': 'Computer Vision and Pattern Recognition',
        'cs.CL': 'Computation and Language (NLP)',
        'cs.RO': 'Robotics',
        'cs.CR': 'Cryptography and Security',
        'cs.DS': 'Data Structures and Algorithms',
        'cs.SE': 'Software Engineering',
        'cs.DB': 'Databases',
        'cs.NE': 'Neural and Evolutionary Computing',

        # Physics
        'astro-ph': 'Astrophysics',
        'cond-mat': 'Condensed Matter',
        'gr-qc': 'General Relativity and Quantum Cosmology',
        'hep-ex': 'High Energy Physics - Experiment',
        'hep-lat': 'High Energy Physics - Lattice',
        'hep-ph': 'High Energy Physics - Phenomenology',
        'hep-th': 'High Energy Physics - Theory',
        'math-ph': 'Mathematical Physics',
        'nlin.CD': 'Nonlinear Sciences - Chaotic Dynamics',
        'nucl-ex': 'Nuclear Experiment',
        'nucl-th': 'Nuclear Theory',
        'physics.optics': 'Physics - Optics',
        'quant-ph': 'Quantum Physics',

        # Mathematics
        'math.AC': 'Mathematics - Commutative Algebra',
        'math.AP': 'Mathematics - Analysis of PDEs',
        'math.CO': 'Mathematics - Combinatorics',
        'math.DS': 'Mathematics - Dynamical Systems',
        'math.IT': 'Mathematics - Information Theory',
        'math.NT': 'Mathematics - Number Theory',
        'math.OC': 'Mathematics - Optimization and Control',
        'math.PR': 'Mathematics - Probability',
        'math.ST': 'Mathematics - Statistics Theory',

        # Quantitative Biology
        'q-bio.BM': 'Quantitative Biology - Biomolecules',
        'q-bio.GN': 'Quantitative Biology - Genomics',
        'q-bio.MN': 'Quantitative Biology - Molecular Networks',
        'q-bio.NC': 'Quantitative Biology - Neurons and Cognition',
        'q-bio.PE': 'Quantitative Biology - Populations and Evolution',

        # Quantitative Finance
        'q-fin.CP': 'Quantitative Finance - Computational Finance',
        'q-fin.EC': 'Quantitative Finance - Economics',
        'q-fin.ST': 'Quantitative Finance - Statistical Finance',
        'q-fin.TR': 'Quantitative Finance - Trading and Market Microstructure',

        # Statistics
        'stat.AP': 'Statistics - Applications',
        'stat.CO': 'Statistics - Computation',
        'stat.ME': 'Statistics - Methodology',
        'stat.ML': 'Statistics - Machine Learning',
        'stat.TH': 'Statistics - Theory',

        # Electrical Engineering and Systems Science
        'eess.AS': 'Audio and Speech Processing',
        'eess.IV': 'Image and Video Processing',
        'eess.SP': 'Signal Processing',

        # Economics
        'econ.EM': 'Econometrics',
        'econ.GN': 'General Economics',
        'econ.TH': 'Theoretical Economics'
    }

def validate_category(topic: str) -> bool:
    """
    Validate if a string is a plausible arXiv category.
    This is a heuristic and may not be perfect.
    """
    # All known categories are in the popular list, which is a good check.
    # This also handles categories with hyphens.
    if topic in get_popular_categories():
        return True
    
    # Fallback for simple formats like "cs.XX"
    if '.' in topic and len(topic.split('.')) == 2:
        return True
        
    return False
