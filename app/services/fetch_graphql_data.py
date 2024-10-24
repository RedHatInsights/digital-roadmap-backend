import logging
import os
import re
from collections import defaultdict

from bs4 import BeautifulSoup

from app.config import BASE_DIR
from app.models import ReleaseModel

logger = logging.getLogger(__name__)


def load_html_and_split_paragraphs(file_path):
    # Open and read the HTML file
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            html_content = file.read()
    except FileNotFoundError:
        logging.error(f"File {file_path} not found")
        return []

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    sections = defaultdict(str)

    current_title = None
    all_text = []
    title_tags = ["h1", "h2", "h3", "h4", "h5", "h6"]
    # Iterate over the tags in the document
    for element in soup.find_all([*title_tags, "p", "ul", "ol", "li", "div", "span"]):
        if element.name in title_tags:
            if current_title and all_text:
                sections[current_title] = {
                    "title": current_title,
                    "text": normalize_text("\n".join(all_text).strip()),
                    "tag": element.name,
                }

            current_title = normalize_text(element.get_text().strip())
            all_text = []
        else:
            all_text.append(element.get_text().strip())

    if current_title and all_text:
        sections[current_title] = {
            "title": current_title,
            "text": normalize_text("\n".join(all_text).strip()),
            "tag": element.name,
        }

    return list(sections.values())


def normalize_text(text):
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def get_release_notes(release: ReleaseModel):
    # TODO: in future this should be replace with a function that will use GrapQL client to fetch data from database
    # It should be cached for a certain period of time
    logging.info(f"Fetching release notes for version {release.major}.{release.minor}")
    path = os.path.join(BASE_DIR, "data", f"{release.major}.{release.minor}.html")
    data = {"release": release, "paragraphs": load_html_and_split_paragraphs(path)}
    # TODO cache results or load them to the database on schedule
    return data
