"""
Trusted Domain Configuration for Citation Verification

This module maintains lists of trusted academic and medical sources
for the citation accuracy metric.

Note: This list is opinionated and based on commonly accepted reputable sources
in medical and scientific research. For your research, you may want to:

1. Document your rationale for including/excluding domains
2. Consider different trust levels (high/medium/low) instead of binary
3. Make this configurable via a config file
4. Track changes over time as new sources emerge
"""

# Highly trusted medical/health databases
MEDICAL_DATABASES = {
    'pubmed.ncbi.nlm.nih.gov',
    'ncbi.nlm.nih.gov',
    'pmc.ncbi.nlm.nih.gov',
    'nih.gov',
    'cdc.gov',
    'who.int',
    'clinicaltrials.gov',
    'cochrane.org',
    'cochranelibrary.com',
    'uptodate.com',
}

# Reputable academic publishers
ACADEMIC_PUBLISHERS = {
    'springer.com', 'link.springer.com',
    'sciencedirect.com', 'elsevier.com',
    'nature.com', 'science.org', 'cell.com',
    'wiley.com', 'onlinelibrary.wiley.com',
    'tandfonline.com', 'sagepub.com',
    'oxford.com', 'academic.oup.com',
    'cambridge.org',
    'karger.com',
}

# Open access publishers (may want different trust level)
OPEN_ACCESS_PUBLISHERS = {
    'plos.org', 'plosone.org',
    'frontiersin.org',
    'mdpi.com',
    'biomedcentral.com',
}

# Major medical journals
MEDICAL_JOURNALS = {
    'bmj.com',
    'thelancet.com',
    'nejm.org',
    'jamanetwork.com',
    'annals.org',
}

# Medical organizations and societies
MEDICAL_ORGANIZATIONS = {
    'aasm.org', 'ama-assn.org', 'acc.org',
    'heart.org', 'mayoclinic.org', 'clevelandclinic.org',
    'diabetes.org', 'cancer.org', 'cancer.gov',
    'stroke.org',
}

# Research repositories
RESEARCH_REPOSITORIES = {
    'arxiv.org', 'biorxiv.org', 'medrxiv.org',
    'researchgate.net', 'scholar.google.com',
    'europepmc.org', 'semanticscholar.org',
}

# Government health agencies
GOVERNMENT_HEALTH = {
    # United States
    'fda.gov', 'hhs.gov', 'cms.gov',
    # United Kingdom
    'nhs.uk', 'nice.org.uk',
    # Europe
    'ema.europa.eu', 'ecdc.europa.eu',
    # Other countries
    'health.gov.au', 'canada.ca',
}

# Top-tier universities (for institutional research)
# Note: Be careful with this - not all university pages are peer-reviewed
UNIVERSITY_DOMAINS = {
    'harvard.edu', 'stanford.edu', 'mit.edu',
    'jhu.edu', 'mayo.edu',
    'ox.ac.uk', 'cam.ac.uk',  # Oxford, Cambridge
}

# Combine all trusted domains
ALL_TRUSTED_DOMAINS = (
    MEDICAL_DATABASES |
    ACADEMIC_PUBLISHERS |
    OPEN_ACCESS_PUBLISHERS |
    MEDICAL_JOURNALS |
    MEDICAL_ORGANIZATIONS |
    RESEARCH_REPOSITORIES |
    GOVERNMENT_HEALTH |
    UNIVERSITY_DOMAINS
)

# Suspicious patterns that indicate fake/test citations
SUSPICIOUS_PATTERNS = [
    'example.com', 'example.org', 'test.com',
    'localhost', '127.0.0.1',
    'placeholder', 'dummy', 'fake',
    'tempuri.org', 'test.org',
]

# Predatory publisher domains (known problematic sources)
# See: https://beallslist.net/
PREDATORY_PUBLISHERS = {
    # Add known predatory publishers here
    # This is subjective and should be researched carefully
}


def get_trusted_domains(include_universities: bool = True) -> set:
    """
    Get the set of trusted domains.
    
    Args:
        include_universities: Whether to include university domains.
                            These are less strict as not all pages are peer-reviewed.
    
    Returns:
        Set of trusted domain strings
    """
    if include_universities:
        return ALL_TRUSTED_DOMAINS
    else:
        return ALL_TRUSTED_DOMAINS - UNIVERSITY_DOMAINS


def get_trust_level(domain: str) -> str:
    """
    Get the trust level of a domain.
    
    Args:
        domain: Domain name (e.g., 'pubmed.ncbi.nlm.nih.gov')
    
    Returns:
        'high', 'medium', 'low', or 'unknown'
    """
    # Remove www. prefix
    if domain.startswith('www.'):
        domain = domain[4:]
    
    if domain in MEDICAL_DATABASES | MEDICAL_JOURNALS | GOVERNMENT_HEALTH:
        return 'high'
    elif domain in ACADEMIC_PUBLISHERS | MEDICAL_ORGANIZATIONS:
        return 'high'
    elif domain in OPEN_ACCESS_PUBLISHERS | RESEARCH_REPOSITORIES:
        return 'medium'
    elif domain in UNIVERSITY_DOMAINS:
        return 'medium'
    else:
        return 'unknown'
