import logging

from app.models import TaggedParagraph
from app.services.fetch_graphql_data import get_release_notes


def get_relevant_notes(release, keywords=None):
    """
    Get the release notes for a given release and tag the paragraphs that contain the keywords as relevant.
    """
    notes = get_release_notes(release)

    if keywords is None:
        logging.info("No keywords provided, returning all paragraphs as relevant")
        # If no keywords are provided, return all paragraphs
        notes["paragraphs"] = [TaggedParagraph(**para, relevant=True) for para in notes["paragraphs"]]
        return notes

    logging.info(f"Searching for keywords: {keywords}")
    # TODO: This should be cached (expiration onl if release notes change)
    notes["paragraphs"] = [
        TaggedParagraph(**para, relevant=True)
        if any(keyword in para.get("text", "").lower() for keyword in keywords)
        else TaggedParagraph(**para, relevant=False)
        for para in notes["paragraphs"]
    ]
    return notes
