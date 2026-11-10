import { Fragment } from 'react';
import styles from './Section.module.css';

const INLINE = /(\*\*[^*\n]+\*\*|`[^`\n]+`|\*[^*\n]+\*)/;

// Inline bold, italic and code. Built as React nodes, so no HTML from the text is ever injected.
function inline(text, key) {
  return text.split(INLINE).map((part, index) => {
    const k = `${key}-${index}`;
    if (part.length > 4 && part.startsWith('**') && part.endsWith('**')) return <strong key={k}>{part.slice(2, -2)}</strong>;
    if (part.length > 2 && part.startsWith('`') && part.endsWith('`')) return <code key={k}>{part.slice(1, -1)}</code>;
    if (part.length > 2 && part.startsWith('*') && part.endsWith('*')) return <em key={k}>{part.slice(1, -1)}</em>;
    return <Fragment key={k}>{part}</Fragment>;
  });
}

function blocksOf(source) {
  const blocks = [];
  let para = null;
  let list = null;
  const closeParagraph = () => {
    if (para) blocks.push({ type: 'p', lines: para });
    para = null;
  };
  const closeList = () => {
    if (list) blocks.push({ type: 'ul', items: list });
    list = null;
  };
  for (const raw of (source || '').split('\n')) {
    const line = raw.trim();
    if (!line) {
      closeParagraph();
      closeList();
      continue;
    }
    const heading = /^(#{1,3})\s+(.*)$/.exec(line);
    if (heading) {
      closeParagraph();
      closeList();
      blocks.push({ type: 'h', level: heading[1].length, text: heading[2] });
      continue;
    }
    const item = /^[-*]\s+(.*)$/.exec(line);
    if (item) {
      closeParagraph();
      list = list || [];
      list.push(item[1]);
      continue;
    }
    closeList();
    para = para || [];
    para.push(line);
  }
  closeParagraph();
  closeList();
  return blocks;
}

export default function Markdown({ source }) {
  return (
    <div className={styles.preview}>
      {blocksOf(source).map((block, i) => {
        if (block.type === 'h') {
          const Tag = block.level === 1 ? 'h2' : block.level === 2 ? 'h3' : 'h4';
          return <Tag key={i}>{inline(block.text, i)}</Tag>;
        }
        if (block.type === 'ul') {
          return (
            <ul key={i}>
              {block.items.map((text, j) => <li key={j}>{inline(text, `${i}-${j}`)}</li>)}
            </ul>
          );
        }
        return (
          <p key={i}>
            {block.lines.map((text, j) => (
              <Fragment key={j}>
                {j > 0 && ' '}
                {inline(text, `${i}-${j}`)}
              </Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}
