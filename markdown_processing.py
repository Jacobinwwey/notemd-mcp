"""Conservative Markdown boundaries for provider responses; no renderer dependency."""

from dataclasses import dataclass
import re


@dataclass
class Fence:
    language: str
    start: int
    body_start: int
    body_end: int
    end: int
    marker: str
    length: int
    closed: bool = False


def scan_markdown(content):
    lines = content.splitlines(keepends=True)
    fences = []
    protected = set()
    active = None
    offset = 0
    yaml = bool(lines and lines[0].lstrip('\ufeff').rstrip('\r\n') == '---')
    for index, line in enumerate(lines):
        text = line.rstrip('\r\n')
        if index == 0:
            text = text.lstrip('\ufeff')
        end = offset + len(line)
        if yaml:
            protected.add(index)
            if index > 0 and text.strip() in ('---', '...'):
                yaml = False
        elif active:
            protected.add(index)
            close = re.fullmatch(r' {0,3}(`+|~+)[ \t]*', text)
            if close and close[1][0] == active.marker and len(close[1]) >= active.length:
                active.body_end, active.end, active.closed = offset, end, True
                active = None
        elif re.match(r'^( {4}|\t)', text):
            protected.add(index)
        else:
            opening = re.fullmatch(r' {0,3}(`{3,}|~{3,})([^\r\n]*)', text)
            if opening and not (opening[1][0] == '`' and '`' in opening[2]):
                info = opening[2].strip().split()
                active = Fence(info[0].lower() if info else '', offset, end, len(content), len(content), opening[1][0], len(opening[1]))
                fences.append(active)
                protected.add(index)
        offset = end
    return lines, fences, protected


def unwrap_markdown_response(content):
    """Only a complete outer response envelope may be removed; inner code remains owned."""
    _, fences, _ = scan_markdown(content)
    if len(fences) == 1:
        fence = fences[0]
        if (fence.closed and fence.language in ('markdown', 'md', '')
                and not content[:fence.start].strip() and not content[fence.end:].strip()):
            return content[fence.body_start:fence.body_end].rstrip('\r\n')
    return content


def refine_mermaid_blocks(content):
    # Normalize only a known malformed opening tag. Do not infer closure from arrows:
    # styles, notes and future diagram families can legitimately follow the last edge.
    lines, fences, _ = scan_markdown(content)
    del lines
    for fence in reversed(fences):
        if fence.language == '(mermaid)':
            opening = content[fence.start:fence.body_start]
            opening = opening.replace('(mermaid)', 'mermaid', 1)
            content = content[:fence.start] + opening + content[fence.body_start:]
    return content


def cleanup_latex_delimiters(content):
    lines, _, protected = scan_markdown(content)
    inline_ticks = 0
    output = []
    for index, line in enumerate(lines):
        if index in protected:
            inline_ticks = 0
            output.append(line)
            continue
        for part in re.split(r'(`+)', line):
            if re.fullmatch(r'`+', part):
                if not inline_ticks:
                    inline_ticks = len(part)
                elif inline_ticks == len(part):
                    inline_ticks = 0
            elif not inline_ticks:
                part = re.sub(r'(?<!\\)\\\((.*?)\\\)', lambda match: '$' + match[1].strip() + '$', part)
            output.append(part)
    return ''.join(output)


def ensure_mermaid_code_block(content, fallback_header='mindmap'):
    stripped = content.strip()
    _, fences, _ = scan_markdown(stripped)
    if any(fence.language in ('mermaid', '(mermaid)') for fence in fences):
        return refine_mermaid_blocks(stripped)
    if not stripped:
        stripped = fallback_header + '\n    Empty'
    # A family allowlist becomes stale as Mermaid grows; preserve the provider's header.
    marker = '`' * max(3, max((len(match[0]) + 1 for match in re.finditer(r'`+', stripped)), default=3))
    return marker + 'mermaid\n' + stripped + '\n' + marker
