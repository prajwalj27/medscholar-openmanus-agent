"""
Report Parser for extracting information from markdown literature survey reports
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Citation:
    """Represents a citation from the report."""
    index: int
    text: str
    url: Optional[str] = None
    title: Optional[str] = None
    source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "text": self.text,
            "url": self.url,
            "title": self.title,
            "source": self.source,
        }


@dataclass
class Claim:
    """Represents a claim from the report."""
    text: str
    section: str
    citations: List[str] = None
    
    def __post_init__(self):
        if self.citations is None:
            self.citations = []


class ReportParser:
    """
    Parser for extracting structured information from markdown reports.
    """
    
    def __init__(self, report_path: str):
        self.report_path = Path(report_path)
        self.content = ""
        self.citations: List[Citation] = []
        self.claims: List[Claim] = []
        self.sections: Dict[str, str] = {}
        
    def parse(self) -> None:
        """Parse the report and extract all structured information."""
        self._read_file()
        self._extract_sections()
        self._extract_citations()
        self._extract_claims()
        
    def _read_file(self) -> None:
        """Read the report file content."""
        if not self.report_path.exists():
            raise FileNotFoundError(f"Report file not found: {self.report_path}")
        
        with open(self.report_path, 'r', encoding='utf-8') as f:
            self.content = f.read()
    
    def _extract_sections(self) -> None:
        """Extract major sections from the report."""
        # Split by headers
        section_pattern = r'^#{1,3}\s+(.+?)$'
        lines = self.content.split('\n')
        
        current_section = "Introduction"
        current_content = []
        
        for line in lines:
            match = re.match(section_pattern, line)
            if match:
                # Save previous section
                if current_content:
                    self.sections[current_section] = '\n'.join(current_content).strip()
                # Start new section
                current_section = match.group(1).strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            self.sections[current_section] = '\n'.join(current_content).strip()
    
    def _extract_citations(self) -> None:
        """
        Extract citations from the References section and inline citations.
        
        Supports formats:
        1. [Title](URL)
        2. Title. Available at: [Source](URL)
        3. Numbered lists with links
        """
        references_section = self._get_references_section()
        if not references_section:
            return
        
        # Pattern 1: Markdown links [text](url)
        markdown_links = re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', references_section)
        
        citations_found = []
        for match in markdown_links:
            title = match.group(1).strip()
            url = match.group(2).strip()
            citations_found.append((title, url))
        
        # Pattern 2: Extract from numbered lists
        lines = references_section.split('\n')
        for i, line in enumerate(lines, 1):
            # Look for numbered items
            numbered_match = re.match(r'^\d+\.\s*(.+)', line)
            if numbered_match:
                citation_text = numbered_match.group(1).strip()
                
                # Try to extract URL and title from this line
                link_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', citation_text)
                if link_match:
                    title = link_match.group(1).strip()
                    url = link_match.group(2).strip()
                else:
                    # If no URL found, use the full text as title
                    title = citation_text
                    url = None
                
                citation = Citation(
                    index=len(self.citations) + 1,
                    text=citation_text,
                    title=title,
                    url=url
                )
                self.citations.append(citation)
        
        # If no citations found via numbered list, try the markdown links directly
        if not self.citations:
            for i, (title, url) in enumerate(citations_found, 1):
                citation = Citation(
                    index=i,
                    text=f"{title}",
                    title=title,
                    url=url
                )
                self.citations.append(citation)
    
    def _get_references_section(self) -> Optional[str]:
        """Get the references/bibliography section."""
        # Common section names for references
        ref_names = ['References', 'Bibliography', 'Citations', 'Sources']
        
        for name in ref_names:
            if name in self.sections:
                return self.sections[name]
        
        # Try case-insensitive search
        for section_name, content in self.sections.items():
            if any(ref.lower() in section_name.lower() for ref in ref_names):
                return content
        
        return None
    
    def _extract_claims(self) -> None:
        """
        Extract claims from the report content.
        
        For now, we'll extract bullet points and key findings.
        More sophisticated claim extraction can be added later.
        """
        for section_name, content in self.sections.items():
            # Skip references section
            if 'reference' in section_name.lower() or 'citation' in section_name.lower():
                continue
            
            # Extract bullet points as claims
            bullet_points = re.finditer(r'^[\-\*]\s+(.+)$', content, re.MULTILINE)
            for match in bullet_points:
                claim_text = match.group(1).strip()
                # Extract inline citations if any
                inline_citations = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', claim_text)
                
                claim = Claim(
                    text=claim_text,
                    section=section_name,
                    citations=[url for _, url in inline_citations]
                )
                self.claims.append(claim)
            
            # Extract numbered points as claims
            numbered_points = re.finditer(r'^\d+\.\s+(.+)$', content, re.MULTILINE)
            for match in numbered_points:
                claim_text = match.group(1).strip()
                inline_citations = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', claim_text)
                
                claim = Claim(
                    text=claim_text,
                    section=section_name,
                    citations=[url for _, url in inline_citations]
                )
                self.claims.append(claim)
    
    def get_citations(self) -> List[Citation]:
        """Get all extracted citations."""
        return self.citations
    
    def get_claims(self) -> List[Claim]:
        """Get all extracted claims."""
        return self.claims
    
    def get_sections(self) -> Dict[str, str]:
        """Get all sections."""
        return self.sections
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get basic statistics about the report."""
        return {
            "total_citations": len(self.citations),
            "total_claims": len(self.claims),
            "total_sections": len(self.sections),
            "citations_with_urls": sum(1 for c in self.citations if c.url),
            "word_count": len(self.content.split()),
        }
