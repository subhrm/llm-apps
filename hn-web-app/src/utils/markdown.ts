/**
 * Lightweight, safe Markdown-to-HTML parser.
 * Converts headings, bold text, links, lists, inline code, and line breaks into styled HTML.
 */
export function parseMarkdown(text: string): string {
  if (!text) return "";

  // Escape HTML tags to prevent XSS issues while permitting our own formatting
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Code blocks (multiline)
  html = html.replace(/```([\s\S]*?)```/g, (_, code) => {
    return `<pre class="code-block"><code>${code.trim()}</code></pre>`;
  });

  // Inline Code: `code`
  html = html.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>');

  // Bold: **text**
  html = html.replace(/\*\*([^\*]+)\*\*/g, "<strong>$1</strong>");

  // Italics: *text*
  html = html.replace(/\*([^\*]+)\*/g, "<em>$1</em>");

  // Links: [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="markdown-link">$1</a>');

  // Lists: Bullet points starting with "- " or "* "
  // Handle them block by block. Let's split by lines first.
  const lines = html.split("\n");
  let inList = false;
  let inNumberedList = false;
  const processedLines: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();

    // Check for bullet list
    const bulletMatch = trimmed.match(/^[-*]\s+(.*)$/);
    if (bulletMatch) {
      if (inNumberedList) {
        processedLines.push("</ol>");
        inNumberedList = false;
      }
      if (!inList) {
        processedLines.push('<ul class="markdown-list">');
        inList = true;
      }
      processedLines.push(`<li>${bulletMatch[1]}</li>`);
      continue;
    }

    // Check for numbered list
    const numberMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (numberMatch) {
      if (inList) {
        processedLines.push("</ul>");
        inList = false;
      }
      if (!inNumberedList) {
        processedLines.push('<ol class="markdown-list numbered">');
        inNumberedList = true;
      }
      processedLines.push(`<li>${numberMatch[2]}</li>`);
      continue;
    }

    // Heading 3: ### text
    const h3Match = trimmed.match(/^###\s+(.*)$/);
    if (h3Match) {
      closeLists(processedLines);
      processedLines.push(`<h3 class="markdown-h3">${h3Match[1]}</h3>`);
      continue;
    }

    // Heading 2: ## text
    const h2Match = trimmed.match(/^##\s+(.*)$/);
    if (h2Match) {
      closeLists(processedLines);
      processedLines.push(`<h2 class="markdown-h2">${h2Match[1]}</h2>`);
      continue;
    }

    // Heading 1: # text
    const h1Match = trimmed.match(/^#\s+(.*)$/);
    if (h1Match) {
      closeLists(processedLines);
      processedLines.push(`<h1 class="markdown-h1">${h1Match[1]}</h1>`);
      continue;
    }

    // Normal line or empty space
    if (trimmed === "") {
      closeLists(processedLines);
      processedLines.push('<div class="markdown-spacer"></div>');
    } else {
      // If we are currently inside a list block, close it
      closeLists(processedLines);
      processedLines.push(`<p class="markdown-para">${line}</p>`);
    }
  }

  // Close any lists that are still open at the end of text
  closeLists(processedLines);

  function closeLists(arr: string[]) {
    if (inList) {
      arr.push("</ul>");
      inList = false;
    }
    if (inNumberedList) {
      arr.push("</ol>");
      inNumberedList = false;
    }
  }

  return processedLines.join("\n");
}
