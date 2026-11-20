/**
 * Small Markdown renderer for VYOM answers. No HTML is ever injected: everything becomes React text.
 * Blocks: # headings, paragraphs, - / * / • and 1. / 1) lists (indent = nesting), > quotes (consecutive
 * lines form one quote), --- rules. Inline: **bold**, __bold__, *italic*, _italic_, `code`.
 * renderText lets the caller turn plain runs into richer nodes (B4: verse citation chips).
 */

/** One list line as written: nesting comes from its indent (2 spaces or a tab per level) */
export interface ListItem { text: string; indent: number; ordered: boolean; number: number }
/** A run of same-type items at one level; each item may hold nested lists */
export interface ListNode { ordered: boolean; start: number; items: { text: string; children: ListNode[] }[] }

export type Block =
  | { type: 'heading'; level: 1 | 2 | 3 | 4; text: string }
  | { type: 'paragraph'; lines: string[] }
  | { type: 'list'; items: ListItem[] }
  | { type: 'quote'; lines: string[] }
  | { type: 'rule' };

const HEADING = /^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$/;
const RULE = /^\s{0,3}([-*_])(\s*\1){2,}\s*$/;
const QUOTE = /^\s{0,3}>\s?(.*)$/;
const BULLET = /^(\s*)[-*•+]\s+(.*)$/;
const ORDERED = /^(\s*)(\d{1,3})[.)]\s+(.*)$/;

export function parseBlocks(markdown: string): Block[] {
  const blocks: Block[] = [];
  let current: Block | null = null;
  const close = () => {
    if (current) blocks.push(current);
    current = null;
  };

  for (const raw of markdown.replace(/\r\n?/g, '\n').split('\n')) {
    const line = raw.replace(/\s+$/, '');
    if (!line.trim()) {
      // A blank line ends paragraphs and quotes; lists survive single blank lines between items
      if (current?.type !== 'list') close();
      continue;
    }
    let m: RegExpMatchArray | null;
    if ((m = line.match(HEADING))) {
      close();
      blocks.push({ type: 'heading', level: Math.min(m[1].length, 4) as 1 | 2 | 3 | 4, text: m[2] });
    } else if (RULE.test(line)) {
      close();
      blocks.push({ type: 'rule' });
    } else if ((m = line.match(QUOTE))) {
      if (current?.type !== 'quote') {
        close();
        current = { type: 'quote', lines: [] };
      }
      if (m[1].trim()) current.lines.push(m[1]);
    } else if ((m = line.match(BULLET)) || (m = line.match(ORDERED))) {
      const ordered = m.length === 4;
      const indent = Math.floor(m[1].replace(/\t/g, '  ').length / 2);
      const text = ordered ? m[3] : m[2];
      if (current?.type !== 'list') {
        close();
        current = { type: 'list', items: [] };
      }
      current.items.push({ text, indent, ordered, number: ordered ? Number(m[2]) : 1 });
    } else if (current?.type === 'list' && /^\s{2,}\S/.test(line)) {
      // Indented continuation of the previous list item
      const last = current.items[current.items.length - 1];
      last.text += ` ${line.trim()}`;
    } else {
      if (current?.type !== 'paragraph') {
        close();
        current = { type: 'paragraph', lines: [] };
      }
      current.lines.push(line.trim());
    }
  }
  close();
  return blocks;
}

/** Turns flat list lines into nested lists. A type change at the same level starts a new list. */
export function nestList(items: ListItem[]): ListNode[] {
  let i = 0;
  const level = (indent: number): ListNode[] => {
    const nodes: ListNode[] = [];
    let node: ListNode | null = null;
    while (i < items.length && items[i].indent >= indent) {
      const item = items[i];
      const lastItem = node?.items[node.items.length - 1];
      if (item.indent > indent && lastItem) {
        lastItem.children.push(...level(item.indent));
        continue;
      }
      if (!node || node.ordered !== item.ordered) {
        node = { ordered: item.ordered, start: item.number, items: [] };
        nodes.push(node);
      }
      node.items.push({ text: item.text, children: [] });
      i += 1;
    }
    return nodes;
  };
  const out: ListNode[] = [];
  while (i < items.length) out.push(...level(items[i].indent));
  return out;
}

export const DEVANAGARI = /[ऀ-ॿ]/;
const IAST_MARKS = /[āīūṛṝḷḹṅñṭḍṇśṣṁṃḥĀĪŪṚṜḶṄÑṬḌṆŚṢṀṂḤ]/g;

/** "sa" for Devanagari, "iast" for romanised Sanskrit (several diacritics), else plain prose */
export function scriptOf(text: string): 'sa' | 'iast' | 'prose' {
  if (DEVANAGARI.test(text)) return 'sa';
  const letters = text.replace(/[^\p{L}]/gu, '').length;
  const marks = text.match(IAST_MARKS)?.length ?? 0;
  return marks >= 2 && marks / Math.max(letters, 1) > 0.04 ? 'iast' : 'prose';
}

/** The answer as plain text, for Copy: no Markdown symbols */
export function markdownToPlainText(markdown: string): string {
  const strip = (s: string) =>
    s.replace(/\*\*([^*]+)\*\*/g, '$1').replace(/__([^_]+)__/g, '$1').replace(/`([^`]+)`/g, '$1')
      .replace(/\*([^*\s][^*]*)\*/g, '$1').replace(/(^|[^\p{L}\d])_([^_\s][^_]*)_(?![\p{L}\d])/gu, '$1$2');
  return parseBlocks(markdown)
    .map((block) => {
      switch (block.type) {
        case 'heading': return strip(block.text);
        case 'rule': return '';
        case 'quote': return block.lines.map(strip).join('\n');
        case 'list': {
          const lines: string[] = [];
          const walk = (nodes: ListNode[], depth: number) => {
            for (const node of nodes) {
              node.items.forEach((item, i) => {
                lines.push(`${'  '.repeat(depth)}${node.ordered ? `${node.start + i}.` : '•'} ${strip(item.text)}`);
                walk(item.children, depth + 1);
              });
            }
          };
          walk(nestList(block.items), 0);
          return lines.join('\n');
        }
        case 'paragraph':
        default:
          return block.type === 'paragraph' ? strip(block.lines.join(' ')) : '';
      }
    })
    .filter((s) => s !== '')
    .join('\n\n');
}
