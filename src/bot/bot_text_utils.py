from telegram.helpers import escape_markdown


def escape_md_v1(text: str) -> str:
    if not text:
        return ""
    return escape_markdown(str(text), version=1)


def escape_md_v2(text: str) -> str:
    if not text:
        return ""
    return escape_markdown(str(text), version=2)


def escape_for_inline_code(text: str, markdown_version: int = 1) -> str:
    if not text:
        return ""
    escaped_text_for_inner_content = escape_markdown(
        str(text), version=markdown_version)
    return f"`{escaped_text_for_inner_content}`"


def format_media_title_for_md2(title: str, year: str | int | None) -> str:
    """Formats a title and year for display in a MarkdownV2 message, bolding the title."""
    escaped_title = escape_md_v2(title)
    year_str = str(year) if year else 'N/A'
    escaped_year = escape_md_v2(year_str)
    return f"*{escaped_title}* \\({escaped_year}\\)"


def format_overview_for_md2(overview: str, max_length: int = 0) -> str:
    """Formats an overview for display in a MarkdownV2 message."""
    if not overview:
        return escape_md_v2("Overview not available.")

    processed_overview = overview
    if max_length > 0 and len(processed_overview) > max_length:
        processed_overview = processed_overview[:max_length - 3] + "..."

    return escape_md_v2(processed_overview)


def format_selected_option_for_md2(label: str, value: str) -> str:
    """Formats a label and its selected value for display in MarkdownV2, value in inline code."""
    escaped_label = escape_md_v2(label)
    escaped_value_as_code = escape_for_inline_code(value, markdown_version=2)
    return f"  {escaped_label}: {escaped_value_as_code}\n"
