import React from 'react';
import { nestList, parseBlocks, scriptOf, type ListNode } from './markdown';

/** Renders a VYOM answer's Markdown. Block parsing lives in ./markdown.ts (shared with Copy). */

const INLINE = /(\*\*[^*\n]+?\*\*|__[^_\n]+?__|`[^`\n]+`|\*[^*\s][^*\n]*?\*|(?<![\p{L}\d])_[^_\s][^_\n]*?_(?![\p{L}\d]))/u;

export type TextRenderer = (text: string, key: string) => React.ReactNode;
const plainText: TextRenderer = (text) => text;

function renderInline(text: string, renderText: TextRenderer = plainText, keyPrefix = 'i'): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  let rest = text;
  let n = 0;
  while (rest) {
    const m = rest.match(INLINE);
    if (!m || m.index === undefined) {
      out.push(renderText(rest, `${keyPrefix}-${n++}`));
      break;
    }
    if (m.index > 0) out.push(renderText(rest.slice(0, m.index), `${keyPrefix}-${n++}`));
    const token = m[0];
    const key = `${keyPrefix}-${n++}`;
    if (token.startsWith('**') || token.startsWith('__')) {
      out.push(<strong key={key} className="font-semibold text-[#4B3825]">{renderInline(token.slice(2, -2), renderText, key)}</strong>);
    } else if (token.startsWith('`')) {
      out.push(<code key={key} className="rounded bg-[#F4ECE1] px-1 py-0.5 font-mono text-[0.85em] text-[#4B3825]">{token.slice(1, -1)}</code>);
    } else {
      const inner = token.slice(1, -1);
      const script = scriptOf(inner);
      out.push(
        script === 'sa'
          ? <span key={key} lang="sa" className="font-sanskrit">{inner}</span>
          : <em key={key} className={script === 'iast' ? 'iast' : 'italic'}>{renderInline(inner, renderText, key)}</em>,
      );
    }
    rest = rest.slice(m.index + token.length);
  }
  return out;
}

const HEADING_CLASS: Record<1 | 2 | 3 | 4, string> = {
  1: 'font-cinzel text-lg font-bold text-[#4B3825] mt-7 mb-3',
  2: 'font-cinzel text-lg font-bold text-[#4B3825] mt-7 mb-3',
  3: 'font-cinzel text-base font-bold text-[#8C2D19] mt-6 mb-2 tracking-wide',
  4: 'font-cinzel text-[15px] font-semibold text-[#8C2D19] mt-5 mb-1.5',
};

function QuoteLine({ text, renderText, k }: { text: string; renderText: TextRenderer; k: string }) {
  const script = scriptOf(text);
  if (script === 'sa') return <p lang="sa" className="font-sanskrit text-[15px] leading-8 text-[#2C261F]">{text}</p>;
  if (script === 'iast') return <p className="iast text-[15px] leading-7">{text.replace(/^\*(.*)\*$/, '$1')}</p>;
  return <p className="font-serif text-[15px] italic leading-7 text-[#4B3825]">{renderInline(text, renderText, k)}</p>;
}

function MarkdownList({ nodes, renderText, k, nested = false }: { nodes: ListNode[]; renderText: TextRenderer; k: string; nested?: boolean }) {
  return (
    <>
      {nodes.map((node, n) => {
        const ListTag = node.ordered ? 'ol' : 'ul';
        const marker = node.ordered
          ? 'list-decimal marker:font-semibold marker:text-[#A27427]'
          : `${nested ? 'list-[circle]' : 'list-disc'} marker:text-[#C5A059]`;
        return (
          <ListTag
            key={`${k}-${n}`}
            start={node.ordered && node.start !== 1 ? node.start : undefined}
            className={`${nested ? 'mt-1.5' : 'my-3'} space-y-1.5 pl-6 ${marker}`}
          >
            {node.items.map((item, i) => (
              <li key={i} className="pl-1">
                {renderInline(item.text, renderText, `${k}-${n}-${i}`)}
                {item.children.length > 0 && <MarkdownList nodes={item.children} renderText={renderText} k={`${k}-${n}-${i}`} nested />}
              </li>
            ))}
          </ListTag>
        );
      })}
    </>
  );
}

interface AnswerMarkdownProps {
  text: string;
  renderText?: TextRenderer;
}

export function AnswerMarkdown({ text, renderText = plainText }: AnswerMarkdownProps) {
  const blocks = parseBlocks(text);
  return (
    <div className="md-root font-sans-body text-[15px] leading-7 text-[#2C261F] [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
      {blocks.map((block, b) => {
        const k = `b${b}`;
        switch (block.type) {
          case 'heading': {
            const Tag = (block.level <= 2 ? 'h3' : block.level === 3 ? 'h4' : 'h5') as 'h3' | 'h4' | 'h5';
            return <Tag key={k} className={HEADING_CLASS[block.level]}>{renderInline(block.text, renderText, k)}</Tag>;
          }
          case 'rule':
            return <hr key={k} className="my-6 border-0 border-t border-[#C5A059]/25" />;
          case 'quote':
            return (
              <blockquote key={k} className="my-4 space-y-1 rounded-r-lg border-l-2 border-[#C5A059]/60 bg-[#F4ECE1]/55 py-2.5 pl-4 pr-3">
                {block.lines.map((line, i) => <QuoteLine key={i} text={line} renderText={renderText} k={`${k}-${i}`} />)}
              </blockquote>
            );
          case 'list':
            return <MarkdownList key={k} nodes={nestList(block.items)} renderText={renderText} k={k} />;
          case 'paragraph':
          default:
            return (
              <p key={k} className="my-3">
                {block.type === 'paragraph' && block.lines.map((line, i) => (
                  <React.Fragment key={i}>
                    {i > 0 && ' '}
                    {renderInline(line, renderText, `${k}-${i}`)}
                  </React.Fragment>
                ))}
              </p>
            );
        }
      })}
    </div>
  );
}

