#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------
# Script Name   : 01_build_wiki.py
# Description   : This script builds the pages of the GitHub wiki from the documentation of the
#                repository. It:
#                   - Collects README.md, CONTRIBUTING.md, SECURITY.md and every page under docs/.
#                   - Names each wiki page after the title of its source page.
#                   - Rewrites the links between pages into wiki links, and every other
#                     relative link into a link to the file in the repository.
#                   - Writes the Home page, the sidebar and the footer.
#
# Usage         : ./scripts/01_build_wiki.py
#
# Output        : dist/wiki, removed and written again on every run.
# --------------------------------------------------------------------------------------------------

import os
import re
import shutil
import sys

# Repository root directory
REPOSITORY_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directory holding the documentation pages
DOCS_DIRECTORY = "docs"

# Directory the wiki pages are written to
WIKI_DIRECTORY = os.path.join(REPOSITORY_DIRECTORY, "dist", "wiki")

# Pages of the repository root, in the order they are listed in the sidebar
ROOT_PAGES = ["README.md", "CONTRIBUTING.md", "SECURITY.md"]

# Page of the repository root that becomes the Home page of the wiki
HOME_PAGE = "README.md"

# Documentation directories, in the order they are listed in the sidebar
SECTIONS = ["architecture", "modules", "examples", "development"]

# Title of the sidebar section listing the pages stored directly under docs/
REFERENCE_SECTION = "Reference"

# Title of the sidebar section listing the pages of the repository root
POLICY_SECTION = "Process And Policy"

# Branch the links to the repository files point at
REPOSITORY_BRANCH = "master"

# Markdown link, as a text and a target
LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")


def read_repository_url() -> str:
    """
    Read the repository url from galaxy.yml
    Returns: str
    """
    # Read the collection metadata
    with open(os.path.join(REPOSITORY_DIRECTORY, "galaxy.yml"), encoding="utf-8") as metadata:
        lines = metadata.read().splitlines()

    # Return the value of the repository key
    for line in lines:
        if line.startswith("repository:"):
            return line.split(":", 1)[1].strip()

    # Fail if the repository key is missing
    raise ValueError("galaxy.yml has no repository key")


def read_page(source: str) -> str:
    """
    Read the content of a documentation page
    Args:
        source: Path of the page, relative to the repository root
    Returns: str
    """
    # Return the page content
    with open(os.path.join(REPOSITORY_DIRECTORY, source), encoding="utf-8") as page:
        return page.read()


def read_title(source: str) -> str:
    """
    Read the title of a documentation page
    Args:
        source: Path of the page, relative to the repository root
    Returns: str
    """
    # Return the text of the first heading
    for line in read_page(source).splitlines():
        if line.startswith("# "):
            return line[2:].strip()

    # Fail if the page has no heading
    raise ValueError("{0} has no title".format(source))


def collect_sources() -> list:
    """
    Collect the documentation pages of the repository
    Returns: list
    """
    # Init sources with the pages of the repository root
    sources = list(ROOT_PAGES)

    # Append every page under the documentation directory
    for directory, _directories, files in os.walk(os.path.join(REPOSITORY_DIRECTORY, DOCS_DIRECTORY)):
        for file in sorted(files):
            if file.endswith(".md"):
                sources.append(os.path.relpath(os.path.join(directory, file), REPOSITORY_DIRECTORY))

    # Return sources
    return sources


def name_pages(sources: list) -> dict:
    """
    Name the wiki page of every documentation page after its title
    Args:
        sources: Paths of the pages, relative to the repository root
    Returns: dict
    """
    # Init pages
    pages = dict()

    # Name every page
    for source in sources:
        # Name the page Home, or after its title with dashes
        name = "Home" if source == HOME_PAGE else read_title(source).replace(" ", "-")

        # Fail if two pages have the same name
        if name in pages.values():
            raise ValueError("two pages are named {0}, give {1} another title".format(name, source))

        # Append page name
        pages[source] = name

    # Return pages
    return pages


def rewrite_links(source: str, content: str, pages: dict, repository_url: str) -> str:
    """
    Rewrite the relative links of a page into wiki links and repository links
    Args:
        source: Path of the page, relative to the repository root
        content: Page content
        pages: Dictionary containing the wiki page name of every page
        repository_url: Url of the repository
    Returns: str
    """

    def rewrite_link(match: re.Match) -> str:
        """
        Rewrite one link
        Args:
            match: Matched link
        Returns: str
        """
        # Extract link text
        text = match.group(1)

        # Extract link target
        target = match.group(2)

        # Keep absolute links and anchors of the same page
        if re.match(r"^([a-z]+:|#)", target):
            return match.group(0)

        # Split the target into a path and an anchor
        path, separator, anchor = target.partition("#")

        # Resolve the path from the repository root
        path = os.path.normpath(os.path.join(os.path.dirname(source), path))

        # Fail if the link points at a file that does not exist
        if not os.path.exists(os.path.join(REPOSITORY_DIRECTORY, path)):
            raise ValueError("{0} links to {1}, which does not exist".format(source, target))

        # Link to the wiki page, or to the file in the repository
        if path in pages:
            url = "{0}/wiki/{1}".format(repository_url, pages[path])
        else:
            url = "{0}/blob/{1}/{2}".format(repository_url, REPOSITORY_BRANCH, path)

        # Return the rewritten link
        return "[{0}]({1}{2}{3})".format(text, url, separator, anchor)

    # Init rewritten lines
    lines = []

    # Init code block state
    in_code_block = False

    # Rewrite the links of every line outside the code blocks
    for line in content.splitlines():
        # Toggle the code block state on a fence
        if line.lstrip().startswith("```"):
            in_code_block = not in_code_block

        # Append the line, rewritten when it is outside a code block
        lines.append(line if in_code_block else LINK_PATTERN.sub(rewrite_link, line))

    # Return the rewritten content
    return "\n".join(lines) + "\n"


def remove_title(content: str) -> str:
    """
    Remove the title of a page, which the wiki shows from the page name
    Args:
        content: Page content
    Returns: str
    """
    # Split the content into lines
    lines = content.splitlines()

    # Remove the first heading
    for index, line in enumerate(lines):
        if line.startswith("# "):
            del lines[index]
            break

    # Return the content without its leading blank lines
    return "\n".join(lines).lstrip("\n") + "\n"


def order_section(directory: str, pages: dict) -> list:
    """
    Order the pages of a documentation directory, hub first, then in the order the hub links them
    Args:
        directory: Documentation directory, relative to the repository root
        pages: Dictionary containing the wiki page name of every page
    Returns: list
    """
    # Init the hub page path
    hub = os.path.join(directory, "README.md")

    # Collect the pages of the directory
    sources = sorted(source for source in pages if os.path.dirname(source) == directory)

    # Return the pages in alphabetical order if the directory has no hub
    if hub not in pages:
        return sources

    # Init ordered pages with the hub
    ordered = [hub]

    # Append the pages in the order the hub links them
    for _text, target in LINK_PATTERN.findall(read_page(hub)):
        # Resolve the link from the repository root
        path = os.path.normpath(os.path.join(directory, target.partition("#")[0]))

        # Append the page if it belongs to the directory and is not listed yet
        if path in sources and path not in ordered:
            ordered.append(path)

    # Return the ordered pages followed by the pages the hub does not link
    return ordered + [source for source in sources if source not in ordered]


def build_sidebar(pages: dict, repository_url: str) -> str:
    """
    Build the sidebar of the wiki
    Args:
        pages: Dictionary containing the wiki page name of every page
        repository_url: Url of the repository
    Returns: str
    """

    def link(source: str) -> str:
        """
        Build the sidebar link of a page
        Args:
            source: Path of the page, relative to the repository root
        Returns: str
        """
        # Return the link, labelled with the page title
        return "[{0}]({1}/wiki/{2})".format(pages[source].replace("-", " "), repository_url, pages[source])

    # Init sidebar with the Home page
    lines = ["- {0}".format(link(HOME_PAGE))]

    # List the known documentation directories first, then any other directory
    directories = sorted(
        {os.path.dirname(source) for source in pages if os.path.dirname(source) not in ("", DOCS_DIRECTORY)}
    )
    sections = [os.path.join(DOCS_DIRECTORY, section) for section in SECTIONS]
    sections = [section for section in sections if section in directories] + [
        directory for directory in directories if directory not in sections
    ]

    # Append one section per documentation directory
    for section in sections:
        # Order the pages of the section
        sources = order_section(section, pages)

        # Append the section title
        lines.append("- **{0}**".format(os.path.basename(section).replace("-", " ").title()))

        # Append the pages of the section
        lines.extend("  - {0}".format(link(source)) for source in sources)

    # Collect the pages stored directly under the documentation directory
    references = sorted(source for source in pages if os.path.dirname(source) == DOCS_DIRECTORY)

    # Append the reference section
    if references:
        lines.append("- **{0}**".format(REFERENCE_SECTION))
        lines.extend("  - {0}".format(link(source)) for source in references)

    # Collect the pages of the repository root other than the Home page
    policies = [source for source in ROOT_PAGES if source != HOME_PAGE and source in pages]

    # Append the policy section
    if policies:
        lines.append("- **{0}**".format(POLICY_SECTION))
        lines.extend("  - {0}".format(link(source)) for source in policies)

    # Return sidebar
    return "\n".join(lines) + "\n"


def build_footer(repository_url: str) -> str:
    """
    Build the footer of the wiki
    Args:
        repository_url: Url of the repository
    Returns: str
    """
    # Return the footer
    return (
        "This wiki is generated from the documentation of the "
        "[repository]({0}). Edit the pages there, not here.\n".format(repository_url)
    )


def main():
    """
    Build the wiki pages
    Returns:
    """
    # Read repository url
    repository_url = read_repository_url()

    # Collect and name the pages
    pages = name_pages(collect_sources())

    # Remove the wiki pages of the previous build
    shutil.rmtree(WIKI_DIRECTORY, ignore_errors=True)

    # Create the wiki directory
    os.makedirs(WIKI_DIRECTORY)

    # Write every page
    for source, name in pages.items():
        # Rewrite the links of the page
        content = rewrite_links(source, read_page(source), pages, repository_url)

        # Remove the title of every page except the Home page
        if source != HOME_PAGE:
            content = remove_title(content)

        # Write the page
        with open(os.path.join(WIKI_DIRECTORY, "{0}.md".format(name)), "w", encoding="utf-8") as page:
            page.write(content)

    # Write the sidebar
    with open(os.path.join(WIKI_DIRECTORY, "_Sidebar.md"), "w", encoding="utf-8") as sidebar:
        sidebar.write(build_sidebar(pages, repository_url))

    # Write the footer
    with open(os.path.join(WIKI_DIRECTORY, "_Footer.md"), "w", encoding="utf-8") as footer:
        footer.write(build_footer(repository_url))

    # Print the result
    print("Built {0} wiki pages in {1}".format(len(pages), WIKI_DIRECTORY))


if __name__ == "__main__":
    # Build the wiki and report a failure without a traceback
    try:
        main()
    except ValueError as error:
        sys.exit("Failed to build the wiki: {0}".format(error))
