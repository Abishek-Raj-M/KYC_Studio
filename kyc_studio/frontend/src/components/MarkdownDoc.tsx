import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export function MarkdownDoc({ content }: { content: string }) {
  return (
    <div className="markdown-doc max-h-72 overflow-y-auto rounded-md border border-border/60 bg-panel-muted p-3 text-sm text-fg">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  )
}
